"""Test `pyproject.toml` parser."""

# std

# lib
import pytest

from . import EXAMPLE_FORMATS
from . import EXAMPLE_WORKSPACE

from ds.args import Args
from ds.parsers import Config
from ds.parsers.pyproject_toml import loads
from ds.parsers.pyproject_toml import parse_tasks
from ds.parsers.pyproject_toml import parse_workspace


def test_workspace() -> None:
    """Load workspace."""
    path = EXAMPLE_WORKSPACE / "pyproject-uv.toml"
    config = Config(path, loads(path.read_text()))
    expected = {
        EXAMPLE_WORKSPACE / "members" / "a": True,
        EXAMPLE_WORKSPACE / "members" / "b": True,
        EXAMPLE_WORKSPACE / "members" / "x": False,  # members/x is excluded
    }
    assert parse_workspace(config) == expected

    # using a non-workspace file
    path = EXAMPLE_FORMATS / "pyproject-ds.toml"
    config = Config(path, loads(path.read_text()))
    with pytest.raises(KeyError):
        parse_workspace(config)


def test_tasks() -> None:
    """Load tasks."""
    args = Args()
    path = EXAMPLE_FORMATS / "pyproject-ds.toml"
    config = Config(path, loads(path.read_text()))
    assert parse_tasks(args, config)

    # using a non-task file
    path = EXAMPLE_WORKSPACE / "pyproject-uv.toml"
    config = Config(path, loads(path.read_text()))
    with pytest.raises(KeyError):
        parse_tasks(args, config)
