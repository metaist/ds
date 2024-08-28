"""`pyproject.toml` parser for `poetry`."""

# std
import logging

# pkg
from . import cargo_toml
from ..configs import Config
from ..configs import Membership
from . import toml
from ..searchers import get_key
from ..symbols import KEY_MISSING
from ..tasks import Task
from ..tasks import Tasks
from .pyproject_rye import PYTHON_CALL


log = logging.getLogger(__name__)

loads = toml.loads
"""Standard `toml` parser."""


def parse_workspace(config: Config, key: str = "tool.poetry.workspace") -> Membership:
    """Workspaces are not officially defined for `poetry`.

    There are two plugins that have two different patterns:
    - https://github.com/jacksmith15/poetry-workspace-plugin
    - https://pypi.org/project/poetry-workspace-plugin2/
    """
    data = get_key(config.data, key, KEY_MISSING)
    if data is KEY_MISSING:
        raise KeyError(f"Missing '{key}' key in {config.path}")

    log.warning("EXPERIMENTAL: parsing tool.poetry.workspace")
    members: Membership = {}
    if "include" in data:
        # https://pypi.org/project/poetry-workspace-plugin2/
        # Cargo-style (include + exclude)
        data["members"] = data["include"]
        members = cargo_toml.parse_workspace(config, key)
    else:
        # https://github.com/jacksmith15/poetry-workspace-plugin
        for path in data.values():
            check = config.path.parent / path
            log.debug(f"checking {check}")
            if check.exists():
                members[check] = True
    return members


def parse_tasks(config: Config, key: str = "tool.poetry.scripts") -> Tasks:
    """`poetry` only supports a `call` script.

    https://python-poetry.org/docs/cli/#run

    Features:
    - Not Supported: disabled task
    - Not Supported: `task.help` - task description
    - **Supported** (*partial*): `task.cmd` - basic task (`call` only)
    - Not Supported: `task.args` - argument interpolation
    - Not Supported: `task.cwd` - working directory
    - Not Supported: `task.depends` - composite task
    - Not Supported: `task.env` - environments
    - Not Supported: `task.keep_going` - error suppression
    """
    # https://python-poetry.org/docs/pyproject/#scripts
    data = get_key(config.data, key, KEY_MISSING)
    if data is KEY_MISSING:
        raise KeyError(f"Missing '{key}' key in {config.path}")

    tasks: Tasks = {}
    for name, script in data.items():
        # NOTE: poetry does not support passing any arguments.
        pkg, fn = script.split(":", 1)
        tasks[name] = Task(
            origin=config.path,
            origin_key=key,
            name=name,
            cmd=PYTHON_CALL.format(pkg=pkg, fn=f"{fn}()"),
        )

    return tasks
