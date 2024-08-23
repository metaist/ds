"""Run tasks."""

# std
from os import environ as ENV
from pathlib import Path
from typing import Dict
from typing import Tuple
import dataclasses
import logging
import os
import subprocess
import sys

# pkg
from .args import Args
from .env import interpolate_args
from .env import wrap_cmd
from .searchers import glob_names
from .searchers import glob_parents
from .symbols import GLOB_DELIMITER
from .symbols import TASK_COMPOSITE
from .tasks import Task

log = logging.getLogger(__name__)


def get_venv() -> str:
    """Return the path to the current virtual environment."""
    # NOTE: We only look at the `VIRTUAL_ENV` environment variable
    # because we might be in a `uvx` or `pipx` virtual environment.
    # Those environments help us stay isolated, but they don't set
    # this environment variable.
    return ENV.get("VIRTUAL_ENV", "")


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
            return str(venv / "bin" / "Activate.ps1")
        return default

    # no cover: start
    log.warning("EXPERIMENTAL: Trying to detect venv activation script.")

    # windows
    is_cmd_prompt = "cmd.exe" in ENV.get("ComSpec", "")
    if is_cmd_prompt:
        return str(venv / "Scripts" / "activate")
    if is_powershell:
        return str(venv / "Scripts" / "Activate.ps1")

    return default
    # no cover: stop


@dataclasses.dataclass
class Runner:
    args: Args
    """Command-line arguments."""

    # config: Config
    # """Parsed configuration file."""

    tasks: Dict[str, Task]
    """Mapping of names to tasks."""

    def run(self, task: Task, override: Task) -> int:
        """Run a `task` overriding parts given `override`."""
        resolved = dataclasses.replace(
            override,
            cmd=task.cmd,
            args=task.args + override.args,
            cwd=override.cwd or task.cwd,
            env={**override.env, **task.env},
            keep_going=override.keep_going or task.keep_going,
        )

        for dep in task.depends:
            # NOTE: we do not save the return code of any dependencies
            # because they will fail on their own merits.
            self.run(dep, resolved)
        # dependencies ran

        if not task.cmd.strip():  # nothing to do
            return 0
        # handled dependency-only tasks

        ran, code = self.run_composite(task, resolved)
        if ran:
            return code
        # composite tasks handled

        # task needs to go into shell
        resolved.cmd = interpolate_args(resolved.cmd, resolved.args)
        resolved = self.find_project(task, resolved)  # add dependencies
        resolved = self.run_in_shell(task, resolved)  # run in shell
        return resolved.code

    def run_composite(self, task: Task, override: Task) -> Tuple[bool, int]:
        """Run a composite task."""
        ran, code = False, 0
        if not task.name == TASK_COMPOSITE:
            return ran, code

        others = glob_names(self.tasks.keys(), task.cmd.split(GLOB_DELIMITER))
        for name in others:
            other = self.tasks.get(name)
            # - name is of another task
            # - task is not trying to run itself (ls: ['ls'] runs in shell)
            # - task is not in the other's dependencies
            if other and other != task and task not in other.depends:
                ran = True
                code = self.run(other, override)
            # in all other cases, we're going to run this in the shell
        return ran, code

    def find_project(self, task: Task, override: Task) -> Task:
        """Find project-specific dependencies."""
        if self.args.no_project:
            log.debug(
                "Not searching for project dependencies. "
                "To enable: remove --no-project."
            )
            return override

        log.info("Searching for project dependencies. To disable: add --no-project")
        found, to_find = {}, {}

        # python
        if venv := get_venv():
            log.debug(f"[python] venv detected: {venv}")
        else:
            log.debug("[python] No venv detected; searching for */pyvenv.cfg")
            to_find["python_venv"] = "*/pyvenv.cfg"

        # node
        if not task.origin or (task.origin and task.origin.name == "package.json"):
            log.debug("[node] searching for node_modules/.bin")
            to_find["node_modules"] = "node_modules/.bin"
        else:
            log.debug("[node] Not searching for node_modules/.bin")

        # ready to search
        for key, item in glob_parents(Path(), to_find):
            if key not in found:  # don't overwrite
                found[key] = item
            if len(found) == len(to_find):  # can end early
                break
        # done searching

        result = dataclasses.replace(override)  # make a copy

        # python
        if venv := found.get("python_venv"):
            venv = venv.parent
            log.debug(f"[python] found: {venv}")
            result.cmd = f"{venv_activate_cmd(venv)}\n{override.cmd}"

        # node
        if node_bin := found.get("node_modules"):
            log.debug(f"[node] found: {node_bin}")
            combined_env = {**ENV, **override.env}
            prev = combined_env.get("PATH", "")
            result._env["PATH"] = f"{node_bin}{os.pathsep if prev else ''}{prev}"

        return result

    def run_in_shell(self, task: Task, resolved: Task) -> Task:
        """Run the resolved task in the shell."""
        # TODO: refactor printing task with --list
        dry_prefix = "[DRY RUN]\n" if self.args.dry_run else ""
        print(
            f"\n{dry_prefix}>",
            wrap_cmd(task.as_args(resolved.cwd, resolved.env, resolved.keep_going)),
        )
        if task.verbatim:
            print("$", resolved.cmd.strip().replace("\n", "\n$ "))
        else:
            print(f"$ {wrap_cmd(resolved.cmd)}")

        if self.args.dry_run:  # do not actually run the command
            return resolved

        combined_env = {**ENV, **resolved.env, **resolved._env}
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
