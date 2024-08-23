"""Run tasks."""

# std
from os import environ as ENV
from pathlib import Path
from typing import Dict
from typing import Tuple
import dataclasses
import os
import subprocess
import sys
import logging

# pkg
from .args import Args
from .env import interpolate_args
from .env import wrap_cmd
from .searchers import glob_names
from .searchers import walk_parents
from .symbols import GLOB_DELIMITER
from .symbols import TASK_COMPOSITE
from .tasks import Task

log = logging.getLogger(__name__)


def in_venv() -> bool:
    """Return True if we are in a venv."""
    # TODO: consider using ENV["VIRTUAL_ENV"]
    return hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )


def venv_activate_cmd(venv: Path) -> str:
    """Return command for activating a .venv"""
    # linux / macos
    shell = ENV.get("SHELL", "")
    default = f"source {venv / 'bin' / 'activate'};"
    if "bash" in shell or "zsh" in shell:  # most common
        return default
    if "csh" in shell:
        return f"source {venv / 'bin' / 'activate.csh'};"
    if "fish" in shell:
        return f"source {venv / 'bin' / 'activate.fish'};"
    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
        return default

    # no cover: start
    log.warning("EXPERIMENTAL: Trying to detect venv activation script.")

    # mixed
    is_power_shell = len(ENV.get("PSModulePath", "").split(os.pathsep)) >= 3
    if is_power_shell:
        return str(venv / "Scripts" / "activate.ps1")

    # windows
    is_cmd_prompt = "cmd.exe" in ENV.get("ComSpec", "")
    if is_cmd_prompt:
        return str(venv / "Scripts" / "activate")

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
            return override

        result = dataclasses.replace(override)  # make a copy
        combined_env = {**ENV, **override.env}

        found, to_find = {}, [".venv", "node_modules"]
        for item in walk_parents(Path(), to_find):
            name = item.name
            if name not in found:
                found[name] = item
            if len(found) == len(to_find):
                break
        # maybe found them all

        # node
        if node_bin := found.get("node_modules"):
            node_bin = node_bin / ".bin"
            if node_bin.exists():
                log.debug(f"found node_modules = {node_bin}")
                prev_path = combined_env.get("PATH", "")
                if prev_path:
                    prev_path = f"{os.pathsep}{prev_path}"
                result._env["PATH"] = f"{node_bin}{prev_path}"

        # python
        if in_venv():
            log.debug("we are in a .venv")
            return result

        if venv := found.get(".venv"):
            log.debug(f"found .venv: {venv}")
            result.cmd = f"{venv_activate_cmd(venv)}\n{override.cmd}"

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
