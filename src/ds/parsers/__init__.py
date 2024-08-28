"""Parsers for supported formats."""

# std
from __future__ import annotations
from fnmatch import fnmatch
from pathlib import Path
from types import ModuleType
from typing import Dict
import logging

# pkg
from . import cargo_toml
from . import composer_json
from . import ds_toml
from . import makefile
from . import package_json
from . import pyproject_toml
from . import uv_toml
from ..configs import Config
from ..searchers import glob_parents


log = logging.getLogger(__name__)

PARSERS_CORE: Dict[str, ModuleType] = {
    "ds.toml": ds_toml,
    "pyproject.toml": pyproject_toml,
    "uv.toml": uv_toml,
    "package.json": package_json,
    "Cargo.toml": cargo_toml,
    "composer.json": composer_json,
    "[Mm]akefile": makefile,
}
"""Parsers for specific file names."""

PARSERS_GENERIC: Dict[str, ModuleType] = {
    "*.toml": ds_toml,
    "*.json": package_json,
}
"""Generic parsers."""

PARSERS = {**PARSERS_CORE, **PARSERS_GENERIC}
"""Combined parsers."""


def parse(path: Path, require_workspace: bool = False) -> Config:
    """Parse a config file."""
    text = path.read_text()
    config = Config(path, {})
    is_loaded = False
    for pattern, parser in PARSERS.items():
        if not fnmatch(path.name, pattern):
            continue

        config.data = parser.loads(text)
        is_loaded = True
        # properly parsed data

        try:
            config.members = parser.parse_workspace(config)
        except (NotImplementedError, KeyError, TypeError):
            if require_workspace:
                raise LookupError(f"No workspace found in: {path}")
        # have workspace or don't need it

        try:
            config.tasks = parser.parse_tasks(config)
        except (NotImplementedError, KeyError, TypeError):
            if not require_workspace:
                raise LookupError(f"No tasks found in: {path}")
        # have tasks or don't need them
        break  # don't try other patterns

    if not is_loaded:
        raise LookupError(f"No parser found for: {path}")

    return config


def find_and_parse(start: Path, require_workspace: bool = False) -> Config:
    """Return the config file in `start` or its parents."""
    for _, check in glob_parents(start, {pattern: pattern for pattern in PARSERS}):
        try:
            return parse(check, require_workspace)
        except LookupError:
            continue  # No valid sections.
    raise FileNotFoundError("No valid configuration file found.")
