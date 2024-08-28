"""Common parser testing tools."""

# std
from pathlib import Path
from types import ModuleType
from typing import Any
from typing import cast
from typing import Dict

# pkg
from ds.parsers import ds_toml
from ds.parsers import PARSERS
from ds.parsers import PARSERS_CORE
from ds.parsers import PARSERS_GENERIC
from ds.parsers import pyproject_pdm
from ds.parsers import pyproject_poetry
from ds.parsers import pyproject_rye
from ds.parsers import uv_toml
from ds.symbols import KEY_DELIMITER

EXAMPLES = Path(__file__).parent.parent.parent / "examples"
"""Path to examples folder."""

EXAMPLE_WORKSPACE = EXAMPLES / "workspace"
"""Path to example workspaces."""

EXAMPLE_FORMATS = EXAMPLES / "formats"
"""Path to example formats."""

PARSERS_TEST: Dict[str, ModuleType] = {
    "pyproject-ds*.toml": ds_toml,
    "pyproject-pdm*.toml": pyproject_pdm,
    "pyproject-poetry*.toml": pyproject_poetry,
    "pyproject-rye*.toml": pyproject_rye,
    "pyproject-uv*.toml": uv_toml,
}
"""Parsers for test files."""

PARSERS.clear()
PARSERS.update({**PARSERS_CORE, **PARSERS_TEST, **PARSERS_GENERIC})


def nest(key: str, value: Any) -> Dict[str, Any]:
    """Nest keys in some levels.

    >>> nest("x.y.z", {"key": "value"})
    {'x': {'y': {'z': {'key': 'value'}}}}
    """
    result = value
    for part in reversed(key.split(KEY_DELIMITER)):
        result = {part: result}
    return cast(Dict[str, Any], result)  # even a blank string gets nested
