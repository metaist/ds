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
import sys
import textwrap

# TODO 2026-10-04 [3.10 EOL]: remove conditional
if sys.version_info >= (3, 11):  # pragma: no cover
    import tomllib as toml
else:  # pragma: no cover
    import tomli as toml

__version__ = "0.1.0"
__pubdate__ = "unpublished"


@dataclass
class Args:
    """ds: Run dev scripts.

    Usage: ds [--help | --version] [--debug]
              [--list | <task>...]

    Options:
    -h, --help                    show this message and exit
    --version                     show program version and exit
    --debug                       show debug messages

    -l, --list                    list available task
    <task>                        one or more tasks to run

    Examples:
    Run the build task.
    $ ds build
    """

    help: bool = False
    """-h, --help           show usage and exit"""

    version: bool = False
    """--version            show version and exit"""

    debug: bool = False
    """--debug              show debug messages"""

    list_: bool = False
    """-l, --list           show available tasks"""

    task: List[str] = field(default_factory=list)
    """<task>               one or more tasks to run"""


Tasks = Dict[str, Union[str, List[str]]]
"""Mapping a task name to a command or names of other tasks."""


def run_task(tasks: Tasks, name: str) -> None:
    """Run a task."""
    cmd = tasks.get(name)
    if cmd is None:
        raise ValueError(f"Unknown task: {name}")
    elif isinstance(cmd, list):
        for n in cmd:
            run_task(tasks, n)
        return

    assert isinstance(cmd, str)
    print(f"\n$ {cmd}")
    proc = run(cmd, shell=True, text=True)
    if proc.returncode != 0:
        sys.exit(proc.returncode)


def print_tasks(path: Path, tasks: Tasks) -> None:
    """Pretty print task names."""
    print(f"Available tasks (from {relpath(path, Path.cwd())}):\n")
    for name, task in tasks.items():
        cmd = str(task)
        if len(cmd) > 60:
            cmd = textwrap.indent(textwrap.fill(cmd, 60), " " * 22)[22:] + "\n"
        print(f"  {name:15}     {cmd}")


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


PARSERS = {
    "ds.toml": parse_ds,
    ".ds.toml": parse_ds,
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
    while argv:
        arg = argv.pop(0)
        if arg in ["--help", "--version", "--debug"]:
            setattr(args, arg[2:], True)
            continue
        elif arg == "-h":
            args.help = True
        elif arg in ["-l", "--list"]:
            args.list_ = True
        else:
            args.task.append(arg)
    # args processed

    if args.help:
        # https://github.com/python/mypy/issues/9170
        assert Args.__doc__ is not None
        print(textwrap.dedent("\n    " + Args.__doc__).lstrip())
        return sys.exit(0)

    if args.version:
        print(f"{__version__} ({__pubdate__})\n")
        return sys.exit(0)

    if args.debug:
        print(args)

    return args


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point."""
    args = parse_args((argv or sys.argv)[1:])
    path = find_config(Path("."), args.debug)
    if not path or not path.exists():
        print(f"ERROR: Could not find: {', '.join(PARSERS)}.")
        sys.exit(1)

    if args.debug:
        print("found", path)

    config = toml.loads(path.read_text())
    parser = PARSERS[path.name]
    tasks = parser(config)

    if args.list_ or not args.task:
        print_tasks(path, tasks)
        sys.exit(0)

    os.chdir(path.parent)
    for name in args.task:
        run_task(tasks, name)


if __name__ == "__main__":  # pragma: no cover
    try:
        main()
    except KeyboardInterrupt:
        pass
