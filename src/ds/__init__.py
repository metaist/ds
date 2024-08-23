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
import logging
import os
import sys

# pkg
from .args import Args
from .args import USAGE
from .env import TempEnv
from .runner import Runner
from .searchers import glob_refine
from .tasks import check_cycles
from .tasks import Config
from .tasks import CycleError
from .tasks import find_config
from .tasks import print_tasks
from .tasks import Task

# from .runner import Runner

__version__ = "1.2.0post"
__pubdate__ = "unpublished"

log_normal = "%(levelname)s: %(message)s"
log_debug = "%(name)s.%(funcName)s: %(levelname)s: %(message)s"
log_verbose = " %(filename)s:%(lineno)s %(funcName)s(): %(levelname)s: %(message)s"
logging.basicConfig(level=logging.WARN, format=log_normal)

log = logging.getLogger(__name__)


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
        if not args.file:
            if path := ENV.get("_DS_CURRENT_FILE"):
                log.debug(f"setting args.file using ENV={path}")
                args.file = Path(path)

        require_workspace = bool(args.workspace)
        if args.file:
            if not args.file.exists():
                raise FileNotFoundError(f"Cannot find file: {args.file}")
            config = Config.load(args.file).parse(require_workspace)
        else:
            # search for a valid config
            config = find_config(Path.cwd(), require_workspace, args.debug)
            args.file = config.path
        # config loaded

        check_cycles(config.tasks)

        args.cwd = args.cwd or config.path.parent
        if not args.cwd.exists():
            raise NotADirectoryError(f"Cannot find directory: {args.cwd}")
    except CycleError as e:
        cycle = e.args[1]
        log.error(f"Task cycle detected: {' => '.join(cycle)}")
        sys.exit(1)
    except (FileNotFoundError, NotADirectoryError, LookupError) as e:
        log.error(str(e))
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
            member_args.file = member_config
        else:
            member_args.file = None

        try:
            with TempEnv(_DS_CURRENT_FILE=None):
                with pushd(member):
                    cli_args = member_args.as_argv()
                    print(f"$ pushd {member}")
                    print(f"$ {join(cli_args)}")
                    main(cli_args)
                    print()
        except SystemExit:  # pragma: no cover
            # Not sure how to cover this case.
            pass


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point."""
    args = Args.parse((argv or sys.argv)[1:])

    # TODO: add --verbose option
    if args.debug:
        log.setLevel(logging.DEBUG)
        formatter = logging.Formatter(log_debug)
        for handler in logging.getLogger().handlers:
            handler.setFormatter(formatter)
        log.debug(args)

    if __pubdate__ == "unpublished":  # pragma: no cover
        # NOTE: When testing we're always using the development version.
        log.warning("You are using a development version of ds.")

    if args.help:
        print(USAGE)
        return

    if args.version:
        print(f"{__version__} ({__pubdate__})")
        return

    runner = Runner(args, {})
    if args.no_config:
        if args.list_:
            log.warning("Cannot list tasks when no configuration file loaded.")
            return
    else:
        config = load_config(args)
        if args.workspace:
            run_workspace(args, config)
            return
        if args.list_:
            print_tasks(config.path, config.tasks)
            return
        runner.tasks = config.tasks

    try:
        with TempEnv(_DS_CURRENT_FILE=str(args.file)):
            with pushd(args.cwd or Path()):
                runner.run(args.task, Task())
    except KeyboardInterrupt:  # pragma: no cover
        # Not sure how to cover CTRL+C.
        return


if __name__ == "__main__":  # pragma: no cover
    # No coverage for being called from the terminal.
    main()
