"""Find and parse configuration files."""

# std
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

    tasks: Dict[str, Task] = field(default_factory=dict)
    """Task definitions."""

    members: List[Path] = field(default_factory=list)
    """List of workspace members."""


def get_path(src: Dict[str, Any], name: str, default: Optional[Any] = None) -> Any:
    """Return value of `name` within `src` or `default` if it's missing."""
    path = name.split(".")
    result: Any = default
    try:
        for key in path:
            result = src[key]  # take step
            src = result  # preserve context
    except (KeyError, IndexError, TypeError):
        # key doesn't exist, index is unreachable, or item is not indexable
        result = default
    return result


def parse_config(config: Dict[str, Any], keys: Optional[List[str]] = None) -> Tasks:
    """Parse a configuration file."""
    result = {}
    found = False
    for key in keys or SEARCH_KEYS:
        section = get_path(config, key)
        if section is not None:
            assert isinstance(section, Mapping)
            found = True
            for name, cmd in section.items():
                name = name.strip()
                if not name or name.startswith(PREFIX_DISABLED):
                    continue
                task = Task.parse(cmd)
                task.name = name
                result[name] = task
            break
    if not found:
        raise LookupError(f"Could not find one of: {', '.join(keys or SEARCH_KEYS)}")
    return result


def load_config(path: Path, keys: Optional[List[str]] = None) -> Tasks:
    """Load and parse the configuration file."""
    if path.suffix not in LOADERS:
        raise LookupError(f"Not sure how to read a {path.suffix} file: {path}")

    config = LOADERS[path.suffix](path.read_text())
    return parse_config(config, keys)


def find_config(
    start: Path, keys: Optional[List[str]] = None, debug: bool = False
) -> Tuple[Path, Tasks]:
    """Return the config file in `start` or its parents."""
    for path in (start / "x").resolve().parents:  # to include start
        for name in SEARCH_FILES:
            check = path / name
            if debug:
                print("check", check.resolve())
            if check.exists():
                try:
                    return check, load_config(check, keys)
                except LookupError:  # pragma: no cover
                    # No valid sections.
                    continue
    raise FileNotFoundError("No valid configuration file found.")
