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
from . import parsers
from .args import Args
from .args import USAGE
from .configs import Config
from .env import TempEnv
from .git import validate_installed_hooks, force_install_hooks, find_git_directory
from .runner import find_project
from .runner import Runner
from .searchers import glob_paths
from .tasks import check_cycles
from .tasks import CycleError
from .tasks import print_tasks

__version__ = "1.3.0"
__pubdate__ = "2024-08-29T13:08:58Z"

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

    dest = dest.resolve()
    cwd = Path.cwd()
    if cwd == dest:
        log.debug(f"staying in: {dest}")
        yield dest
        return

    log.debug(f"going to: {dest}")
    os.chdir(dest)
    try:
        yield dest
    finally:
        log.debug(f"coming back: {cwd}")
        os.chdir(cwd)


def load_config(args: Args) -> Config:
    """Load configuration file."""
    try:
        if not args.file:
            if path := ENV.get("DS_INTERNAL__FILE"):
                log.debug(f"Setting --file to $DS_INTERNAL__FILE = {path}")
                args.file = Path(path)

        require_workspace = bool(args.workspace)
        if args.file:
            if not args.file.exists():
                raise FileNotFoundError(f"Cannot find file: {args.file}")
            config = parsers.parse(args.file, require_workspace)
        else:
            # search for a valid config
            config = parsers.find_and_parse(Path.cwd(), require_workspace)
            args.file = config.path
        # config loaded

        check_cycles(config.tasks)

        args.cwd = args.cwd or config.path.parent
        if not args.cwd.exists():
            raise NotADirectoryError(f"Cannot find directory: {args.cwd}")
    except CycleError as e:  # TODO: move this into check_cycles
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
    members = glob_paths(
        config.path.parent,
        args.workspace,
        allow_all=True,
        allow_excludes=True,
        allow_new=False,
        previous=members,
    )
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
            with TempEnv(DS_INTERNAL__FILE=None):
                with pushd(member):
                    cli_args = member_args.as_argv()
                    print(f"$ pushd {member}", flush=True)
                    print(f"$ {join(cli_args)}", flush=True)
                    main(cli_args)
                    print(flush=True)
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

    if args.help:
        print(USAGE)
        return

    if args.version:
        print(f"{__version__} ({__pubdate__})", flush=True)
        return

    if args.self_update:
        # We can only get here if cosmofy.updater didn't self-update.
        log.error(
            "Cannot update a non-Cosmopolitan install. "
            "Please use your package manager (uv or pip) to update."
        )
        return

    if __pubdate__ == "unpublished":  # pragma: no cover
        # NOTE: When testing we're always using the development version.
        log.warning("You are using a development version of ds.")

    runner = Runner(args, {})
    if args.no_config:
        log.debug("Not loading config. To enable: remove --no-config")
        if args.workspace:
            log.error("Cannot use --workspace together with --no-config.")
            sys.exit(1)
        if args.list_:
            log.error("Cannot use --list together with --no-config.")
            sys.exit(1)
    else:
        log.debug("Loading config. To disable: add --no-config")
        config = load_config(args)
        # NOTE: We process --workspace first so that you can run $ ds -w*
        # to be roughly equal to: $ ds --workspace '*' 'ds --list'
        if args.workspace:
            run_workspace(args, config)
            return

        # NOTE: we also process this before the directory listing!
        # git hook sync: if we're in a git directory, then these checks apply
        git_dir = find_git_directory()
        if git_dir is not None:
            # first, if we're allowed to fix stuff then check if we can
            if args.sync_git_hooks:
                # if we're out of sync, fix it and let the user know
                force_install_hooks(git_dir, config.tasks)
                log.info("Synchronized git hooks.")
            else:
                # if we're out of sync, let the user know
                if not validate_installed_hooks(git_dir, config.tasks):
                    log.warning(
                        "Git hooks are defined, but out of sync with the git repo!"
                    )
        else:
            if args.sync_git_hooks:
                log.info("No git repository found in this or parent directories.")

        if args.list_:
            print_tasks(config.path, config.tasks)
            return

        runner.tasks = config.tasks

    try:
        with TempEnv(DS_INTERNAL__FILE=str(args.file)):
            with pushd(args.cwd or Path()):
                override = find_project(args, args.task)
                runner.run(args.task, override)

        for proc in runner.processes:
            proc.wait()
    except KeyboardInterrupt:  # pragma: no cover
        # Not sure how to cover CTRL+C.
        return


if __name__ == "__main__":  # pragma: no cover
    # No coverage for being called from the terminal.
    main()
