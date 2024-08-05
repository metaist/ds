#!/usr/bin/env python
"""Run dev scripts.

.. include:: ../../README.md
   :start-line: 2
"""

# std
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from os.path import relpath
from pathlib import Path
from subprocess import run
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple
import json
import os
import re
import shlex
import sys
import textwrap

# TODO 2024-10-31 [3.8 EOL]: remove conditional
if sys.version_info >= (3, 9):  # pragma: no cover
    import graphlib
else:  # pragma: no cover
    import graphlib  # type: ignore


# TODO 2026-10-04 [3.10 EOL]: remove conditional
if sys.version_info >= (3, 11):  # pragma: no cover
    import tomllib as toml
else:  # pragma: no cover
    import tomli as toml

__version__ = "0.1.3"
__pubdate__ = "2024-07-25T06:20:18Z"

# NOTE: Used by cog in README.md
usage = """ds: Run dev scripts.

Usage: ds [--help | --version] [--debug]
          [--cwd PATH] [--file PATH]
          [--list | (<task>[: <options>... --])...]

Options:
  -h, --help
    Show this message and exit.

  --version
    Show program version and exit.

  --debug
    Show debug messages.

  --cwd PATH
    Set the working directory (default: task file parent).

  -f PATH, --file PATH
    File with task definitions (default: search in parents).

  -l, --list
    List available tasks and exit.

  <task>[: <options>... --]
    One or more tasks to run with task-specific arguments.
    Use a colon (`:`) to indicate start of arguments and
    double-dash (`--`) to indicate the end.

    If the first <option> starts with a hyphen (`-`), you may omit the
    colon (`:`). If there are no more tasks after the last option, you
    may omit the double-dash (`--`).

Examples:
List the available tasks:
$ ds

Run one or more tasks:
$ ds build
$ ds clean build

If a task fails, subsequent tasks are not run.

Provide arguments to one or more tasks (the following are equivalent):
$ ds clean --all -- build test --no-gpu
$ ds clean --all && ds build && ds test --no-gpu
"""


Loader = Callable[[str], Dict[str, Any]]
"""A loader takes text and returns a mapping of strings to values."""

LOADERS: Dict[str, Loader] = {".toml": toml.loads, ".json": json.loads}
"""Mapping of file extensions to string load functions."""

# NOTE: Used by cog in README.md
SEARCH_FILES = [
    "ds.toml",
    ".ds.toml",
    "Cargo.toml",
    "composer.json",
    "package.json",
    "pyproject.toml",
]
"""Search order for configuration file names."""

# NOTE: Used by cog in README.md
SEARCH_KEYS = [
    "scripts",  # ds.toml, .ds.toml, package.json, composer.json
    "tool.ds.scripts",  # pyproject.toml
    "tool.pdm.scripts",  # pyproject.toml
    "package.metadata.scripts",  # Cargo.toml
]
"""Search order for configuration keys."""

RE_ARGS = re.compile(r"(\$(?:@|\d+))")
"""Regex for matching an argument to be interpolated."""

ARG_START = ":"
"""Explicit command-line start of task arguments."""

ARG_END = "--"
"""Explicit command-line end of task arguments."""

PREFIX_KEEP_GOING = "+"
"""Error suppression prefix."""

PREFIX_ARG_START = "-"
"""Implicit start of command-line task arguments."""

