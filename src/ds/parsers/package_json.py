"""`package.json` parser."""

# std
from __future__ import annotations
from dataclasses import replace
from shlex import split
import json
import logging

# pkg
from . import Config
from . import Membership
from ..args import Args
from ..env import RE_ARGS
from ..searchers import glob_apply
from ..searchers import glob_names
from ..symbols import GLOB_DELIMITER
from ..symbols import TASK_COMPOSITE
from ..symbols import TASK_DISABLED
from ..symbols import TASK_KEEP_GOING
from ..tasks import Task
from ..tasks import Tasks

log = logging.getLogger(__name__)


loads = json.loads
"""Standard `json` parser."""


def parse_workspace(config: Config) -> Membership:
    """`package.json` workspaces are in `workspaces`.

    - [npm](https://docs.npmjs.com/cli/v10/using-npm/workspaces)
    - [yarn](https://yarnpkg.com/features/workspaces)
    - [bun](https://bun.sh/docs/install/workspaces)
    - Not Supported: [pnpm](https://pnpm.io/workspaces): `pnpm-workspace.yaml`
    """
    members: Membership = {}
    if "workspaces" not in config.data:
        raise KeyError(f"Missing 'workspaces' key in {config.path}")

    # SUPPORTED: package.json: workspaces
    # https://docs.npmjs.com/cli/v10/configuring-npm/package-json#workspaces
    # It can describe either the direct paths of the folders to be used as
    # workspaces or it can define globs that will resolve to these same
    # folders.

    # NON-STANDARD: We support glob exclusions. This is like what
    # `pnpm` does in `pnpm-workspace.yaml` and what `bun` hopes to implement.
    members = glob_apply(config.path.parent, config.data["workspaces"])
    return members


def parse_tasks(args: Args, config: Config) -> Tasks:
    """`package.json` tasks are in `scripts`.

    - [npm](https://docs.npmjs.com/cli/v10/using-npm/scripts)
    - [yarn](https://classic.yarnpkg.com/lang/en/docs/cli/run/)
    - [pnpm](https://pnpm.io/cli/run)
    - [bun](https://bun.sh/docs/cli/run)

    Features:
    - **Supported** (*non-standard*): disabled task
    - **Supported** (*non-standard*): `task.help` - task description
    - **Supported**: `task.cmd` - basic task
    - **Supported** (*non-standard*): `task.args` - argument interpolation
    - Not Supported: `task.cwd` - working directory
    - **Supported** (*partial*): `task.depends` - composite task (pre/post only)
    - Not Supported: `task.env` - environments
    - Not Supported: `task.keep_going` - error suppression
    """
    tasks: Tasks = {}
    if "scripts" not in config.data:
        raise KeyError(f"Missing 'scripts' key in {config.path}")

    scripts = config.data["scripts"]
    for name, cmd in scripts.items():
        # Non-standard: disabled task
        if name.startswith(TASK_DISABLED):
            continue

        # Not supported: error suppression
        if cmd.startswith(TASK_KEEP_GOING):
            log.warning(
                "package.json does not support error suppression."
                f'Did you mean "{name}": "ds {cmd}"'
            )

        # Non-standard: argument interpolation
        if RE_ARGS.search(cmd):
            log.warning(
                "package.json does not support argument interpolation. "
                "We'll allow it, but it may break other tools."
            )

        tasks[name] = Task(
            origin=config.path,
            origin_key="scripts",
            name=name,
            cmd=cmd,
            # Non-standard: `task.help`
            help=scripts.get(f"{TASK_DISABLED}{name}", ""),
        )

    # Non-standard: task reference
    for name, task in tasks.items():
        cmd, *_ = split(task.cmd)
        others = glob_names(tasks.keys(), cmd.split(GLOB_DELIMITER))
        for name in others:
            other = tasks.get(name)
            if other and other != task and task not in other.depends:
                log.warning(
                    "package.json does not support tasks that reference other tasks."
                    f'Did you mean: "{name}": "ds {task.cmd}"'
                )

    if args.pre or args.post:
        log.warning("EXPERIMENTAL: --pre and --post flags are experimental.")
        for name, task in tasks.items():
            pre = f"pre{name}" if args.pre and tasks.get(f"pre{name}") else None
            post = f"post{name}" if args.post and tasks.get(f"post{name}") else None
            if not pre and not post:
                continue

            depends = []
            task_copy = replace(task, name=TASK_COMPOSITE)
            if pre:
                depends.append(replace(task_copy, cmd=pre))
            depends.append(replace(task_copy))
            if post:
                depends.append(replace(task_copy, cmd=post))
            task.depends = depends
            task.cmd = ""

    return tasks
