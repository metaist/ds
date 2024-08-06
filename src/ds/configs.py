"""Find and parse configuration files."""

# std
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple
import json
import sys

# TODO 2026-10-04 [3.10 EOL]: remove conditional
if sys.version_info >= (3, 11):  # pragma: no cover
    import tomllib as toml
else:  # pragma: no cover
    import tomli as toml

# pkg
from .tasks import Task
from .tasks import PREFIX_DISABLED

Tasks = Dict[str, Task]
"""Mapping a task name to a `Task`."""

Loader = Callable[[str], Dict[str, Any]]
"""A loader takes text and returns a mapping of strings to values."""

LOADERS: Dict[str, Loader] = {".toml": toml.loads, ".json": json.loads}
"""Mapping of file extensions to string load functions."""

KEY_DELIMITER = "."
"""Separator between parts of keys."""

PREFIX_EXCLUDE_GLOB = "!"
"""Prefix to exclude a glob match."""

# NOTE: Used by cog in README.md
SEARCH_FILES = [
    "ds.toml",
    ".ds.toml",
    "Cargo.toml",
    "composer.json",
    "package.json",
    "pyproject.toml",
]
"""Search order for configuration file names."""

# NOTE: Used by cog in README.md
SEARCH_KEYS = [
    "scripts",  # ds.toml, .ds.toml, package.json, composer.json
    "tool.ds.scripts",  # pyproject.toml
    "tool.pdm.scripts",  # pyproject.toml
    "tool.rye.scripts",  # pyproject.toml
    "package.metadata.scripts",  # Cargo.toml
    "workspace.metadata.scripts",  # Cargo.toml
]
"""Search order for configuration keys."""

SEARCH_KEYS_WORKSPACE = [
    "workspaces",  # ds.toml, .ds.toml, package.json
    "tool.ds.workspace.members",  # project.toml
    "tool.rye.workspace.members",  # pyproject.toml
    "workspace.members",  # Cargo.toml
]
"""Search for workspace configuration keys."""


@dataclass
class Config:
    """ds configuration."""

    path: Path
    """Path to the configuration file."""

    config: Dict[str, Any]
    """Configuration data."""

    tasks: Dict[str, Task] = field(default_factory=dict)
    """Task definitions."""

    members: List[Path] = field(default_factory=list)
    """List of workspace members."""

    @staticmethod
    def load(path: Path) -> Config:
        """Try to load a configuration file."""
        if path.suffix not in LOADERS:
            raise LookupError(f"Not sure how to read a {path.suffix} file: {path}")

        config = LOADERS[path.suffix](path.read_text())
        return Config(path, config)

    def parse(self, require_workspace: bool = False) -> Config:
        """Parse a configuration file."""
        found, self.members = parse_workspace(self.path.parent, self.config)
        if require_workspace and not found:
            raise LookupError("Could not find workspace configuration.")

        found, self.tasks = parse_tasks(self.config)
        if not require_workspace and not found:
            raise LookupError("Could not find task configuration.")

        return self


def get_path(src: Dict[str, Any], name: str, default: Optional[Any] = None) -> Any:
    """Return value of `name` within `src` or `default` if it's missing."""
    path = name.split(KEY_DELIMITER)
    result: Any = default
    try:
        for key in path:
            result = src[key]  # take step
            src = result  # preserve context
    except (KeyError, IndexError, TypeError):
        # key doesn't exist, index is unreachable, or item is not indexable
        result = default
    return result


def match_glob(
    path: Path, patterns: List[str], cache: Optional[Dict[Path, bool]] = None
) -> Dict[Path, bool]:
    """Return glob matches."""
    cache = cache or {}
    for pattern in patterns:
        include = True
        if pattern.startswith(PREFIX_EXCLUDE_GLOB):
            include = False
            pattern = pattern[len(PREFIX_EXCLUDE_GLOB) :]
        for match in sorted(path.glob(pattern)):
            cache[match] = include
    return cache


def parse_workspace(path: Path, config: Dict[str, Any]) -> Tuple[bool, List[Path]]:
    """Parse workspace configurations."""
    found = False
    members: List[Path] = []
    key = ""
    patterns: List[str] = []
    for key in SEARCH_KEYS_WORKSPACE:
        patterns = get_path(config, key)
        if patterns is not None:
            found = True
            break
    if not found:
        return found, members

    member_map = match_glob(path, patterns)

    # special case: Cargo.toml exclude patterns
    if KEY_DELIMITER in key:
        parts = key.split(KEY_DELIMITER)
        parts[-1] = "exclude"
        patterns = get_path(config, KEY_DELIMITER.join(parts))
        if patterns:
            patterns = [f"!{p}" for p in patterns]  # remove all these
            member_map = match_glob(path, patterns, member_map)

    members = [p for p, include in member_map.items() if include]
    return found, members


def parse_tasks(config: Dict[str, Any]) -> Tuple[bool, Tasks]:
    """Parse task configurations."""
    found = False
    tasks: Tasks = {}
    key, section = "", {}
    for key in SEARCH_KEYS:
        section = get_path(config, key)
        if section is not None:
            found = True
            break

    if not found:
        return found, tasks

    assert isinstance(section, Mapping)
    for name, cmd in section.items():
        name = name.strip()
        if not name or name.startswith(PREFIX_DISABLED):
            continue

        # special case: rye bare cmd as list
        if key == "tool.rye.scripts" and isinstance(cmd, list):
            cmd = {"cmd": cmd}

        task = Task.parse(cmd)
        task.name = name
        tasks[name] = task

    return found, tasks


def find_config(
    start: Path, require_workspace: bool = False, debug: bool = False
) -> Config:
    """Return the config file in `start` or its parents."""
    for path in (start / "x").resolve().parents:  # to include start
        for name in SEARCH_FILES:
            check = path / name
            if debug:
                print("check", check.resolve())
            if not check.exists():
                continue
            try:
                return Config.load(check).parse(require_workspace)
            except LookupError:  # pragma: no cover
                continue  # No valid sections.
    raise FileNotFoundError("No valid configuration file found.")