COMPOSITE_NAME = "#composite"
"""Name of a task that is part of a composite task."""


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
                parsed.name = COMPOSITE_NAME
                task.depends.append(parsed)

        elif isinstance(config, str):
            task.cmd = config
            if config.startswith(PREFIX_KEEP_GOING):  # suppress error
                task.cmd = config[len(PREFIX_KEEP_GOING) :]
                task.keep_going = True

        elif isinstance(config, Mapping):
            if "composite" in config:
                assert isinstance(config["composite"], list)
                return Task.parse(config["composite"])

            elif "shell" in config:
                return Task.parse(str(config["shell"]))

            elif "cmd" in config:
                cmd = config["cmd"]
                return Task.parse(" ".join(cmd) if isinstance(cmd, list) else str(cmd))

            elif "call" in config:
                raise ValueError(f"pdm-style `call` commands not supported: {config}")
            else:
                raise TypeError(f"Unknown task type: {config}")
        else:
            raise TypeError(f"Unknown task type: {config}")
        return task

    def pprint(self) -> None:
        """Pretty-print a representation of this task."""
        cmd = f"{PREFIX_KEEP_GOING if self.keep_going else ''}{self.cmd}"
        if self.depends:
            cmd = str(
                [
                    f"{PREFIX_KEEP_GOING if t.keep_going else ''}{t.cmd}"
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

        # 3. Check if a part of a composite command is calling another task.
        if self.name == COMPOSITE_NAME:
            cmd, *args = shlex.split(self.cmd)
            other = tasks.get(cmd)
            if other and other != self and self not in other.depends:
                return other.run(tasks, args + extra, keep_going)

        if not self.allow_shell:
            raise ValueError(f"Unknown task: {self.cmd}")

        # 4. Run our command.
        prefix = PREFIX_KEEP_GOING if keep_going else ""
        cmd = interpolate_args(self.cmd, [*extra])
        print(f"\n$ {prefix}{cmd}")
        proc = run(cmd, shell=True, text=True)
        code = proc.returncode

        if code != 0 and not keep_going:
            sys.exit(code)
        return 0  # either it was zero or we keep going


Tasks = Dict[str, Task]
"""Mapping a task name to a `Task`."""


@dataclass
class Args:
    """Type-checked arguments."""

    help: bool = False
    """Whether to show the usage."""

    version: bool = False
    """Whether to show the version."""

    debug: bool = False
    """Whether to show debug messages"""

    cwd: Optional[Path] = None
    """Path to run tasks in."""

    file_: Optional[Path] = None
    """Path to task definitions."""

    list_: bool = False
    """Whether to show available tasks"""

    task: Task = field(default_factory=Task)
    """A composite task for the tasks given on the command-line."""


def interpolate_args(cmd: str, args: List[str]) -> str:
    """Return `args` interpolated into `cmd`."""
    not_done: List[Optional[str]] = [arg for arg in args]

    # By default, we append all args to the end of the command.
    if not RE_ARGS.search(cmd):
        cmd = f"{cmd} $@"

    def _replace_arg(match: re.Match[str]) -> str:
        """Return the argument replacement."""
        if match[0] == "$@":  # remaining args
            return " ".join(arg for arg in not_done if arg is not None)

        idx = int(match[0][1:]) - 1
        if idx >= len(args):
            raise IndexError(f"Not enough arguments provided: ${idx+1}")

        not_done[idx] = None
        return args[idx]

    return RE_ARGS.sub(_replace_arg, cmd).rstrip()


def get_path(src: Dict[str, Any], name: str, default: Optional[Any] = None) -> Any:
    """Return value of `name` within `src` or `default` if it's missing."""
    path = name.split(".")
    result: Any = default
    try:
        for key in path:
            result = src[key]  # take step
            src = result  # preserve context
    except (KeyError, IndexError, TypeError):
        # key doesn't exist, index is unreachable, or item is not indexable
        result = default
    return result


def check_cycles(tasks: Tasks) -> List[str]:
    """Raise a `CycleError` if there is a cycle in the task graph."""
    graph = {}
    for name, task in tasks.items():
        edges = set()
        for dep in task.depends:
            other = shlex.split(dep.cmd)[0]

            # In theory, this should have been stripped when parsing commands.
            if other.startswith("-"):  # pragma: no cover
                other = other[1:]
            if other != name:
                edges.add(other)
        graph[name] = edges
    return list(graphlib.TopologicalSorter(graph).static_order())


def print_tasks(path: Path, tasks: Tasks) -> None:
    """Pretty print task names."""
    count = len(tasks)
    plural = "s" if count != 1 else ""

    path_abs = str(path.resolve())
    path_rel = relpath(path, Path.cwd())
    location = path_abs if len(path_abs) < len(path_rel) else path_rel

    print(f"# Found {count} task{plural} in {location}\n")
    for task in tasks.values():
        task.pprint()


def parse_config(config: Dict[str, Any], keys: Optional[List[str]] = None) -> Tasks:
    """Parse a configuration file."""
    result = {}
    found = False
    for key in keys or SEARCH_KEYS:
        section = get_path(config, key)
        if section is not None:
            assert isinstance(section, Mapping)
            found = True
            for name, cmd in section.items():
                name = name.strip()
                if not name or name.startswith("#"):
                    continue
                task = Task.parse(cmd)
                task.name = name
                result[name] = task
            break
    if not found:
        raise LookupError(f"Could not find one of: {', '.join(keys or SEARCH_KEYS)}")
    return result


def load_config(path: Path) -> Tasks:
    """Load and parse the configuration file."""
    if path.suffix not in LOADERS:
        raise LookupError(f"Not sure how to read a {path.suffix} file: {path}")

    config = LOADERS[path.suffix](path.read_text())
    return parse_config(config)


def find_config(start: Path, debug: bool = False) -> Tuple[Path, Tasks]:
    """Return the config file in `start` or its parents."""
    for path in (start / "x").resolve().parents:  # to include start
        for name in SEARCH_FILES:
            check = path / name
            if debug:
                print("check", check.resolve())
            if check.exists():
                try:
                    return check, load_config(check)
                except LookupError:  # pragma: no cover
                    # No valid sections.
                    continue
    raise FileNotFoundError("No valid configuration file found.")


def parse_args(argv: List[str]) -> Args:
    """Parse command-line arguments in a docopt-like way."""
    args = Args()
    tasks: List[str] = []
    task = ""
    is_ours = True
    is_task = False
    while argv:
        arg = argv.pop(0)
        if is_ours:
            if arg in ["--help", "--version", "--debug"]:
                setattr(args, arg[2:], True)
            elif arg == "-h":
                args.help = True
            elif arg in ["-l", "--list"]:
                args.list_ = True
            elif arg == "--cwd":
                args.cwd = Path(argv.pop(0)).resolve()
            elif arg in ["-f", "--file"]:
                args.file_ = Path(argv.pop(0)).resolve()
            else:
                is_ours = False

        if is_ours:
            continue  # processed
        # our args processed

        if task and arg == ARG_START:  # explicit arg start
            is_task = True
            continue  # not an argument

        if arg == ARG_END:  # explicit arg end
            task, is_task = "", False
            continue  # not an argument

        if task and arg.startswith(PREFIX_ARG_START):  # implicit arg start
            is_task = True

        if is_task:  # append task args
            tasks[-1] += f" {arg}"
            continue  # processed

        if arg.endswith(ARG_START):  # task name + explicit arg start
            arg = arg[: -len(ARG_START)]
            is_task = True

        task = arg
        tasks.append(task)

    args.task = Task.parse(tasks)
    for dep in args.task.depends:
        # top-level tasks can't be shell commands
        dep.allow_shell = False

    # all args processed

    if args.help:
        print(usage)
        return sys.exit(0)

    if args.version:
        print(f"{__version__} ({__pubdate__})\n")
        return sys.exit(0)

    if args.debug:
        print(args)
    return args


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point."""
    try:
        args = parse_args((argv or sys.argv)[1:])
        if args.file_:
            if not args.file_.exists():
                raise FileNotFoundError(f"Cannot find file: {args.file_}")
            tasks = load_config(args.file_)
        else:
            args.file_, tasks = find_config(Path.cwd(), args.debug)

        args.cwd = args.cwd or args.file_.parent
        if not args.cwd.exists():
            raise NotADirectoryError(f"Cannot find directory: {args.cwd}")

        check_cycles(tasks)
    except graphlib.CycleError as e:
        cycle = e.args[1]
        print("ERROR: Task cycle detected:", " => ".join(cycle))
        sys.exit(1)
    except (FileNotFoundError, NotADirectoryError, LookupError) as e:
        print("ERROR:", e)
        sys.exit(1)

    if args.list_ or not args.task.depends:
        print_tasks(args.file_, tasks)
        sys.exit(0)

    curr = os.getcwd()
    os.chdir(args.cwd)
    try:
        args.task.run(tasks)
    except ValueError as e:
        print("ERROR:", e)
        sys.exit(1)
    except KeyboardInterrupt:  # pragma: no cover
        return
    finally:
        os.chdir(curr)


if __name__ == "__main__":  # pragma: no cover
    main()
