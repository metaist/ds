"""Parsers for supported formats."""

# std
from __future__ import annotations
from fnmatch import fnmatch
from pathlib import Path
from types import ModuleType
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
import dataclasses
import json
import logging

# pkg
from . import toml
from ..searchers import get_key
from ..searchers import glob_parents
from ..searchers import glob_paths
from ..searchers import GlobMatches
from ..symbols import GLOB_EXCLUDE
from ..symbols import KEY_DELIMITER
from ..symbols import TASK_DISABLED
from ..tasks import parse_task
from ..tasks import Tasks

log = logging.getLogger(__name__)


Loader = Callable[[str], Dict[str, Any]]
"""A loader takes text and returns a mapping of strings to values."""

FILE_LOADERS: Dict[str, ModuleType] = {}
"""Mapping of file pattern to module that handles that pattern."""

Membership = Dict[Path, bool]
"""Mapping of paths to whether they are members."""

# NOTE: Used by cog in README.md
SEARCH_FILES = [
    "ds.toml",
    "pyproject.toml",  # python
    "package.json",  # node
    "Cargo.toml",  # rust
    "composer.json",  # php
    "[Mm]akefile",
    ".ds.toml",
]
"""Search order for configuration file names."""

# NOTE: Used by cog in README.md
SEARCH_KEYS_TASKS = [
    "scripts",  # ds.toml, .ds.toml, package.json, composer.json
    "tool.ds.scripts",  # pyproject.toml
    "tool.pdm.scripts",  # pyproject.toml
    "tool.rye.scripts",  # pyproject.toml
    "package.metadata.scripts",  # Cargo.toml
    "workspace.metadata.scripts",  # Cargo.toml
    "Makefile",  # Makefile
]
"""Search order for configuration keys."""

# NOTE: Used by cog in README.md
SEARCH_KEYS_WORKSPACE = [
    "workspace.members",  # ds.toml, .ds.toml, Cargo.toml
    "tool.ds.workspace.members",  # project.toml
    "tool.rye.workspace.members",  # pyproject.toml
    "tool.uv.workspace.members",  # pyproject.toml
    "workspaces",  # package.json
]
"""Search for workspace configuration keys."""


@dataclasses.dataclass
class Config:
    """ds configuration."""

    path: Path
    """Path to the configuration file."""

    data: Dict[str, Any]
    """Configuration data."""

    tasks: Tasks = dataclasses.field(default_factory=dict)
    """Task definitions."""

    members: GlobMatches = dataclasses.field(default_factory=dict)
    """Workspace members mapped to `True` for active members."""

    @staticmethod
    def find(start: Path, require_workspace: bool = False) -> Config:
        """Return the config file in `start` or its parents."""
        log.debug(f"require_workspace={require_workspace}")
        for _, check in glob_parents(start, {v: v for v in SEARCH_FILES}):
            try:
                return Config.load(check).parse(require_workspace)
            except LookupError:
                continue  # No valid sections.
        raise FileNotFoundError("No valid configuration file found.")

    @staticmethod
    def load(path: Path) -> Config:
        """Try to load a configuration file."""
        for pattern, loader in LOADERS.items():
            if fnmatch(path.name, pattern):
                return Config(path, loader(path.read_text()))
        raise LookupError(f"Not sure how to read file: {path}")

    def parse(self, require_workspace: bool = False) -> Config:
        """Parse a configuration file."""
        found, self.members = parse_workspace(self.path.parent, self.data)
        if require_workspace and not found:
            raise LookupError("Could not find workspace configuration.")

        found, self.tasks = parse_tasks(self.data, self.path)
        if not require_workspace and not found:
            raise LookupError("Could not find task configuration.")

        return self


def parse_workspace(
    path: Path, config: Dict[str, Any]
) -> Tuple[bool, Dict[Path, bool]]:
    """Parse workspace configurations."""
    found = False
    members: Dict[Path, bool] = {}
    key = ""
    patterns: List[str] = []
    for key in SEARCH_KEYS_WORKSPACE:
        patterns = get_key(config, key)
        if patterns is not None:
            found = True
            break
    if not found:
        return found, members

    members = glob_paths(
        path, patterns, allow_all=False, allow_excludes=True, allow_new=True
    )

    # special case: Cargo.toml exclude patterns
    if KEY_DELIMITER in key:
        patterns = get_key(config, key.split(KEY_DELIMITER)[:-1] + ["exclude"])
        if patterns:  # remove all of these
            patterns = [f"{GLOB_EXCLUDE}{p}" for p in patterns]
            members = glob_paths(
                path,
                patterns,
                allow_all=True,
                allow_excludes=True,
                allow_new=False,
                previous=members,
            )
    return found, members


def parse_tasks(
    config: Dict[str, Any], origin: Optional[Path] = None
) -> Tuple[bool, Tasks]:
    """Parse task configurations."""
    found = False
    tasks: Tasks = {}
    key, section = "", {}
    for key in SEARCH_KEYS_TASKS:
        section = get_key(config, key)
        if section is not None:
            found = True
            break

    if not found:
        return found, tasks

    assert isinstance(section, Dict)
    for name, cmd in section.items():
        name = str(name).strip()
        if not name or name.startswith(TASK_DISABLED):
            continue

        # special case: rye bare cmd as list
        if key == "tool.rye.scripts" and isinstance(cmd, list):
            cmd = {"cmd": cmd}

        task = parse_task(cmd, origin, key)
        task.name = name
        tasks[name] = task

    return found, tasks


from . import cargo_toml  # noqa: E402
from . import composer_json  # noqa: E402
from . import ds_toml  # noqa: E402
from . import makefile  # noqa: E402
from . import package_json  # noqa: E402
from . import pyproject_toml  # noqa: E402
from . import uv_toml  # noqa: E402

PARSERS = {
    "ds.toml": ds_toml,
    "pyproject.toml": pyproject_toml,
    "uv.toml": uv_toml,
    "package.json": package_json,
    "Cargo.toml": cargo_toml,
    "composer.json": composer_json,
    "[Mm]akefile": makefile,
}

LOADERS: Dict[str, Loader] = {
    "*.json": json.loads,
    "*.toml": toml.loads,
    "*[Mm]akefile": makefile.loads,
}
"""Mapping of file patterns to load functions."""
