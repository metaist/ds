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
from typing import Optional
from typing import Tuple
from typing import Union
import json
import sys

# TODO 2026-10-04 [3.10 EOL]: remove conditional
if sys.version_info >= (3, 11):  # pragma: no cover
    import tomllib as toml
else:  # pragma: no cover
    import tomli as toml

# pkg
from .symbols import GLOB_ALL
from .symbols import GLOB_EXCLUDE
from .symbols import KEY_DELIMITER
from .symbols import starts
from .symbols import TASK_DISABLED
from .tasks import Task
from .tasks import Tasks

GlobMatches = Dict[Path, bool]
"""Mapping a path to whether it should be included."""

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
SEARCH_KEYS_TASKS = [
    "scripts",  # ds.toml, .ds.toml, package.json, composer.json
    "tool.ds.scripts",  # pyproject.toml
    "tool.pdm.scripts",  # pyproject.toml
    "tool.rye.scripts",  # pyproject.toml
    "package.metadata.scripts",  # Cargo.toml
    "workspace.metadata.scripts",  # Cargo.toml
]
"""Search order for configuration keys."""

# NOTE: Used by cog in README.md
SEARCH_KEYS_WORKSPACE = [
    "workspace.members",  # ds.toml, .ds.toml, Cargo.toml
    "tool.ds.workspace.members",  # project.toml
    "tool.rye.workspace.members",  # pyproject.toml
    "workspaces",  # package.json
]
"""Search for workspace configuration keys."""


@dataclass
class Config:
    """ds configuration."""

    path: Path
    """Path to the configuration file."""

    config: Dict[str, Any]
    """Configuration data."""

    tasks: Tasks = field(default_factory=dict)
    """Task definitions."""

    members: GlobMatches = field(default_factory=dict)
    """Workspace members mapped to `True` for active members."""

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


def get_path(
    src: Dict[str, Any], name: Union[str, List[str]], default: Optional[Any] = None
) -> Any:
    """Return value of `name` within `src` or `default` if it's missing.

    >>> get_path({"a": {"b": {"c": 1}}}, "a.b.c") == 1
    True
    >>> get_path({"a": {"b": {"c": 1}}}, ["a", "b", "c"]) == 1
    True
    """
    path: List[str] = []
    if isinstance(name, str):
        path = name.split(KEY_DELIMITER)
    elif isinstance(name, list):
        path = name
    else:  # pragma: no cover
        raise TypeError("Unknown type of key:", type(name))

    result: Any = default
    try:
        for key in path:
            result = src[key]  # take step
            src = result  # preserve context
    except (KeyError, IndexError, TypeError):
        # key doesn't exist, index is unreachable, or item is not indexable
        result = default
    return result


def glob_apply(
    path: Path, patterns: List[str], matches: Optional[GlobMatches] = None
) -> GlobMatches:
    """Apply glob `patterns` to `path`."""
    result = {} if not matches else matches.copy()
    for pattern in patterns:
        exclude, pattern = starts(pattern, GLOB_EXCLUDE)
        for match in sorted(path.glob(pattern)):
            result[match] = not exclude
    return result


def glob_refine(path: Path, patterns: List[str], matches: GlobMatches) -> GlobMatches:
    """Apply glob-like `patterns` to `path` to refine `matches`."""
    result = matches.copy()
    for pattern in patterns:
        exclude, pattern = starts(pattern, GLOB_EXCLUDE)
        if pattern == GLOB_ALL:
            for match in result:
                result[match] = not exclude
            continue

        for match in sorted(path.glob(pattern)):
            if match in result:  # no new entries
                result[match] = not exclude
    return result


def parse_workspace(
    path: Path, config: Dict[str, Any]
) -> Tuple[bool, Dict[Path, bool]]:
    """Parse workspace configurations."""
    found = False
    members: Dict[Path, bool] = {}
    key = ""
    patterns: List[str] = []
    for key in SEARCH_KEYS_WORKSPACE:
        patterns = get_path(config, key)
        if patterns is not None:
            found = True
            break
    if not found:
        return found, members

    members = glob_apply(path, patterns)

    # special case: Cargo.toml exclude patterns
    if KEY_DELIMITER in key:
        patterns = get_path(config, key.split(KEY_DELIMITER)[:-1] + ["exclude"])
        if patterns:  # remove all of these
            patterns = [f"{GLOB_EXCLUDE}{p}" for p in patterns]
            members = glob_apply(path, patterns, members)
    return found, members


def parse_tasks(config: Dict[str, Any]) -> Tuple[bool, Tasks]:
    """Parse task configurations."""
    found = False
    tasks: Tasks = {}
    key, section = "", {}
    for key in SEARCH_KEYS_TASKS:
        section = get_path(config, key)
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

        task = Task.parse(cmd)
        task.name = name
        tasks[name] = task

    return found, tasks


def find_config(
    start: Path, require_workspace: bool = False, debug: bool = False
) -> Config:
    """Return the config file in `start` or its parents."""
    if debug:
        print(f"find_config: require_workspace={require_workspace}")
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
