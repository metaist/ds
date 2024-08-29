"""`pyproject.toml` parser for `rye`."""

# std
import logging

# pkg
from ..configs import Config
from ..configs import Membership
from . import toml
from ..searchers import get_key
from ..searchers import glob_paths
from ..symbols import KEY_DELIMITER
from ..symbols import KEY_MISSING
from ..symbols import TASK_COMPOSITE
from ..symbols import TASK_DISABLED
from ..tasks import Task
from ..tasks import Tasks


log = logging.getLogger(__name__)

loads = toml.loads
"""Standard `toml` parser."""

PYTHON_CALL = "python -c 'import sys; import {pkg} as _1; sys.exit(_1.{fn})'"
"""Format for a python call."""


def parse_workspace(config: Config, key: str = "tool.rye.workspace") -> Membership:
    """Workspaces are in `tool.rye.workspace`

    See:
    - https://rye.astral.sh/guide/workspaces/
    - https://rye.astral.sh/guide/pyproject/#toolryeworkspace
    - https://rye.astral.sh/guide/pyproject/#toolryevirtual
    """
    data = get_key(config.data, key, KEY_MISSING)
    if data is KEY_MISSING:
        raise KeyError(f"Missing '{key}' key in {config.path}")

    parts = key.split(KEY_DELIMITER)
    parts[-1] = "virtual"
    is_virtual = bool(get_key(config.data, parts))

    members: Membership = {}
    if not is_virtual:
        members[config.path.parent.resolve()] = True

    if "members" in data:
        members = glob_paths(
            config.path.parent,
            data["members"],
            allow_all=False,
            allow_excludes=True,  # Non-standard: allow excludes
            allow_new=True,
            previous=members,
        )
    else:
        # https://rye.astral.sh/guide/pyproject/#toolryeworkspace
        # > By default all Python projects discovered in sub folders
        # will then become members of this workspace [...]
        for item in config.path.parent.glob("**/pyproject.toml"):
            members[item.parent] = True
    return members


def parse_tasks(config: Config, key: str = "tool.rye.scripts") -> Tasks:
    """Tasks are in `tool.rye.scripts`.

    See:
    - https://rye.astral.sh/guide/pyproject/#toolryescripts
    - https://rye.astral.sh/guide/commands/run/

    Features:
    - **Supported** (*non-standard*): disabled task
    - **Supported** (*non-standard*): `task.help` - task description
    - **Supported**: `task.cmd` - basic task
    - **Supported**: `task.args` - argument interpolation
    - **Supported**: `task.cwd` - working directory
    - **Supported**: `task.depends` - composite task
    - **Supported**: `task.env` - environments
    - Not Supported: `task.keep_going` - error suppression
    """
    data = get_key(config.data, key, KEY_MISSING)
    if data is KEY_MISSING:
        raise KeyError(f"Missing '{key}' key in {config.path}")

    tasks: Tasks = {}
    for name, item in data.items():
        # Non-standard: disabled tasks
        if name.startswith(TASK_DISABLED):
            continue

        task = Task(origin=config.path, origin_key=key, name=name)
        if isinstance(item, str):
            task.cmd = item
        elif isinstance(item, list):
            task.cmd = " ".join(item)
        elif isinstance(item, dict):
            # Non-standard: help
            if help := item.get("help"):
                task.help = help

            # `cmd`: https://rye.astral.sh/guide/pyproject/#cmd
            # The command to execute. This is either a string or an array
            # of arguments.
            if cmd := item.get("cmd"):
                task.cmd = " ".join(cmd) if isinstance(cmd, list) else cmd

            # `call`: https://rye.astral.sh/guide/pyproject/#call
            # [...] can be set instead of `cmd`` to make a command invoke
            # python functions or modules
            elif call := item.get("call"):
                task.cmd = python_call(call)

            # `chain`: https://rye.astral.sh/guide/pyproject/#chain
            # [...] can be set instead of `cmd` to make a command invoke
            # multiple other commands
            elif chain := item.get("chain"):
                for step in chain:
                    task.depends.append(
                        Task(
                            origin=config.path,
                            origin_key=key,
                            name=TASK_COMPOSITE,
                            cmd=step,
                        )
                    )

            else:  # not sure what kind of command this is
                raise SyntaxError(
                    f"Unknown command: {item} for '{name}' in {config.path}"
                )

            # `env`: https://rye.astral.sh/guide/pyproject/#env
            if env := item.get("env"):
                assert isinstance(env, dict)
                task.env = {k: str(v) for k, v in env.items()}

            # `env-file`: https://rye.astral.sh/guide/pyproject/#env-file
            # [...] points to a file that should be loaded (relative to the
            # pyproject.toml)
            if env_file := item.get("env-file"):
                task.env_file = (config.path.parent / env_file).resolve()

        else:
            raise TypeError(f"Unknown type: {type(item)} for '{name}' in {config.path}")
        tasks[task.name] = task

    return tasks


def python_call(call: str) -> str:
    """Return a formatted `call` string.

    See: https://rye.astral.sh/guide/pyproject/#call

    >>> python_call("http.server")
    'python -m http.server'

    >>> python_call("builtins:help") == PYTHON_CALL.format(pkg="builtins", fn="help()")
    True

    >>> python_call("builtins:print('Hello World!')") == PYTHON_CALL.format(
    ...     pkg="builtins", fn="print('Hello World!')")
    True
    """
    if ":" not in call:
        return f"python -m {call}"

    pkg, fn = call.split(":", 1)
    if not fn.endswith(")"):
        fn = f"{fn}()"
    return PYTHON_CALL.format(pkg=pkg, fn=fn)
