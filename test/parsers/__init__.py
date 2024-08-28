"""Common parser testing tools."""

# std
from pathlib import Path
from typing import Any
from typing import Dict
from typing import cast

# pkg
from ds.symbols import KEY_DELIMITER


EXAMPLES = Path(__file__).parent.parent.parent / "examples"
"""Path to examples folder."""

EXAMPLE_WORKSPACE = EXAMPLES / "workspace"
"""Path to example workspaces."""

EXAMPLE_FORMATS = EXAMPLES / "formats"
"""Path to example formats."""


def nest(key: str, value: Any) -> Dict[str, Any]:
    """Nest keys in some levels.

    >>> nest("x.y.z", {"key": "value"})
    {'x': {'y': {'z': {'key': 'value'}}}}
    """
    result = value
    for part in reversed(key.split(KEY_DELIMITER)):
        result = {part: result}
    return cast(Dict[str, Any], result)  # even a blank string gets nested
