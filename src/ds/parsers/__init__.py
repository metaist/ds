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

PARSERS: Dict[str, ModuleType] = {
    "ds.toml": ds_toml,
    "pyproject.toml": pyproject_toml,
    "uv.toml": uv_toml,
    "package.json": package_json,
    "Cargo.toml": cargo_toml,
    "composer.json": composer_json,
    "[Mm]akefile": makefile,
}
"""Parsers for specific file names."""


def parse(path: Path, require_workspace: bool = False) -> Config:
    """Parse a config file."""
    text = path.read_text()
    config = Config(path, {})
    for pattern, parser in PARSERS.items():
        if not fnmatch(path.name, pattern):
            continue

        msg = ""
        config.data = parser.loads(text)  # allow failure to bubble up
        try:
            if require_workspace:
                msg = f"No workspace found in: {path}"
                config.members = parser.parse_workspace(config)
            else:
                msg = f"No tasks found in: {path}"
                config.tasks = parser.parse_tasks(config)
            return config
        except (NotImplementedError, KeyError, TypeError):
            raise LookupError(msg)
        # have workspace or don't need it

    raise LookupError(f"No parser found for: {path}")


def find_and_parse(start: Path, require_workspace: bool = False) -> Config:
    """Return the config file in `start` or its parents."""
    for _, check in glob_parents(start, {pattern: pattern for pattern in PARSERS}):
        try:
            return parse(check, require_workspace)
        except LookupError:
            continue  # No valid sections.
    raise FileNotFoundError("No valid configuration file found.")
