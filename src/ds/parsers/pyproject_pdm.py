"""`pyproject.toml` parser for `pdm`."""

# std
from pathlib import Path
from typing import Optional
import logging

# pkg
from ..configs import Config
from ..configs import Membership
from . import toml
from ..searchers import get_key
from ..searchers import glob_paths
from ..symbols import KEY_MISSING
from ..symbols import TASK_COMPOSITE
from ..symbols import TASK_DISABLED
from ..symbols import TASK_SHARED
from ..tasks import Task
from ..tasks import Tasks
from .pyproject_rye import python_call


log = logging.getLogger(__name__)

loads = toml.loads
"""Standard `toml` parser."""


def parse_workspace(config: Config, key: str = "tool.pdm.workspace") -> Membership:
    """`pdm` does not officially support workspaces.

    See: https://github.com/pdm-project/pdm/issues/1505
    """
    data = get_key(config.data, key, KEY_MISSING)
    if data is KEY_MISSING:
        raise KeyError(f"Missing '{key}' key in {config.path}")

    log.warning("EXPERIMENTAL: pdm does not officially support workspaces")
    members: Membership = {}
    if "packages" in data:
        members = glob_paths(
            config.path.parent,
            data["packages"],
            allow_all=False,
            allow_excludes=True,
            allow_new=True,
            previous=members,
        )

    return members


def parse_tasks(config: Config, key: str = "tool.pdm.scripts") -> Tasks:
    """Tasks are in `tool.pdm.scripts`.

    See: https://pdm-project.org/latest/usage/scripts/#user-scripts

    Features:
    - **Supported** (*non-standard*): disabled task
    - **Supported**: `task.help` - task description
    - **Supported**: `task.cmd` - basic task
    - **Supported**: `task.args` - argument interpolation
    - **Supported**: `task.cwd` - working directory
    - **Supported**: `task.depends` - composite task
    - **Supported**: `task.env` - environments
    - **Supported**: `task.keep_going` - error suppression
    """
    data = get_key(config.data, key, KEY_MISSING)
    if data is KEY_MISSING:
        raise KeyError(f"Missing '{key}' key in {config.path}")

    common: Optional[Task] = None
    tasks: Tasks = {}
    for name, item in data.items():
        # Non-standard: disabled tasks
        if name.startswith(TASK_DISABLED):
            continue

        task = Task(origin=config.path, origin_key=key, name=name)
        if isinstance(item, str):
            task.cmd = item
        elif isinstance(item, dict):
            # `help`: https://pdm-project.org/latest/usage/scripts/#show-the-list-of-scripts
            if help := item.get("help"):
                task.help = help

            # `cmd`: https://pdm-project.org/latest/usage/scripts/#cmd
            if cmd := item.get("cmd"):
                task.cmd = " ".join(cmd) if isinstance(cmd, list) else cmd

            # `shell`: https://pdm-project.org/latest/usage/scripts/#shell
            elif cmd := item.get("shell"):
                task.cmd = cmd

            # `call`: https://pdm-project.org/latest/usage/scripts/#call
            elif call := item.get("call"):
                # Non-standard: support `module.name`
                task.cmd = python_call(call)

            # `composite`: https://pdm-project.org/latest/usage/scripts/#composite
            elif composite := item.get("composite"):
                for step in composite:
                    task.depends.append(
                        Task(
                            origin=config.path,
                            origin_key=key,
                            name=TASK_COMPOSITE,
                            cmd=step,
                        )
                    )
            elif name == "_":  # shared options
                pass
            else:  # not sure what kind of command this is
                raise SyntaxError(
                    f"Unknown command: {item} for '{name}' in {config.path}"
                )

            # Non-standard: apply `keep_going` to any task.
            if keep_going := item.get("keep_going"):
                task.keep_going = keep_going

            # `env`: https://pdm-project.org/latest/usage/scripts/#env
            if env := item.get("env"):
                assert isinstance(env, dict)
                task.env = {k: str(v) for k, v in env.items()}

            base = config.path.parent if config.path else Path.cwd()

            # `env_file`: https://pdm-project.org/latest/usage/scripts/#env_file
            if env_file := item.get("env_file"):
                task.env_file = (base / env_file).resolve()
                # Not supported: `env_file.override`

            # `working_dir`: https://pdm-project.org/latest/usage/scripts/#working_dir
            # Relative paths are resolved against the project root.
            if cwd := item.get("working_dir"):
                task.cwd = (config.path.parent / cwd).resolve()

            # Not Supported: `site_packages`

        else:
            raise TypeError(f"Unknown type: {type(item)} for '{name}' in {config.path}")

        if name == TASK_SHARED:
            common = task
        else:
            tasks[task.name] = task

    # Shared Options: https://pdm-project.org/latest/usage/scripts/#shared-options
    if common:
        for task in tasks.values():
            task.keep_going = task.keep_going or common.keep_going
            task.env = {**common.env, **task.env}
            task.env_file = task.env_file or common.env_file
            task.cwd = task.cwd or common.cwd

    # Arguments Placeholder: https://pdm-project.org/latest/usage/scripts/#arguments-placeholder
    # handled by the runner

    # Not Supported: `pdm` placeholder: https://pdm-project.org/latest/usage/scripts/#pdm-placeholder

    return tasks
