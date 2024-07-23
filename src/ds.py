#!/usr/bin/env python
"""Run dev scripts.

.. include:: ../README.md
   :start-line: 2
"""

# std
from dataclasses import dataclass
from dataclasses import field
from os.path import relpath
from pathlib import Path
from subprocess import run
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union
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


Tasks = Dict[str, Union[str, List[str]]]
"""Mapping a task name to a command or names of other tasks."""


def run_task(tasks: Tasks, name: str, extra: Optional[List[str]] = None) -> None:
    """Run a task."""
    cmd = tasks.get(name)
    if cmd is None:
        raise ValueError(f"Unknown task: {name}")
    elif isinstance(cmd, list):
        for n in cmd:
            run_task(tasks, n, extra)
        return

    assert isinstance(cmd, str)
    cmd = f"{cmd} {shlex.join(extra or [])}"
    print(f"\n$ {cmd}")
    proc = run(cmd, shell=True, text=True)
    if proc.returncode != 0:
        sys.exit(proc.returncode)


def print_tasks(path: Path, tasks: Tasks) -> None:
    """Pretty print task names."""
    count = len(tasks)
    plural = "s" if count != 1 else ""

    path_abs = str(path.resolve())
    path_rel = relpath(path, Path.cwd())
    location = path_abs if len(path_abs) < len(path_rel) else path_rel

    print(f"# Found {count} task{plural} in {location}\n")
    indent = " " * 4
    for name, task in tasks.items():
        prefix = "\n"
        if isinstance(task, list):
            prefix = " "
            task = " ".join(task)
        elif len(task) < 80 - len(indent):
            task = f"{indent}{task.strip()}"
        else:
            task = textwrap.fill(
                task.strip(),
                78,
                initial_indent=indent,
                subsequent_indent=indent,
                break_on_hyphens=False,
                tabsize=len(indent),
            )

        task = task.replace("\n", " \\\n")
        print(f"{name}:{prefix}{task}\n")


def parse_ds(config: Dict[str, Any]) -> Tasks:
    """Parse a ds.toml or .ds.toml file."""
    result: Tasks = {}
    if "scripts" in config:
        for name, cmd in config["scripts"].items():
            if isinstance(cmd, str):
                result[name] = cmd
            elif isinstance(cmd, list):
                result[name] = cmd
            else:
                raise ValueError(f"Script [{name}] has unknown value type:", cmd)
    return result


def parse_npm(config: Dict[str, Any]) -> Tasks:
    """Parse a package.json file."""
    result: Tasks = {}
    if "scripts" in config:
        for name, cmd in config["scripts"].items():
            if not isinstance(cmd, str):
                raise ValueError(f"Script [{name}] has unknown type:", cmd)

            if name.startswith("#") or not cmd.strip():
                continue

            result[name] = cmd
    return result


PARSERS = {
    "ds.toml": parse_ds,
    ".ds.toml": parse_ds,
    "package.json": parse_npm,
}
"""Mapping of file names to config parsers."""


def find_config(start: Path, debug: bool = False) -> Optional[Path]:
    """Return the config file in `start` or its parents."""
    for path in (start / "x").resolve().parents:  # to include start
        for name in PARSERS:
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
            raise ValueError("No configuration file found.")
        if not args.file_.exists():
            raise ValueError(f"Cannot find file: {args.file_}")

        args.cwd = args.cwd or args.file_.parent
        if not args.cwd.exists():
            raise ValueError(f"Cannot find directory: {args.cwd}")
    except ValueError as e:
        print("ERROR:", e)
        sys.exit(1)

    config = toml.loads(args.file_.read_text())
    parser = PARSERS[args.file_.name]
    tasks = parser(config)

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
