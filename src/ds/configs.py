"""Configs are a path and data."""

# std
import dataclasses
from pathlib import Path
from typing import Any
from typing import Dict

# pkg
from .tasks import Tasks
from .searchers import GlobMatches

Membership = GlobMatches
"""Mapping of paths to whether they are members."""


@dataclasses.dataclass
class Config:
    """ds configuration."""

    path: Path
    """Path to the configuration file."""

    data: Dict[str, Any]
    """Configuration data."""

    # `tasks` and `members` are loaded by tool-specific parsers

    tasks: Tasks = dataclasses.field(default_factory=dict)
    """Task definitions."""

    members: Membership = dataclasses.field(default_factory=dict)
    """Workspace members mapped to `True` for active members."""
