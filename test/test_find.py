"""Test finding configuration files."""

# std
from pathlib import Path

# lib
import pytest

# pkg
from ds.configs import find_config


def test_no_config() -> None:
    """Fail to find a config."""
    with pytest.raises(FileNotFoundError):
        assert find_config(Path("/")) is None

    with pytest.raises(FileNotFoundError):
        assert find_config(Path("/"), debug=True) is None


def test_find_config() -> None:
    """Successfully find a config."""
    assert find_config(Path(__file__)) is not None
