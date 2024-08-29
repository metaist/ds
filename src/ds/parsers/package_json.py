"""`package.json` parser."""

# std
from __future__ import annotations
from shlex import split
import json
import logging

# pkg
from ..configs import Config
from ..configs import Membership
from ..env import RE_ARGS
from ..searchers import get_key
from ..searchers import glob_names
from ..searchers import glob_paths
from ..symbols import GLOB_DELIMITER
from ..symbols import KEY_MISSING
from ..symbols import TASK_DISABLED
from ..symbols import TASK_KEEP_GOING
from ..tasks import Task
from ..tasks import Tasks

log = logging.getLogger(__name__)


loads = json.loads
"""Standard `json` parser."""


def parse_workspace(config: Config, key: str = "workspaces") -> Membership:
    """`package.json` workspaces are in `workspaces`.

    - [npm](https://docs.npmjs.com/cli/v10/using-npm/workspaces)
    - [yarn](https://yarnpkg.com/features/workspaces)
    - [bun](https://bun.sh/docs/install/workspaces)
    - Not Supported: [pnpm](https://pnpm.io/workspaces): `pnpm-workspace.yaml`
    """
    data = get_key(config.data, key, KEY_MISSING)
    if data is KEY_MISSING:
        raise KeyError(f"Missing '{key}' key in {config.path}")

    # SUPPORTED: package.json: workspaces
    # https://docs.npmjs.com/cli/v10/configuring-npm/package-json#workspaces
    # It can describe either the direct paths of the folders to be used as
    # workspaces or it can define globs that will resolve to these same
    # folders.
    members: Membership = {}

    # NON-STANDARD: We support glob exclusions. This is like what
    # `pnpm` does in `pnpm-workspace.yaml` and what `bun` hopes to implement.
    members = glob_paths(
        config.path.parent,
        data,
        allow_all=False,
        allow_excludes=True,  # Non-standard, but there's no other exclusion.
        allow_new=True,
    )
    return members


def parse_tasks(config: Config, key: str = "scripts") -> Tasks:
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
    data = get_key(config.data, key, KEY_MISSING)
    if data is KEY_MISSING:
        raise KeyError(f"Missing '{key}' key in {config.path}")

    tasks: Tasks = {}
    for name, cmd in data.items():
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
            origin_key=key,
            name=name,
            cmd=cmd,
            # Non-standard: `task.help`
            help=data.get(f"{TASK_DISABLED}{name}", ""),
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

    return tasks
