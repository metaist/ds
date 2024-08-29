"""Test `pyproject.toml` parser using `rye`."""

# std
from dataclasses import replace
from pathlib import Path

# lib
import pytest

# pkg
from . import EXAMPLE_FORMATS
from . import EXAMPLE_WORKSPACE
from . import nest
from ds.configs import Config
from ds.parsers.pyproject_rye import loads
from ds.parsers.pyproject_rye import parse_tasks
from ds.parsers.pyproject_rye import parse_workspace
from ds.symbols import TASK_COMPOSITE
from ds.tasks import Task

PATH = Path("pyproject.toml")
"""Default path."""

KEY = "tool.rye.scripts"
"""Default key."""

TASK = Task(origin=PATH, origin_key=KEY)
"""Default task data."""


def test_workspace() -> None:
    """End-to-end test of workspace config."""
    path = EXAMPLE_WORKSPACE / "pyproject-rye.toml"
    config = Config(path, loads(path.read_text()))
    expected = {
        EXAMPLE_WORKSPACE: True,  # rye includes the root folder
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
    path = EXAMPLE_WORKSPACE / "pyproject-rye.toml"
    data = nest("tool.rye.workspace", {})
    expected = {
        EXAMPLE_WORKSPACE: True,  # rye includes the root folder
        EXAMPLE_WORKSPACE / "members" / "x": True,
        # members/x is the only folder with a pyproject.toml
    }
    assert parse_workspace(Config(path, data)) == expected

    # tool.rye.virtual can prevent the root from being included
    path = EXAMPLE_WORKSPACE / "pyproject-rye.toml"
    data = nest("tool.rye", {"virtual": True, "workspace": {}})
    expected = {
        EXAMPLE_WORKSPACE / "members" / "x": True,
        # members/x is the only folder with a pyproject.toml
    }
    assert parse_workspace(Config(path, data)) == expected


def test_workspace_basic() -> None:
    """Workspace members."""
    path = EXAMPLE_WORKSPACE / "pyproject.toml"
    data = nest("tool.rye.workspace.members", ["members/*", "!members/x"])
    expected = {
        path.parent: True,
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        path.parent / "members" / "x": False,  # member/x is excluded
    }
    assert parse_workspace(Config(path, data)) == expected


def test_format() -> None:
    """End-to-end test of the format."""
    path = EXAMPLE_FORMATS / "pyproject-rye.toml"
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
    data = nest(KEY, {"a": {"cmd": "b", "help": "run things"}})
    expected = {"a": replace(TASK, name="a", cmd="b", help="run things")}
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_cmd() -> None:
    """`cmd` task."""
    data = nest(KEY, {"a": "b"})
    expected = {"a": replace(TASK, name="a", cmd="b")}
    assert parse_tasks(Config(PATH, data)) == expected

    data = nest(KEY, {"a": ["ls", "-lah"]})
    expected = {"a": replace(TASK, name="a", cmd="ls -lah")}
    assert parse_tasks(Config(PATH, data)) == expected

    data = nest(KEY, {"a": {"cmd": ["ls", "-lah"]}})
    expected = {"a": replace(TASK, name="a", cmd="ls -lah")}
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_call() -> None:
    """`call` task."""
    data = nest(KEY, {"a": {"call": "http.server"}})
    expected = {"a": replace(TASK, name="a", cmd="python -m http.server")}
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_chain() -> None:
    """`chain` task."""
    data = nest(KEY, {"a": "b", "c": "d", "e": {"chain": ["a", "c"]}})
    expected = {
        "a": replace(TASK, name="a", cmd="b"),
        "c": replace(TASK, name="c", cmd="d"),
        "e": replace(
            TASK,
            name="e",
            depends=[
                replace(TASK, name=TASK_COMPOSITE, cmd="a"),
                replace(TASK, name=TASK_COMPOSITE, cmd="c"),
            ],
        ),
    }
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_env() -> None:
    """`env` option."""
    data = nest(
        "tool.rye.scripts", {"a": {"cmd": "flask $PORT", "env": {"PORT": 8080}}}
    )
    expected = {
        "a": replace(TASK, name="a", cmd="flask $PORT", env={"PORT": "8080"}),
    }
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_env_file() -> None:
    """`env_file` option."""
    path = EXAMPLE_FORMATS / "pyproject.toml"
    data = nest(KEY, {"a": {"cmd": "flask $PORT", "env-file": ".env"}})
    expected = {
        "a": replace(
            TASK,
            origin=path,
            name="a",
            cmd="flask $PORT",
            env_file=EXAMPLE_FORMATS / ".env",
        ),
    }
    assert parse_tasks(Config(path, data)) == expected

    # with missing file
    data = nest(KEY, {"a": {"cmd": "flask $PORT", "env-file": ".env"}})
    expected = {
        "a": replace(
            TASK,
            name="a",
            cmd="flask $PORT",
            env_file=Path(".env").resolve(),
        ),
    }
    assert parse_tasks(Config(PATH, data)) == expected


def test_bad_syntax() -> None:
    """Syntax errors."""
    data = nest(KEY, {"a": False})
    with pytest.raises(TypeError):
        parse_tasks(Config(PATH, data))

    data = nest(KEY, {"a": {"unknown": "missing required keys"}})
    with pytest.raises(SyntaxError):
        parse_tasks(Config(PATH, data))
