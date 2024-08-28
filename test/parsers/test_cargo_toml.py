"""Test `Cargo.toml` parser."""

# std
from dataclasses import replace
from pathlib import Path

# lib
import pytest

# pkg
from . import EXAMPLE_WORKSPACE
from . import nest
from ds.args import Args
from ds.parsers import Config
from ds.parsers.cargo_toml import loads
from ds.parsers.cargo_toml import parse_tasks
from ds.parsers.cargo_toml import parse_workspace
from ds.tasks import Task

PATH = Path("Cargo.toml")
"""Default path."""

TASK = Task(origin=PATH, origin_key="package.metadata.scripts")
"""Default task data."""


def test_workspace() -> None:
    """End-to-end test of workspace config."""
    path = EXAMPLE_WORKSPACE / "Cargo.toml"
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
        parse_workspace(Config(PATH, {}))


def test_workspace_empty() -> None:
    """Empty workspace."""
    data = nest("workspace", {})
    assert parse_workspace(Config(PATH, data)) == {}


def test_workspace_basic() -> None:
    """Workspace members."""
    path = EXAMPLE_WORKSPACE / "Cargo.toml"
    data = nest("workspace", {"members": ["members/*"], "exclude": ["members/x"]})
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        path.parent / "members" / "x": False,  # members/x is excluded
    }
    assert parse_workspace(Config(path, data)) == expected


def test_tasks_missing() -> None:
    """Missing tasks."""
    args = Args()
    config = Config(PATH, {})
    with pytest.raises(KeyError):
        parse_tasks(args, config)


def test_tasks() -> None:
    """Test parsing tasks."""
    args = Args()
    config = Config(PATH, nest("workspace.metadata.scripts", {"a": "b"}))
    expected = {
        "a": replace(TASK, origin_key="workspace.metadata.scripts", name="a", cmd="b")
    }
    assert parse_tasks(args, config) == expected

    args = Args()
    config = Config(PATH, nest("package.metadata.scripts", {"a": "b"}))
    expected = {
        "a": replace(TASK, origin_key="package.metadata.scripts", name="a", cmd="b")
    }
    assert parse_tasks(args, config) == expected
