"""Parse and run tasks."""

# std
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from fnmatch import fnmatch
from os import environ as ENV
from os.path import relpath
from pathlib import Path
from shlex import join
from shlex import split
from subprocess import run
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
import sys

# Coverage disabled to cover all python versions.
# TODO 2024-10-31 [3.8 EOL]: remove conditional
if sys.version_info >= (3, 9):  # pragma: no cover
    import graphlib
else:  # pragma: no cover
    import graphlib  # type: ignore

# pkg
from .env import interpolate_args
from .env import read_env
from .env import wrap_cmd
from .symbols import GLOB_DELIMITER
from .symbols import GLOB_EXCLUDE
from .symbols import starts
from .symbols import TASK_COMPOSITE
from .symbols import TASK_KEEP_GOING

CycleError = graphlib.CycleError
"""Error thrown where there is a cycle in the tasks."""

ORIGINAL_CWD = Path.cwd()
"""Save a reference to the original working directory."""


@dataclass
class Task:
    """Represents a thing to be done."""

    origin: Optional[Path] = None
    """File from which this configuration came."""

    origin_key: str = ""
    """Key from which this task came."""

    name: str = ""
    """Task name."""

    help: str = ""
    """Task description."""

    cmd: str = ""
    """Shell command to execute after `depends`."""

    cwd: Optional[Path] = None
    """Task working directory."""

    env: Dict[str, str] = field(default_factory=dict)
    """Task environment variables."""

    depends: List[Task] = field(default_factory=list)
    """Tasks to execute before this one."""

    keep_going: bool = False
    """Ignore a non-zero return code."""

    verbatim: bool = False
    """Whether to format the command at all."""

    @staticmethod
    def parse(config: Any, origin: Optional[Path] = None, key: str = "") -> Task:
        """Parse a config into a `Task`."""
        task = Task(origin=origin, origin_key=key)
        if isinstance(config, list):
            for item in config:
                parsed = Task.parse(item, origin, key)
                parsed.name = TASK_COMPOSITE
                task.depends.append(parsed)

        elif isinstance(config, str):
            task.keep_going, task.cmd = starts(config, TASK_KEEP_GOING)

        elif isinstance(config, Dict):
            if "verbatim" in config:
                task.verbatim = config["verbatim"]
            if "help" in config:
                task.help = config["help"]

            if "keep_going" in config:
                task.keep_going = config["keep_going"]

            # Working directory
            if "cwd" in config:  # `working_dir` alias (ds)
                assert origin is not None
                task.cwd = origin.parent / config["cwd"]
            elif "working_dir" in config:  # `cwd` alias (pdm)
                assert origin is not None
                task.cwd = origin.parent / config["working_dir"]

            # Environment File
            if "env_file" in config:  # `env-file` alias (pdm)
                assert origin is not None
                task.env.update(
                    read_env((origin.parent / config["env_file"]).read_text())
                )
            elif "env-file" in config:  # `env_file` alias (rye)
                assert origin is not None
                task.env.update(
                    read_env((origin.parent / config["env-file"]).read_text())
                )

            # Environment Variables
            if "env" in config:
                assert isinstance(config["env"], dict)
                task.env.update(config["env"])

            found = False
            # Composite Task
            if "composite" in config:  # `chain` alias
                found = True
                assert isinstance(config["composite"], list)
                parsed = Task.parse(config["composite"], origin, key)
                task.name = parsed.name
                task.cmd = parsed.cmd
                task.depends = parsed.depends
            elif "chain" in config:  # `composite` alias
                found = True
                assert isinstance(config["chain"], list)
                parsed = Task.parse(config["chain"], origin, key)
                task.name = parsed.name
                task.cmd = parsed.cmd
                task.depends = parsed.depends

            # Basic Task
            if "shell" in config:
                found = True
                parsed = Task.parse(str(config["shell"]), origin, key)
                task.cmd = parsed.cmd
                task.keep_going = parsed.keep_going
            elif "cmd" in config:
                found = True
                cmd = config["cmd"]
                parsed = Task.parse(
                    " ".join(cmd) if isinstance(cmd, list) else str(cmd),
                    origin,
                    key,
                )
                task.cmd = parsed.cmd
                task.keep_going = parsed.keep_going

            if not found:
                if "call" in config:
                    raise ValueError(f"`call` commands not supported: {config}")
                raise TypeError(f"Unknown task type: {config}")
        else:
            raise TypeError(f"Unknown task type: {config}")
        return task

    def pprint(self) -> None:
        """Pretty-print a representation of this task."""
        if self.help:
            print("#", self.help)
        print(">", wrap_cmd(self.as_args()))
        if self.depends:
            print(
                [
                    f"{TASK_KEEP_GOING if t.keep_going else ''}{t.cmd}"
                    for t in self.depends
                ]
            )
        if self.cmd:
            if self.verbatim:
                print("$", self.cmd.strip().replace("\n", "\n$ "))
            else:
                print(f"$ {wrap_cmd(self.cmd)}")
        print()

    def as_args(
        self,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        keep_going: bool = False,
    ) -> str:
        """Return a shell representation of running this task."""
        args = ["ds"]
        if cwd or self.cwd:
            args.extend(["--cwd", str(cwd or self.cwd)])
        for key, val in (env or self.env or {}).items():
            args.extend(["-e", f"{key}={val}"])

        prefix = ""
        if keep_going or self.keep_going:
            prefix = TASK_KEEP_GOING
        if self.name == TASK_COMPOSITE:
            args.append(f"{prefix}{self.cmd}")
        elif self.name:
            args.append(f"{prefix}{self.name}")
        return join(args)

    def run(
        self,
        tasks: Tasks,
        extra: Optional[List[str]] = None,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        keep_going: bool = False,
        dry_run: bool = False,
    ) -> int:
        """Run this task."""
        extra = extra or []
        cwd = cwd or self.cwd
        env = env or self.env
        keep_going = keep_going or self.keep_going

        # 1. Run all the dependencies.
        for dep in self.depends:
            dep.run(tasks, extra, cwd, env, keep_going, dry_run)

        # 2. Check if we have anything to do.
        if not self.cmd.strip():  # nothing to do
            return 0

        # 3. Check if a part of a composite task is calling another task.
        if self.name == TASK_COMPOSITE:
            cmd, *args = split(self.cmd)
            others = glob_names(tasks.keys(), cmd.split(GLOB_DELIMITER))
            ran, code = False, 0
            for other_name in others:
                other = tasks.get(other_name)
                if other and other != self and self not in other.depends:
                    ran = True
                    code = other.run(tasks, args + extra, cwd, env, keep_going, dry_run)
            if ran:
                return code

        # 4. Run in the shell.
        cmd = interpolate_args(self.cmd, extra)
        dry_prefix = "[DRY RUN]\n" if dry_run else ""
        print(f"\n{dry_prefix}>", wrap_cmd(self.as_args(cwd, env, keep_going)))
        if self.verbatim:
            print("$", cmd.strip().replace("\n", "\n$ "))
        else:
            print(f"$ {wrap_cmd(cmd)}")
        if dry_run:  # do not actually run the command
            return 0

        combined_env = {**ENV, **env}
        proc = run(
            cmd,
            shell=True,
            text=True,
            cwd=cwd,
            env=combined_env,
            executable=combined_env.get("SHELL"),
        )
        code = proc.returncode

        if code != 0 and not keep_going:
            print("ERROR: return code =", code)
            sys.exit(code)
        return 0  # either it was zero or we keep going


