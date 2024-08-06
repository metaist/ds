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
from typing import List
from typing import Optional
import os
import sys

# pkg
from .args import parse_args
from .configs import find_config
from .configs import load_config
from .configs import SEARCH_KEYS
from .configs import SEARCH_KEYS_WORKSPACE
from .env import TempEnv
from .tasks import check_cycles
from .tasks import graphlib
from .tasks import print_tasks

__version__ = "0.1.3post"
__pubdate__ = "unpublished"


@contextmanager
def pushd(dest: Path):
    """Temporarily change the current working directory."""
    cwd = os.getcwd()
    os.chdir(dest)
    try:
        yield Path(dest).resolve()
    finally:
        os.chdir(cwd)


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point."""
    try:
        args = parse_args((argv or sys.argv)[1:], __version__, __pubdate__)
        if not args.file_:
            if path := ENV.get("_DS_CURRENT_FILE"):
                args.file_ = Path(path)

        if args.file_:
            if not args.file_.exists():
                raise FileNotFoundError(f"Cannot find file: {args.file_}")
            tasks = load_config(args.file_)
        else:
            keys = SEARCH_KEYS if not args.workspace else SEARCH_KEYS_WORKSPACE
            args.file_, tasks = find_config(Path.cwd(), keys, args.debug)

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

    try:
        with TempEnv(_DS_CURRENT_FILE=str(args.file_)):
            with pushd(args.cwd):
                args.task.run(tasks)
    except ValueError as e:
        print("ERROR:", e)
        sys.exit(1)
    except KeyboardInterrupt:  # pragma: no cover
        return


if __name__ == "__main__":  # pragma: no cover
    main()
