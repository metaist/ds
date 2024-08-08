"""Parse and run tasks."""

# std
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from os.path import relpath
from pathlib import Path
from shlex import split
from subprocess import run
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
import sys
import textwrap

# TODO 2024-10-31 [3.8 EOL]: remove conditional
if sys.version_info >= (3, 9):  # pragma: no cover
    import graphlib
else:  # pragma: no cover
    import graphlib  # type: ignore

# pkg
from .env import interpolate_args
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

    name: str = ""
    """Name of the task."""

    cmd: str = ""
    """Shell command to execute after `depends`."""

    depends: List[Task] = field(default_factory=list)
    """Tasks to execute before this one."""

    keep_going: bool = False
    """Ignore a non-zero return code."""

    allow_shell: bool = True
    """Whether this task is allowed to run on the shell."""

    @staticmethod
    def parse(config: Any) -> Task:
        """Parse a config into a `Task`."""
        task = Task()
        if isinstance(config, list):
            for item in config:
                parsed = Task.parse(item)
                parsed.name = TASK_COMPOSITE
                task.depends.append(parsed)

        elif isinstance(config, str):
            task.keep_going, task.cmd = starts(config, TASK_KEEP_GOING)

        elif isinstance(config, Dict):
            if "composite" in config:
                assert isinstance(config["composite"], list)
                return Task.parse(config["composite"])

            elif "chain" in config:
                assert isinstance(config["chain"], list)
                return Task.parse(config["chain"])

            elif "shell" in config:
                return Task.parse(str(config["shell"]))

            elif "cmd" in config:
                cmd = config["cmd"]
                return Task.parse(" ".join(cmd) if isinstance(cmd, list) else str(cmd))

            elif "call" in config:
                raise ValueError(f"`call` commands not supported: {config}")
            else:
                raise TypeError(f"Unknown task type: {config}")
        else:
            raise TypeError(f"Unknown task type: {config}")
        return task

    def pprint(self) -> None:
        """Pretty-print a representation of this task."""
        cmd = f"{TASK_KEEP_GOING if self.keep_going else ''}{self.cmd}"
        if self.depends:
            cmd = str(
                [
                    f"{TASK_KEEP_GOING if t.keep_going else ''}{t.cmd}"
                    for t in self.depends
                ]
            )

        indent = " " * 4
        print(f"{self.name}:")
        if len(cmd) < 80 - len(indent):
            print(f"{indent}{cmd.strip()}\n")
        else:
            print(
                textwrap.fill(
                    cmd.strip(),
                    78,
                    initial_indent=indent,
                    subsequent_indent=indent,
                    break_on_hyphens=False,
                    tabsize=len(indent),
                ).replace("\n", " \\\n")
                + "\n"
            )

    def run(
        self, tasks: Tasks, extra: Optional[List[str]] = None, keep_going: bool = False
    ) -> int:
        """Run this task."""
        extra = extra or []
        keep_going = keep_going or self.keep_going

        # 1. Run all the dependencies.
        for dep in self.depends:
            dep.run(tasks, extra, keep_going)

        # 2. Check if we have anything to do.
        if not self.cmd.strip():  # nothing to do
            return 0

        # 3. Check if a part of a composite task is calling another task.
        if self.name == TASK_COMPOSITE:
            cmd, *args = split(self.cmd)
            other = tasks.get(cmd)
            if other and other != self and self not in other.depends:
                return other.run(tasks, args + extra, keep_going)

        if not self.allow_shell:
            raise ValueError(f"Unknown task: {self.cmd}")

        # 4. Run in the shell.
        prefix = TASK_KEEP_GOING if keep_going else ""
        cmd = interpolate_args(self.cmd, [*extra])
        print(f"\n$ {prefix}{cmd}")
        proc = run(cmd, shell=True, text=True)
        code = proc.returncode

        if code != 0 and not keep_going:
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
