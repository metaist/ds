"""`composer.json` parser."""

# std
import json
import logging
import re

# pkg
from ..configs import Config
from ..configs import Membership
from ..searchers import get_key
from ..symbols import KEY_MISSING
from ..symbols import TASK_DISABLED
from ..symbols import TASK_COMPOSITE
from ..symbols import TASK_KEEP_GOING
from ..symbols import starts
from ..env import RE_ARGS
from ..tasks import Tasks
from ..tasks import Task


log = logging.getLogger(__name__)

loads = json.loads
"""Standard `json` parser."""

RE_PHP_CALL = re.compile(r"^[A-Z][A-Za-z0-9_\\]+(::[A-Za-z0-9_]+)?$")
"""Detect a PHP call."""

PHP_CALL = """php -r "require 'vendor/autoload.php'; {fn}();"""
"""PHP call."""

PHP_REFER = "@"
"""Reference symbol."""


def parse_workspace(config: Config, key: str = "") -> Membership:
    """Workspaces are not officially supported by `composer.json`."""
    raise NotImplementedError("composer.json does not support workspaces.")


def parse_tasks(config: Config, key: str = "scripts") -> Tasks:
    """Tasks are defined in `scripts`.

    See: https://getcomposer.org/doc/articles/scripts.md#writing-custom-commands

    Features:
    - **Supported** (*non-standard*): disabled task
    - **Supported**: `task.help` - task description
    - **Supported**: `task.cmd` - basic task
    - **Supported**: `task.args` - argument interpolation
    - Not Supported: `task.cwd` - working directory
    - **Supported**: `task.depends`
    - **Supported**: `task.env` - environments
    - Not Supported: `task.keep_going` - error suppression
    """
    data = get_key(config.data, key, KEY_MISSING)
    if data is KEY_MISSING:
        raise KeyError(f"Missing '{key}' key in {config.path}")

    log.warning("EXPERIMENTAL: Parsing `composer.json` format.")
    tasks: Tasks = {}

    # https://getcomposer.org/doc/articles/scripts.md#custom-descriptions
    descriptions = get_key(config.data, f"{key}-descriptions", {})
    for name, item in data.items():
        # Non-standard: disabled task
        if name.startswith(TASK_DISABLED):
            continue

        task = Task(origin=config.path, origin_key=key, name=name)
        task.help = descriptions.get(name, "")

        # https://getcomposer.org/doc/articles/scripts.md#defining-scripts
        # > An event's scripts can be defined as either a string
        # (only for a single script) or an array (for single or multiple
        # scripts.)

        if isinstance(item, str):
            # Not supported: error suppression
            if item.startswith(TASK_KEEP_GOING):
                log.warning(
                    "composer.json does not support error suppression."
                    f'Did you mean "{name}": "ds {item}"'
                )

            # Non-standard: argument interpolation
            if RE_ARGS.search(item):
                log.warning(
                    "composer.json does not support argument interpolation. "
                    "We'll allow it, but it may break other tools."
                )

            parse_cmd(task, item)
        elif isinstance(item, list):
            for step in item:
                # `@putenv`: https://getcomposer.org/doc/articles/scripts.md#setting-environment-variables
                is_env, rule = starts(step, "@putenv ")
                if is_env:
                    task.env.update(dict([rule.split("=", 1)]))
                else:
                    sub = Task(origin=config.path, origin_key=key, name=TASK_COMPOSITE)
                    task.depends.append(parse_cmd(sub, step))
        else:
            raise TypeError(f"Unknown type: {type(item)} for '{name}' in {config.path}")

        tasks[task.name] = task

    # https://getcomposer.org/doc/articles/scripts.md#custom-aliases
    aliases = get_key(config.data, f"{key}-aliases", {})
    for target, names in aliases.items():
        for name in names:
            tasks[name] = Task(
                origin=config.path,
                origin_key=f"{key}-aliases",
                name=name,
                depends=[
                    Task(
                        origin=config.path,
                        origin_key=key,
                        name=TASK_COMPOSITE,
                        cmd=target,
                    )
                ],
            )

    return tasks


def php_call(cmd: str) -> str:
    """Format a PHP call."""
    # TODO: There must be some other way that composer is making this decision.
    if not RE_PHP_CALL.match(cmd):
        return cmd
    return PHP_CALL.format(fn=cmd)


def parse_cmd(task: Task, cmd: str) -> Task:
    """Parse a command."""
    # `@` reference: https://getcomposer.org/doc/articles/scripts.md#referencing-scripts
    # `@composer`: https://getcomposer.org/doc/articles/scripts.md#calling-composer-commands
    # `@php`: https://getcomposer.org/doc/articles/scripts.md#executing-php-scripts
    is_refer, cmd = starts(cmd, PHP_REFER)
    if is_refer:
        task.depends.append(
            Task(
                origin=task.origin,
                origin_key=task.origin_key,
                name=TASK_COMPOSITE,
                cmd=cmd,
            )
        )
    else:
        task.cmd = php_call(cmd)
    return task
