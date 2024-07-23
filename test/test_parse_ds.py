"""Test ds.toml parser."""

# lib
import pytest

# pkg
from ds import parse_ds


def test_empty() -> None:
    """Parse an empty file."""
    assert parse_ds({}) == {}


def test_basic() -> None:
    """Parse basic commands."""
    assert parse_ds({"scripts": {"ls": "ls -la"}}) == {"ls": "ls -la"}
    assert parse_ds({"scripts": {"all": ["clean", "build"]}}) == {
        "all": ["clean", "build"]
    }


def test_error() -> None:
    """Handle bad types."""
    with pytest.raises(ValueError):
        parse_ds({"scripts": {"foo": False}})
