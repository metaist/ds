"""Parse and run tasks."""

# std
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from os.path import relpath
from pathlib import Path
from shlex import join
from shlex import split
from typing import Dict
from typing import List
from typing import Optional
import logging
import sys

# Coverage disabled to cover all python versions.
# TODO 2024-10-31 [3.8 EOL]: remove conditional
if sys.version_info >= (3, 9):  # pragma: no cover
    import graphlib
else:  # pragma: no cover
    import graphlib  # type: ignore

# pkg
from .env import wrap_cmd
from .symbols import TASK_COMPOSITE
from .symbols import TASK_KEEP_GOING


log = logging.getLogger(__name__)

Tasks = Dict[str, "Task"]
"""Mapping of task names to `Task` objects."""

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

    verbatim: bool = False
    """Whether to format the command at all."""

    depends: List[Task] = field(default_factory=list)
    """Tasks to execute before this one."""

    cmd: str = ""
    """Shell command to execute after `depends`."""

    code: int = 0
    """Return code from running this task."""

    # NOTE: args, cwd, env, keep_going are overridable
    # via the CLI or when calling a composite command.

    args: List[str] = field(default_factory=list)
    """Additional arguments to `cmd`."""

    cwd: Optional[Path] = None
    """Task working directory."""

    env: Dict[str, str] = field(default_factory=dict)
    """Task environment variables."""

    _env: Dict[str, str] = field(default_factory=dict)
    """Hidden environment variables."""

    env_file: Optional[Path] = None
    """Path to an environment file to load."""

    keep_going: bool = False
    """Ignore a non-zero return code."""

    def pprint(self, override: Optional[Task] = None, dry_run: bool = False) -> None:
        """Print a representation of this task."""
        is_run = override or dry_run
        display = self
        if override:
            display = replace(self, cmd=override.cmd, keep_going=override.keep_going)

        print()

        if dry_run:
            print("[DRY RUN]")
        if display.help:
            print("#", display.help)
        print(">", wrap_cmd(self.as_args(override)))

        if not is_run and display.depends:
            print(
                [
                    f"{TASK_KEEP_GOING if t.keep_going else ''}{t.cmd}"
                    for t in display.depends
                ]
            )

        if display.cmd:
            if display.verbatim:
                print("$", display.cmd.strip().replace("\n", "\n$ "))
            else:
                print(f"$ {wrap_cmd(display.cmd)}")

    def as_args(self, override: Optional[Task] = None) -> str:
        """Return a shell representation of running this task."""
        override = override or Task()

        args = ["ds"]
        if self.cwd:
            args.extend(["--cwd", str(self.cwd)])
        if self.env_file:
            args.extend(["--env-file", str(self.env_file)])
        for key, val in (self.env or {}).items():
            args.extend(["-e", f"{key}={val}"])

        prefix = ""
        if self.keep_going or override.keep_going:
            prefix = TASK_KEEP_GOING
        if self.name == TASK_COMPOSITE:
            args.append(f"{prefix}{self.cmd}")
        elif self.name:
            args.append(f"{prefix}{self.name}")
        return join(args)


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

    print(f"# Found {count} task{plural} in {location}")
    for task in tasks.values():
        task.pprint()
