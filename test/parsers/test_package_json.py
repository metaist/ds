"""Test `package.json` parser."""

# std
from dataclasses import replace
from pathlib import Path

# lib
import pytest

# pkg
from . import EXAMPLE_FORMATS
from . import EXAMPLE_WORKSPACE
from . import nest
from ds.args import Args
from ds.parsers import Config
from ds.parsers.package_json import loads
from ds.parsers.package_json import parse_tasks
from ds.parsers.package_json import parse_workspace
from ds.symbols import TASK_KEEP_GOING
from ds.tasks import Task

PATH = Path("package.json")
"""Default path."""

KEY = "scripts"
"""Default key."""

TASK = Task(origin=PATH, origin_key=KEY)
"""Default task data."""


def test_workspace() -> None:
    """End-to-end test of workspace config."""
    path = EXAMPLE_WORKSPACE / "package.json"
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
    data = nest("workspaces", {})
    assert parse_workspace(Config(Path(), data)) == {}


def test_workspace_basic() -> None:
    """Workspace members using strings."""
    path = EXAMPLE_WORKSPACE / "package.json"
    data = nest("workspaces", ["members/a", "members/b", "does-not-exist"])
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        # non-existent member is skipped
    }
    assert parse_workspace(Config(path, data)) == expected


def test_workspace_glob() -> None:
    """Workspace members using globs."""
    path = EXAMPLE_WORKSPACE / "package.json"
    data = nest("workspaces", ["members/*", "!members/x"])
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        path.parent / "members" / "x": False,  # members/x is excluded
    }
    assert parse_workspace(Config(path, data)) == expected


def test_format() -> None:
    """End-to-end test of the format."""
    path = EXAMPLE_FORMATS / "package.json"
    config = Config(path, loads(path.read_text()))
    tasks = parse_tasks(config)
    assert tasks


def test_tasks_missing() -> None:
    """Missing tasks."""
    with pytest.raises(KeyError):
        parse_tasks(Config(PATH, {}))


def test_tasks_empty() -> None:
    """Empty tasks."""
    data = nest(KEY, {})
    assert parse_tasks(Config(PATH, data)) == {}


def test_task_disabled() -> None:
    """Disabled task."""
    data = nest(KEY, {"#a": "b"})
    assert parse_tasks(Config(PATH, data)) == {}


def test_task_help() -> None:
    """Task help."""
    data = nest(KEY, {"#a": "run things", "a": "b"})
    expected = {"a": replace(TASK, name="a", cmd="b", help="run things")}
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_cmd() -> None:
    """Basic task."""
    data = nest(KEY, {"a": "b"})
    expected = {"a": replace(TASK, name="a", cmd="b")}
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_args() -> None:
    """Task args."""
    # argument interpolation: via reference
    data = nest(KEY, {"a": "ls", "b": "a -lah"})
    expected = {
        "a": replace(TASK, name="a", cmd="ls"),
        "b": replace(TASK, name="b", cmd="a -lah"),
    }
    assert parse_tasks(Config(PATH, data)) == expected

    # argument interpolation: via CLI
    data = nest(KEY, {"a": "ls $1", "b": "a -lah"})
    expected = {
        "a": replace(TASK, name="a", cmd="ls $1"),
        "b": replace(TASK, name="b", cmd="a -lah"),
    }
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_reference() -> None:
    """Non-standard: task reference"""
    # task reference: apparent self-reference (but actually ok)
    data = nest(KEY, {"ls": "ls"})
    expected = {"ls": replace(TASK, name="ls", cmd="ls")}
    assert parse_tasks(Config(PATH, data)) == expected

    # task reference: loop (not ok)
    data = nest(KEY, {"a": "b", "b": "a"})
    expected = {
        "a": replace(TASK, name="a", cmd="b"),
        "b": replace(TASK, name="b", cmd="a"),
    }
    assert parse_tasks(Config(PATH, data)) == expected


def test_keep_going() -> None:
    """Not supported: error suppression"""
    data = nest(KEY, {"a": f"{TASK_KEEP_GOING}b"})
    expected = {"a": replace(TASK, name="a", cmd=f"{TASK_KEEP_GOING}b")}
    # NOTE: `keep_going` NOT set
    assert parse_tasks(Config(PATH, data)) == expected
