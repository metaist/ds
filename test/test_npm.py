"""Test package.json parser."""

# lib
import pytest

# pkg
from ds import parse_npm


def test_empty() -> None:
    """Parse an empty file."""
    assert parse_npm({}) == {}
    assert parse_npm({"scripts": {"ls": ""}}) == {}  # empty
    assert parse_npm({"scripts": {"#ls": "ls -la"}}) == {}  # commented


def test_basic() -> None:
    """Parse basic commands."""
    assert parse_npm({"scripts": {"ls": "ls -la"}}) == {"ls": "ls -la"}


def test_error() -> None:
    """Handle bad types."""
    with pytest.raises(ValueError):
        parse_npm({"scripts": {"X": False}})
    with pytest.raises(ValueError):
        parse_npm({"scripts": {"X": ["A", "B", "C"]}})
