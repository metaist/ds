#!/usr/bin/env python
"""Run dev scripts.

.. include:: ../../README.md
   :start-line: 2
"""

# std
from __future__ import annotations
from contextlib import contextmanager
from os import environ as ENV
from pathlib import Path
from shlex import join
from typing import Iterator
from typing import List
from typing import Optional
from typing import Union
import os
import sys

# pkg
from .args import Args
from .args import parse_args
from .args import USAGE
from .configs import Config
from .configs import find_config
from .configs import glob_refine
from .env import TempEnv
from .tasks import check_cycles
from .tasks import CycleError
from .tasks import print_tasks

__version__ = "1.0.0"
__pubdate__ = "2024-08-08T16:25:40Z"


@contextmanager
def pushd(dest: Union[str, Path]) -> Iterator[Path]:
    """Temporarily change the current working directory."""
    if isinstance(dest, str):
        dest = Path(dest)

    cwd = os.getcwd()
    os.chdir(dest)
    try:
        yield Path(dest).resolve()
    finally:
        os.chdir(cwd)


def load_config(args: Args) -> Config:
    """Load configuration file."""
    try:
        if not args.file_:
            if path := ENV.get("_DS_CURRENT_FILE"):
                if args.debug:
                    print("ds:load_config", "setting args.file_ from ENV=", path)
                args.file_ = Path(path)

        require_workspace = bool(args.workspace)
        if args.file_:
            if not args.file_.exists():
                raise FileNotFoundError(f"Cannot find file: {args.file_}")
            config = Config.load(args.file_).parse(require_workspace)
        else:
            # search for a valid config
            config = find_config(Path.cwd(), require_workspace, args.debug)
            args.file_ = config.path
        # config loaded

        check_cycles(config.tasks)

        args.cwd = args.cwd or config.path.parent
        if not args.cwd.exists():
            raise NotADirectoryError(f"Cannot find directory: {args.cwd}")
    except CycleError as e:
        cycle = e.args[1]
        print("ERROR: Task cycle detected:", " => ".join(cycle))
        sys.exit(1)
    except (FileNotFoundError, NotADirectoryError, LookupError) as e:
        print("ERROR:", e)
        sys.exit(1)

    return config


def run_workspace(args: Args, config: Config) -> None:
    """Run tasks in the context of each member."""
    members = {m: False for m, i in config.members.items() if i}  # reset
    members = glob_refine(config.path.parent, args.workspace, members)
    for member, include in members.items():
        if not include:
            continue

        member_args = args.copy()
        member_args.cwd = None  # remove cwd
        member_args.workspace = []  # remove workspace

        member_config = member / config.path.name
        if member_config.exists():  # try config with same name
            member_args.file_ = member_config
        else:
            member_args.file_ = None

        try:
            with TempEnv(_DS_CURRENT_FILE=None):
                with pushd(member):
                    cli_args = member_args.as_argv()
                    print(f"$ pushd {member}")
                    print(f"$ {join(cli_args)}")
                    main(cli_args)
                    print()
        except SystemExit:  # pragma: no cover
            pass


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point."""
    args = parse_args((argv or sys.argv)[1:])
    if args.debug:
        print(args)

    if args.help:
        print(USAGE)
        return

    if args.version:
        print(f"{__version__} ({__pubdate__})\n")
        return

    config = load_config(args)

    if args.workspace:
        run_workspace(args, config)
        return

    if args.list_:
        print_tasks(config.path, config.tasks)
        return

    try:
        with TempEnv(_DS_CURRENT_FILE=str(args.file_)):
            assert args.cwd is not None
            with pushd(args.cwd):
                args.task.run(config.tasks)
    except ValueError as e:
        print("ERROR:", e)
        sys.exit(1)
    except KeyboardInterrupt:  # pragma: no cover
        return


if __name__ == "__main__":  # pragma: no cover
    main()
