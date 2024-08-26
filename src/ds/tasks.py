"""Parse and run tasks."""

# std
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from os.path import relpath
from pathlib import Path
from shlex import join
from shlex import split
from typing import Any
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
from .env import read_env
from .env import wrap_cmd
from .symbols import starts
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

    keep_going: bool = False
    """Ignore a non-zero return code."""

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


def parse_task(config: Any, origin: Optional[Path] = None, key: str = "") -> Task:
    """Parse a config into a `Task`."""
    task = Task(origin=origin, origin_key=key)
    if isinstance(config, list):
        for item in config:
            parsed = parse_task(item, origin, key)
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
            task.env.update(read_env((origin.parent / config["env_file"]).read_text()))
        elif "env-file" in config:  # `env_file` alias (rye)
            assert origin is not None
            task.env.update(read_env((origin.parent / config["env-file"]).read_text()))

        # Environment Variables
        if "env" in config:
            assert isinstance(config["env"], dict)
            task.env.update(config["env"])

        found = False
        # Composite Task
        if "composite" in config:  # `chain` alias
            found = True
            assert isinstance(config["composite"], list)
            parsed = parse_task(config["composite"], origin, key)
            task.name = parsed.name
            task.cmd = parsed.cmd
            task.depends = parsed.depends
        elif "chain" in config:  # `composite` alias
            found = True
            assert isinstance(config["chain"], list)
            parsed = parse_task(config["chain"], origin, key)
            task.name = parsed.name
            task.cmd = parsed.cmd
            task.depends = parsed.depends

        # Basic Task
        if "shell" in config:
            found = True
            parsed = parse_task(str(config["shell"]), origin, key)
            task.cmd = parsed.cmd
            task.keep_going = parsed.keep_going
        elif "cmd" in config:
            found = True
            cmd = config["cmd"]
            parsed = parse_task(
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
