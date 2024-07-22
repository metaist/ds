#!/usr/bin/env python
"""Run dev scripts.

.. include:: ../README.md
   :start-line: 2
"""

# std
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from subprocess import run
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union
import sys
import textwrap

# TODO 2026-10-04 [3.10 EOL]: switch to native tomllib
try:
    import tomllib as toml  # type: ignore
except ImportError:
    import tomli as toml

__version__ = "0.1.0"
__pubdate__ = "unpublished"


@dataclass
class Args:
    """ds: Run dev scripts.

    Usage: ds [--help | --version] [--debug] <task>...

    Options:
    -h, --help                    show this message and exit
    --version                     show program version and exit
    --debug                       show debug messages

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

    task: List[str] = field(default_factory=list)
    """<task>               one or more names """


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
    for name in args.task:
        run_task(tasks, name)


if __name__ == "__main__":  # pragma: no cover
    try:
        main()
    except KeyboardInterrupt:
        pass
