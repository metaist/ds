"""Test env vars and interpolation."""

# std
from typing import Union
from typing import Optional

# lib
import pytest

# pkg
from ds.env import interpolate_args
from ds.symbols import ARG_PREFIX
from ds.symbols import ARG_REST


def arg(
    n: Union[int, str, None] = None,
    b: bool = False,
    d: Optional[str] = None,
) -> str:
    """Helper to produce args.

    >>> arg(1)
    '$1'
    >>> arg()
    '$@'

    Add braces:
    >>> arg(2, b=True)
    '${2}'

    Provide defaults:
    >>> arg(d="")
    '${@:-}'
    """
    name = n or ARG_REST
    if d is not None:
        b = True
        name = f"{name}:-{d}"
    return f"{ARG_PREFIX}{{{name}}}" if b else f"{ARG_PREFIX}{name}"


def test_interpolate_args() -> None:
    """Interpolate args properly."""
    assert interpolate_args("a b", ["c"]) == "a b c"
    assert interpolate_args(f"a {arg(1)} c", ["b"]) == "a b c"
    assert (
        interpolate_args(
            f"a {arg(1)} {arg(b=True)} {arg(3)} {arg()}",
            ["b", "c", "d"],
        )
        == "a b c d d c"
    )


def test_missing_args() -> None:
    """Try to interpolate with insufficient args."""
    with pytest.raises(IndexError):
        interpolate_args(f"ls {arg(1)}", [])


def test_default_args() -> None:
    """Add a default value for a missing arg."""
    cmd = f"ls {arg(1, d='foo')}"
    assert interpolate_args(cmd, []) == "ls foo"
    assert interpolate_args(cmd, ["bar"]) == "ls bar"
    assert interpolate_args(cmd, [""]) == "ls"
