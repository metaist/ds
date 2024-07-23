"""Test generic config parsing."""

# std
from pathlib import Path

# lib
import pytest

# pkg
from ds import parse_config


def test_unknown_suffix() -> None:
    """Try to read a file with an unknown suffix."""
    with pytest.raises(ValueError):
        parse_config(Path("foo.txt"))


def test_unknown_name() -> None:
    """Try to parse a file with an unknown file name."""
    assert parse_config(Path("examples") / "unknown.json")


def test_bad_format() -> None:
    """Try to parse a file with an unknown format."""
    with pytest.raises(ValueError):
        parse_config(Path("examples") / "bad.toml")
