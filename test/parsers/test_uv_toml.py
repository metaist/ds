"""Test `uv.toml` parser."""

# std
from pathlib import Path

# lib
import pytest

# pkg
from . import EXAMPLE_WORKSPACE
from . import nest
from ds.configs import Config
from ds.parsers.uv_toml import loads
from ds.parsers.uv_toml import parse_tasks
from ds.parsers.uv_toml import parse_workspace


def test_workspace() -> None:
    """End-to-end test of workspace config."""
    path = EXAMPLE_WORKSPACE / "pyproject-uv.toml"
    config = Config(path, loads(path.read_text()))
    expected = {
        EXAMPLE_WORKSPACE / "members" / "a": True,
        EXAMPLE_WORKSPACE / "members" / "b": True,
        EXAMPLE_WORKSPACE / "members" / "x": False,  # members/x is excluded
    }
    assert parse_workspace(config) == expected


def test_workspace_missing() -> None:
    """Missing workspace."""
    with pytest.raises(KeyError):
        parse_workspace(Config(Path(), {}))


def test_workspace_empty() -> None:
    """Empty workspace."""
    data = nest("tool.uv.workspace", {})
    assert parse_workspace(Config(Path("pyproject.toml"), data)) == {}

    data = nest("workspace", {})
    assert parse_workspace(Config(Path("uv.toml"), data)) == {}


def test_workspace_basic1() -> None:
    """Workspace members using `pyproject.toml` style."""
    path = EXAMPLE_WORKSPACE / "pyproject.toml"
    data = nest(
        "tool.uv.workspace", {"members": ["members/*"], "exclude": ["members/x"]}
    )
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        path.parent / "members" / "x": False,  # members/x is excluded
    }
    assert parse_workspace(Config(path, data)) == expected


def test_workspace_basic2() -> None:
    """Workspace members using `uv.toml` style."""
    path = EXAMPLE_WORKSPACE / "uv.toml"
    data = nest("workspace", {"members": ["members/*"], "exclude": ["members/x"]})
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        path.parent / "members" / "x": False,  # members/x is excluded
    }
    assert parse_workspace(Config(path, data)) == expected


def test_tasks_not_implemented() -> None:
    """Tasks are not implemented."""
    config = Config(Path("pyproject.toml"), {})
    with pytest.raises(NotImplementedError):
        parse_tasks(config)
