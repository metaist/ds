"""Test env vars and interpolation."""

# lib
import pytest

# pkg
from ds.env import interpolate_args


def test_interpolate_args() -> None:
    """Interpolate args properly."""
    assert interpolate_args("a ${1} c", ["b"]) == "a b c"
    assert interpolate_args("a $1 ${@} $3 $@", ["b", "c", "d"]) == "a b c d d c"


def test_missing_args() -> None:
    """Try to parse a command with insufficient args."""
    with pytest.raises(IndexError):
        interpolate_args("ls $1", [])


def test_default_args() -> None:
    """Add a default value for a missing arg."""
    assert interpolate_args("ls ${1:-foo}", []) == "ls foo"
    assert interpolate_args("ls ${1:-foo}", ["bar"]) == "ls bar"
    assert interpolate_args("ls ${1:-foo}", [""]) == "ls"
