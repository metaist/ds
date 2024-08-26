"""Test `pyproject.toml` parser using `poetry`."""

# std
from dataclasses import replace
from pathlib import Path
from typing import Any
from typing import Dict

# lib
import pytest

# pkg
from . import EXAMPLE_FORMATS
from . import EXAMPLE_WORKSPACE
from ds.args import Args
from ds.parsers import Config
from ds.parsers.pyproject_poetry import loads
from ds.parsers.pyproject_poetry import parse_tasks
from ds.parsers.pyproject_poetry import parse_workspace
from ds.parsers.pyproject_poetry import PYTHON_CALL
from ds.tasks import Task

TASK = Task(origin=Path("pyproject.toml"), origin_key="tool.poetry.scripts")
"""Default task data."""


def test_workspace() -> None:
    """End-to-end test of workspace config."""
    path = EXAMPLE_WORKSPACE / "pyproject-poetry1.toml"
    config = Config(path, loads(path.read_text()))
    expected = {
        EXAMPLE_WORKSPACE / "members" / "a": True,
        EXAMPLE_WORKSPACE / "members" / "b": True,
        # members/x is was not defined
    }
    assert parse_workspace(config) == expected

    path = EXAMPLE_WORKSPACE / "pyproject-poetry2.toml"
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
    data: Dict[str, Any] = {"tool": {"poetry": {"workspace": {}}}}
    assert parse_workspace(Config(Path(), data)) == {}


def test_workspace_basic1() -> None:
    """Workspace members using plugin 1 style."""
    path = EXAMPLE_WORKSPACE / "pyproject.toml"
    data: Dict[str, Any] = {
        "tool": {
            "poetry": {
                "workspace": {"a": "members/a", "b": "members/b", "x": "does not exist"}
            }
        }
    }
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        # non-existent member is skipped
    }
    assert parse_workspace(Config(path, data)) == expected


def test_workspace_basic2() -> None:
    """Workspace members using strings."""
    path = EXAMPLE_WORKSPACE / "pyproject.toml"
    data: Dict[str, Any] = {
        "tool": {
            "poetry": {
                "workspace": {"include": ["members/*"], "exclude": ["members/x"]}
            }
        }
    }
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        path.parent / "members" / "x": False,  # members/x is excluded
    }
    assert parse_workspace(Config(path, data)) == expected

    # no exclude key
    data = {"tool": {"poetry": {"workspace": {"include": ["members/*"]}}}}
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        path.parent / "members" / "x": True,
    }
    assert parse_workspace(Config(path, data)) == expected


def test_format() -> None:
    """End-to-end test of the format."""
    path = EXAMPLE_FORMATS / "pyproject-poetry.toml"
    args = Args(file=path)
    config = Config(path, loads(path.read_text()))
    tasks = parse_tasks(args, config)
    assert tasks


def test_tasks_missing() -> None:
    """File without scripts."""
    args = Args()
    config = Config(Path("pyproject.toml"), {})
    with pytest.raises(KeyError):
        parse_tasks(args, config)


def test_tasks_empty() -> None:
    """Empty scripts."""
    args = Args()
    config = Config(Path("pyproject.toml"), {"tool": {"poetry": {"scripts": {}}}})
    assert parse_tasks(args, config) == {}


def test_task_cmd() -> None:
    """Basic task."""
    args = Args()
    config = Config(
        Path("pyproject.toml"), {"tool": {"poetry": {"scripts": {"a": "pkg:func"}}}}
    )
    expected = {
        "a": replace(TASK, name="a", cmd=PYTHON_CALL.format(pkg="pkg", fn="func"))
    }
    assert parse_tasks(args, config) == expected