Tasks = Dict[str, Task]
"""Mapping of task names to `Task` objects."""


def check_cycles(tasks: Tasks) -> List[str]:
    """Raise a `CycleError` if there is a cycle in the task graph."""
    graph = {}
    for name, task in tasks.items():
        edges = set()
        for dep in task.depends:
            other = split(dep.cmd)[0]
            if other != name:
                edges.add(other)
        graph[name] = edges
    return list(graphlib.TopologicalSorter(graph).static_order())


def print_tasks(path: Path, tasks: Tasks) -> None:
    """Pretty print task names."""
    count = len(tasks)
    plural = "s" if count != 1 else ""

    path_abs = str(path.resolve())
    path_rel = relpath(path, ORIGINAL_CWD)
    location = path_abs if len(path_abs) < len(path_rel) else path_rel

    print(f"# Found {count} task{plural} in {location}\n")
    for task in tasks.values():
        task.pprint()


def glob_names(names: Iterable[str], patterns: List[str]) -> List[str]:
    """Return the names of `tasks` that match `patterns`.

    Prefixing a pattern with `!` will remove that matched pattern
    from the result.

    >>> names = ['cab', 'car', 'cat', 'crab']
    >>> glob_names(names, ['c?r', 'c*b'])
    ['cab', 'car', 'crab']

    >>> glob_names(names, ['*', '!crab'])
    ['cab', 'car', 'cat']
    """
    result: Dict[str, bool] = {name: False for name in names}
    for pattern in patterns:
        exclude, pattern = starts(pattern, GLOB_EXCLUDE)
        for name in result:
            if fnmatch(name, pattern):
                result[name] = not exclude
    return [name for name, include in result.items() if include]
