"""Run tasks."""

# std
from dataclasses import replace
from os import environ as ENV
from pathlib import Path
from shlex import split
from typing import Dict
from typing import List
from typing import Tuple
import atexit
import dataclasses
import logging
import os
import subprocess
import sys

# pkg
from .args import Args
from .env import interpolate_args
from .env import read_env
from .searchers import glob_names
from .searchers import glob_parents
from .symbols import GLOB_DELIMITER
from .symbols import TASK_COMPOSITE
from .tasks import Task
from .tasks import Tasks

log = logging.getLogger(__name__)


def venv_activate_cmd(venv: Path) -> str:
    """Return command for activating a .venv

    See: https://docs.python.org/3/library/venv.html#how-venvs-work
    """
    # Detecting PowerShell is not great.
    # See: https://stackoverflow.com/a/55598796/
    is_powershell = len(ENV.get("PSModulePath", "").split(os.pathsep)) >= 3

    # POSIX
    shell = ENV.get("SHELL", "")
    default = f"source {venv / 'bin' / 'activate'};"
    if "bash" in shell or "zsh" in shell:  # most common
        return default
    if "fish" in shell:
        return f"source {venv / 'bin' / 'activate.fish'};"
    if "csh" in shell or "tcsh" in shell:
        return f"source {venv / 'bin' / 'activate.csh'};"
    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
        if is_powershell:  # POSIX
            return f"source {venv / 'bin' / 'Activate.ps1'};"
        return default

    # no cover: start
    log.warning("EXPERIMENTAL: Trying to detect venv activation script.")

    # windows
    is_cmd_prompt = "cmd.exe" in ENV.get("ComSpec", "")
    if is_cmd_prompt:
        return str(venv / "Scripts" / "activate.bat") + ";"
    if is_powershell:
        return str(venv / "Scripts" / "Activate.ps1") + ";"

    return default
    # no cover: stop


def find_project(args: Args, task: Task) -> Task:
    """Find project-specific dependencies."""
    if args.no_project:
        log.debug(
            "Not searching for project dependencies. To enable: remove --no-project."
        )
        return task

    log.info("Searching for project dependencies. To disable: add --no-project")
    result = replace(task)  # make a copy
    to_find: Dict[str, str] = {}
    found: Dict[str, Path] = {}

    # python
    # NOTE: We only look at the `VIRTUAL_ENV` environment variable
    # because we might be in a `uvx` or `pipx` virtual environment.
    # Those environments help us stay isolated, but they don't set
    # this environment variable.
    if current_venv := ENV.get("VIRTUAL_ENV"):
        log.debug(f"[python] venv detected: {current_venv}")
    else:
        log.debug("[python] No venv detected; searching for */pyvenv.cfg")
        to_find["python_venv"] = "*/pyvenv.cfg"

    # node
    log.debug("[node] searching for node_modules/.bin")
    to_find["node_modules"] = "node_modules/.bin"

    # ready to search
    for key, item in glob_parents(Path(), to_find):
        if key not in found:  # don't overwrite
            found[key] = item
        if len(found) == len(to_find):  # can end early
            break
    # done searching

    # python
    if venv := found.get("python_venv"):
        venv = venv.parent
        log.debug(f"[python] found: {venv}")
        result.cmd = f"{venv_activate_cmd(venv)}\n{task.cmd}"

    # node
    if node_bin := found.get("node_modules"):
        log.debug(f"[node] found: {node_bin}")
        prev = {**ENV, **result.env}.get("PATH", "")
        if str(node_bin) not in prev:
            result._env["PATH"] = f"{node_bin}{os.pathsep if prev else ''}{prev}"

    return result


