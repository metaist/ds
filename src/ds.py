#!/usr/bin/env python
"""Run dev scripts.

.. include:: ../README.md
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
import json
import os
import shlex
import sys
import textwrap

# TODO 2026-10-04 [3.10 EOL]: remove conditional
if sys.version_info >= (3, 11):  # pragma: no cover
    import tomllib as toml
else:  # pragma: no cover
    import tomli as toml

__version__ = "0.1.0"
__pubdate__ = "unpublished"

usage = """ds: Run dev scripts.

Usage: ds [--help | --version] [--debug]
          [--cwd PATH] [--file PATH]
          [--list | (<task> [: <options>... --])...]

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

  <task> [: <options>... --]
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

SEARCH_FILES = ["ds.toml", ".ds.toml", "package.json", "pyproject.toml"]
"""Search order for configuration file names."""

SEARCH_KEYS = ["scripts", "tool.ds.scripts", "tool.pdm.scripts"]
"""Search order for configuration keys."""

PYTHON_CALL = "python -c 'import sys, {module} as _1; sys.exit(_1.{func})'"
"""Template for a python call."""


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

    task: Dict[str, List[str]] = field(default_factory=dict)
    """Mapping of task names to extra arguments."""


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

    @staticmethod
    def parse(config: Any) -> Task:
        """Parse a config into a `Task`."""
        task = Task()
        if isinstance(config, list):
            for item in config:
                parsed = Task.parse(item)
                parsed.name = "#composite"
                task.depends.append(parsed)
            # task.depends.extend(Task.parse(x) for x in config)

        elif isinstance(config, str):
            task.cmd = config
            if config.startswith("-"):  # suppress error
                task.cmd = config[1:]
                task.keep_going = True

        elif isinstance(config, Mapping):
            if "composite" in config:
                assert isinstance(config["composite"], list)
                task = Task.parse(config["composite"])

            elif "shell" in config:
                task.cmd = str(config["shell"])

            elif "cmd" in config:
                cmd = config["cmd"]
                task.cmd = " ".join(cmd) if isinstance(cmd, list) else str(cmd)

            elif "call" in config:
                # See: https://github.com/pdm-project/pdm/blob/c76e982e46c6e77a54a0fca4d4417eabb70cc85d/src/pdm/cli/commands/run.py#L333
                cmd = config["call"]
                assert isinstance(cmd, str)
                module, _, func = cmd.partition(":")
                func += "()" if not func.endswith(")") else ""
                task.cmd = PYTHON_CALL.format(module=module, func=func)
            else:
                raise TypeError(f"Unknown task type: {config}")
        else:
            raise TypeError(f"Unknown task type: {config}")
        return task

    def pprint(self) -> None:
        """Pretty-print a representation of this task."""
        cmd = f"{'-' if self.keep_going else ''}{self.cmd}"
        if self.depends:
            cmd = str([f"{'-' if t.keep_going else ''}{t.cmd}" for t in self.depends])

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
        self,
        tasks: Tasks,
        extra: Optional[List[str]] = None,
        keep_going: bool = False,
        seen: Optional[List[Task]] = None,
    ) -> int:
        """Run this task."""
        seen = seen or []
        if self in seen:
            return 0
        seen.append(self)  # avoid loops

        extra = extra or []
        keep_going = keep_going or self.keep_going

        # 1. Run all the dependencies.
        for dep in self.depends:
            dep.run(tasks, extra, keep_going, seen)

        # 2. Check if we have anything to do.
        if not self.cmd.strip():  # nothing to do
            return 0

        # 3. Check if a part of a composite command is calling another task.
        if self.name == "#composite":
            cmd, *args = shlex.split(self.cmd)
            other = tasks.get(cmd)
            if other and other != self and self not in other.depends:
                return other.run(tasks, args + extra, keep_going, seen)

        # 4. Run our command.
        cmd = f"{self.cmd} {' '.join(extra)}".strip()
        print(f"\n$ {cmd}")
        proc = run(cmd, shell=True, text=True)
        code = proc.returncode

        if code != 0 and not keep_going:
            sys.exit(code)
        return 0  # either it was zero or we keep going


Tasks = Dict[str, Task]
"""Mapping a task name to a `Task`."""


def get_path(src: Dict[str, Any], name: str, default: Optional[Any] = None) -> Any:
    """Return"""
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


def run_task(tasks: Tasks, name: str, extra: Optional[List[str]] = None) -> None:
    """Run a task."""
    task = tasks.get(name)
    if task is None:
        raise ValueError(f"Unknown task: {name}")
    task.run(tasks, extra)


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


def find_config(start: Path, debug: bool = False) -> Optional[Path]:
    """Return the config file in `start` or its parents."""
    for path in (start / "x").resolve().parents:  # to include start
        for name in SEARCH_FILES:
            check = path / name
            if debug:
                print("check", check.resolve())
            if check.exists():
                return check
    return None


def parse_args(argv: List[str]) -> Args:
    """Parse command-line arguments in a docopt-like way."""
    args = Args()
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

        if task and arg == ":":  # explicit arg start
            is_task = True
            continue  # not an argument

        if arg == "--":  # explicit arg end
            task, is_task = "", False
            continue  # not an argument

        if task and arg.startswith("-"):  # implicit arg start
            is_task = True

        if is_task:  # add task args
            args.task[task].append(arg)
            continue  # processed

        task = arg
        args.task[task] = []
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
        args.file_ = args.file_ or find_config(Path.cwd(), args.debug)
        if not args.file_:
            raise FileNotFoundError("No configuration file found.")
        if not args.file_.exists():
            raise FileNotFoundError(f"Cannot find file: {args.file_}")

        args.cwd = args.cwd or args.file_.parent
        if not args.cwd.exists():
            raise NotADirectoryError(f"Cannot find directory: {args.cwd}")

        tasks = load_config(args.file_)
    except (FileNotFoundError, NotADirectoryError, LookupError) as e:
        print("ERROR:", e)
        sys.exit(1)

    if args.list_ or not args.task:
        print_tasks(args.file_, tasks)
        sys.exit(0)

    try:
        curr = os.getcwd()
        os.chdir(args.cwd)
        for name, extra in args.task.items():
            run_task(tasks, name, extra)
        os.chdir(curr)
    except ValueError as e:
        print("ERROR:", e)
        sys.exit(1)
    except KeyboardInterrupt:  # pragma: no cover
        return


if __name__ == "__main__":  # pragma: no cover
    main()
