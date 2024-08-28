"""`ds.toml` parser."""

# std
from dataclasses import replace
from typing import Any
from typing import Dict
from typing import List
import logging

# pkg
from . import Config
from . import Membership
from . import toml
from ..args import Args
from ..searchers import get_key
from ..searchers import glob_paths
from ..symbols import GLOB_EXCLUDE
from ..symbols import KEY_MISSING
from ..symbols import starts
from ..symbols import TASK_COMPOSITE
from ..symbols import TASK_DISABLED
from ..symbols import TASK_KEEP_GOING
from ..symbols import TASK_SHARED
from ..tasks import Task
from ..tasks import Tasks
from .pyproject_rye import python_call


log = logging.getLogger(__name__)

loads = toml.loads
"""Standard `toml` parser."""


def parse_workspace(config: Config, key: str = "tool.ds.workspace") -> Membership:
    """Workspaces are in `tool.ds.workspace` (pyproject.toml) or `workspace` (ds.toml)."""
    if config.path.name == "ds.toml" and key == "tool.ds.workspace":
        key = "workspace"

    data = get_key(config.data, key, KEY_MISSING)
    if data is KEY_MISSING:
        raise KeyError(f"Missing '{key}' key in {config.path}")

    members: Membership = {}
    if "members" in data:
        members = glob_paths(
            config.path.parent,
            data["members"],
            allow_all=False,
            allow_excludes=True,  # we support excludes in members
            allow_new=True,
            previous=members,
        )

    if "exclude" in data:
        members = glob_paths(
            config.path.parent,
            [f"{GLOB_EXCLUDE}{p}" for p in data["exclude"]],
            allow_all=False,
            allow_excludes=True,
            allow_new=False,
            previous=members,
        )
    return members


def parse_tasks(args: Args, config: Config, key: str = "tool.ds.scripts") -> Tasks:
    """Tasks in `scripts`.

    Features:
    - **Supported**: disabled task
    - **Supported**: `task.help` - task description
    - **Supported**: `task.cmd` - basic task
    - **Supported**: `task.args` - argument interpolation
    - **Supported**: `task.cwd` - working directory
    - **Supported**: `task.depends` - composite task
    - **Supported**: `task.env` - environments
    - **Supported**: `task.keep_going` - error suppression
    """
    if config.path.name == "ds.toml" and key == "tool.ds.scripts":
        key = "scripts"

    data = get_key(config.data, key, KEY_MISSING)
    if data is KEY_MISSING:
        raise KeyError(f"Missing '{key}' key in {config.path}")

    common: Task = None
    tasks: Tasks = {}
    for name, item in data.items():
        if name.startswith(TASK_DISABLED):
            continue

        task = Task(origin=config.path, origin_key=key, name=name)
        if isinstance(item, str):
            task.keep_going, task.cmd = starts(item, TASK_KEEP_GOING)
        elif isinstance(item, list):
            parse_composite(task, item)
        elif isinstance(item, dict):
            try:
                rename_aliases(item, PROPERTY_ALIASES)
            except KeyError as e:
                src, dest = e.args
                raise SyntaxError(
                    f"{name} cannot contain '{dest}' and its alias '{src}': {config.path}"
                )

            if help := item.get("help"):
                task.help = help

            # unlike pdm or rye, we allow `composite` + `cmd`
            if composite := item.get("composite"):
                parse_composite(task, composite)

            if cmd := item.get("cmd"):
                task.cmd = " ".join(cmd) if isinstance(cmd, list) else cmd
                task.keep_going, task.cmd = starts(task.cmd, TASK_KEEP_GOING)
            elif call := item.get("call"):
                if config.path.name != "pyproject.toml":
                    raise SyntaxError(
                        f"'{name}' uses `call` task outside of `pyproject.toml`: {config.path}"
                    )
                task.cmd = python_call(call)

            # internal
            if verbatim := item.get("verbatim"):
                task.verbatim = verbatim

            # since keep_going might have been set elsewhere
            if keep_going := item.get("keep_going", KEY_MISSING) is not KEY_MISSING:
                task.keep_going = keep_going

            if env := item.get("env"):
                assert isinstance(env, dict)
                task.env = {k: str(v) for k, v in env.items()}

            if env_file := item.get("env_file"):
                task.env_file = (config.path.parent / env_file).resolve()
                if not task.env_file.exists():
                    log.warning(
                        f"{name}.env_file does not currently exist: {task.env_file}"
                    )

            if cwd := item.get("cwd"):
                task.cwd = (config.path.parent / cwd).resolve()
        else:
            raise SyntaxError(
                f"Unknown type: {type(item)} for '{name}' in {config.path}"
            )

        if name == TASK_SHARED:
            common = task
        else:
            tasks[task.name] = task

    if common:
        for task in tasks.values():
            task.keep_going = task.keep_going or common.keep_going
            task.env = {**common.env, **task.env}
            task.env_file = task.env_file or common.env_file
            task.cwd = task.cwd or common.cwd

    return tasks


PROPERTY_ALIASES = {
    "chain": "composite",  # pdm-style
    "env-file": "env_file",  # pdm-style
    "shell": "cmd",  # combine
    "working_dir": "cwd",  # ds-style
}
"""Aliased property names."""


def rename_aliases(
    item: Dict[str, Any], renames: Dict[str, str], overwrite: bool = False
) -> Dict[str, Any]:
    """Rename items in a dict.

    >>> rename_aliases({'old': 'value'}, {'old': 'new'})
    {'new': 'value'}

    >>> rename_aliases({'old': 'value', 'new': 'other'}, {'old': 'new'}, overwrite=True)
    {'new': 'value'}

    >>> rename_aliases({'old': 'value', 'new': 'other'}, {'old': 'new'})
    Traceback (most recent call last):
     ...
    KeyError: ('old', 'new')
    """
    for src, dest in renames.items():
        has_src = src in item
        if not has_src:
            continue

        has_dest = dest in item
        if has_src and has_dest and not overwrite:
            raise KeyError(src, dest)

        item[dest] = item.pop(src)
    return item


def parse_composite(task: Task, item: List[str]) -> Task:
    """Parse composite task."""
    depends = []
    for step in item:
        keep_going, cmd = starts(step, TASK_KEEP_GOING)
        depends.append(
            replace(task, name=TASK_COMPOSITE, cmd=cmd, keep_going=keep_going)
        )
    task.depends = depends
    return task