@dataclasses.dataclass
class Runner:
    args: Args
    """Command-line arguments."""

    tasks: Tasks
    """Mapping of names to tasks."""

    processes: List[subprocess.Popen] = dataclasses.field(default_factory=list)
    """Subprocesses started in parallel."""

    def run(self, task: Task, override: Task) -> int:
        """Run a `task` overriding parts given `override`."""
        env_from_file = {}
        if task.env_file:
            if not task.env_file.exists():
                log.error(f"Cannot find env-file: {task.env_file}")
                sys.exit(1)

            log.debug(f"Reading env-file: {task.env_file}")
            env_from_file = read_env(task.env_file.read_text())

        resolved = replace(
            override,
            args=task.args + override.args,
            cwd=override.cwd or task.cwd,
            env={**override.env, **task.env},
            _env={**override._env, **override.env, **env_from_file, **task.env},
            env_file=override.env_file or task.env_file,  # for printing
            keep_going=override.keep_going or task.keep_going,
            parallel=override.parallel or task.parallel,
        )

        self.run_pre_post(task, resolved, "pre")

        for dep in task.depends:
            # NOTE: we do not save the return code of any dependencies
            # because they will fail on their own merits.
            self.run(dep, resolved)
        # dependencies ran

        if not task.cmd.strip():  # nothing to do
            return self.run_pre_post(task, resolved, "post")
        # handled dependency-only tasks

        ran, code = self.run_composite(task, resolved)
        if ran:
            return code or self.run_pre_post(task, resolved, "post")
        # composite tasks handled

        # task needs to go into shell
        resolved.cmd = interpolate_args(override.cmd + task.cmd, resolved.args)
        resolved = self.run_in_shell(task, resolved)  # run in shell
        return resolved.code or self.run_pre_post(task, resolved, "post")

    def run_composite(self, task: Task, override: Task) -> Tuple[bool, int]:
        """Run a composite task."""
        ran, code = False, 0
        if not task.name == TASK_COMPOSITE:
            return ran, code

        cmd, *args = split(task.cmd)
        others = glob_names(self.tasks.keys(), cmd.split(GLOB_DELIMITER))
        for name in others:
            other = self.tasks.get(name)
            # - name is of another task
            # - task is not trying to run itself (ls: ['ls'] runs in shell)
            # - task is not in the other's dependencies
            if other and other != task and task not in other.depends:
                ran = True
                code = self.run(other, replace(override, args=override.args + args))
            # in all other cases, we're going to run this in the shell
        return ran, code

    def run_pre_post(self, task: Task, override: Task, pre_post: str = "pre") -> int:
        """Run pre- or post- task."""
        name = task.name
        if not name or name == TASK_COMPOSITE or not getattr(self.args, pre_post):
            return 0

        for check in [f"{pre_post}{name}", f"{pre_post}_{name}", f"{pre_post}-{name}"]:
            log.debug(f"check {check}")
            if sub_task := self.tasks.get(check):
                log.debug(f"EXPERIMENTAL: Running --{pre_post} task {check}")
                return self.run(sub_task, override)

        # no task found
        return 0

    def run_in_shell(self, task: Task, resolved: Task) -> Task:
        """Run the resolved task in the shell."""
        dry_run = self.args.dry_run
        task.pprint(resolved, dry_run)
        if dry_run:  # do not actually run the command
            return resolved

        combined_env = {**ENV, **resolved.env, **resolved._env}
        if resolved.parallel:
            proc = subprocess.Popen(
                resolved.cmd,
                shell=True,
                text=False,
                cwd=resolved.cwd,
                env=combined_env,
                executable=combined_env.get("SHELL"),
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            if not self.processes:  # first parallel
                log.warning("EXPERIMENTAL: running tasks in parallel")
                atexit.register(self.cleanup)
            self.processes.append(proc)
        else:
            proc = subprocess.run(
                resolved.cmd,
                shell=True,
                text=True,
                cwd=resolved.cwd,
                env=combined_env,
                executable=combined_env.get("SHELL"),
            )

            resolved.code = proc.returncode
            if resolved.code != 0 and not resolved.keep_going:
                log.error(f"return code = {resolved.code}")
                sys.exit(resolved.code)
        return resolved

    def cleanup(self) -> None:
        """Cleanup any child processes."""
        log.debug("cleaning up child processes")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
