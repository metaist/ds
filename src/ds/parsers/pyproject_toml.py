"""`pyproject.toml` parser."""

# std
from __future__ import annotations
from typing import Callable
from typing import Dict
import logging

# pkg
from ..configs import Config
from . import ds_toml
from ..configs import Membership
from . import pyproject_pdm
from . import pyproject_poetry
from . import pyproject_rye
from . import toml
from . import uv_toml
from ..tasks import Tasks

log = logging.getLogger(__name__)

loads = toml.loads
"""Standard `toml` parser."""


WORKSPACE_PARSERS: Dict[str, Callable[[Config, str], Membership]] = {
    "tool.ds.workspace": ds_toml.parse_workspace,
    "tool.uv.workspace": uv_toml.parse_workspace,
    "tool.rye.workspace": pyproject_rye.parse_workspace,
    "tool.pdm.workspace": pyproject_pdm.parse_workspace,  # Experimental
    "tool.poetry.workspace": pyproject_poetry.parse_workspace,  # Experimental
}
"""Locations of workspace parsers in `pyproject.toml`."""

TASK_PARSERS: Dict[str, Callable[[Config, str], Tasks]] = {
    "tool.ds.scripts": ds_toml.parse_tasks,
    "tool.rye.scripts": pyproject_rye.parse_tasks,
    "tool.pdm.scripts": pyproject_pdm.parse_tasks,
    "tool.poetry.scripts": pyproject_poetry.parse_tasks,
}
"""Locations of task parsers in `pyproject.toml`."""


def parse_workspace(config: Config) -> Membership:
    """`pyproject.toml` workspaces are tool-specific."""
    for key, parser in WORKSPACE_PARSERS.items():
        log.debug(f"Trying to find {key} in {config.path}")
        try:
            return parser(config, key)
        except (KeyError, NotImplementedError):
            continue
    raise KeyError(f"Missing workspace key in {config.path}")


def parse_tasks(config: Config) -> Tasks:
    """`pyproject.toml` tasks are tool-specific."""
    for key, parser in TASK_PARSERS.items():
        log.debug(f"Trying to find {key} in {config.path}")
        try:
            return parser(config, key)
        except (KeyError, NotImplementedError):
            continue
    raise KeyError(f"Missing tasks key in {config.path}")
