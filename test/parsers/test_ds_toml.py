"""Test `ds.toml` parser."""

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
from ds.parsers.ds_toml import loads
from ds.parsers.ds_toml import parse_tasks
from ds.parsers.ds_toml import parse_workspace
from ds.parsers.pyproject_rye import PYTHON_CALL
from ds.symbols import TASK_COMPOSITE
from ds.tasks import Task

PATH = Path("pyproject.toml")
"""Default path."""

KEY = "tool.ds.scripts"
"""Default key."""

TASK = Task(origin=PATH, origin_key=KEY)
"""Default task data."""

TASK2 = Task(origin=Path("ds.toml"), origin_key="scripts")
"""Default task data (ds.toml)."""


def test_workspace() -> None:
    """End-to-end test of workspace config."""
    path = EXAMPLE_WORKSPACE / "pyproject-ds.toml"
    config = Config(path, loads(path.read_text()))
    expected = {
        EXAMPLE_WORKSPACE / "members" / "a": True,
        EXAMPLE_WORKSPACE / "members" / "b": True,
        EXAMPLE_WORKSPACE / "members" / "x": False,  # members/x is excluded
    }
    assert parse_workspace(config) == expected

    path = EXAMPLE_WORKSPACE / "ds.toml"
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
    data = nest("tool.ds.workspace", {})
    assert parse_workspace(Config(PATH, data)) == {}

    data = nest("workspace", {})
    assert parse_workspace(Config(Path("ds.toml"), data)) == {}


def test_workspace_basic1() -> None:
    """Workspace members using `pyproject.toml` style."""
    path = EXAMPLE_WORKSPACE / "pyproject.toml"
    data = nest("tool.ds.workspace.members", ["members/*", "!members/x"])
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        path.parent / "members" / "x": False,  # members/x is excluded
    }
    assert parse_workspace(Config(path, data)) == expected


def test_workspace_basic2() -> None:
    """Workspace members using `ds.toml` style."""
    path = EXAMPLE_WORKSPACE / "ds.toml"
    data = nest("workspace", {"members": ["members/*"], "exclude": ["members/x"]})
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        path.parent / "members" / "x": False,  # members/x is excluded
    }
    assert parse_workspace(Config(path, data)) == expected


def test_format() -> None:
    """End-to-end test of the format."""
    path = EXAMPLE_FORMATS / "pyproject-ds.toml"
    config = Config(path, loads(path.read_text()))
    tasks = parse_tasks(config)
    assert tasks

    path = EXAMPLE_FORMATS / "ds.toml"
    config = Config(path, loads(path.read_text()))
    tasks = parse_tasks(config)
    assert tasks


def test_tasks_missing() -> None:
    """Missing tasks."""
    with pytest.raises(KeyError):
        parse_tasks(Config(PATH, {}))


def test_tasks_empty() -> None:
    """Empty tasks."""
    data = nest("tool.ds.scripts", {})
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

    data = nest(KEY, {"a": {"cmd": ["ls", "-lah"]}})
    expected = {"a": replace(TASK, name="a", cmd="ls -lah")}
    assert parse_tasks(Config(PATH, data)) == expected

    data = nest(KEY, {"a": {"shell": "ls -lah", "verbatim": True}})
    expected = {"a": replace(TASK, name="a", cmd="ls -lah", verbatim=True)}
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_call() -> None:
    """`call` task."""
    data = nest(KEY, {"a": {"call": "ds:main"}})
    expected = {
        "a": replace(TASK, name="a", cmd=PYTHON_CALL.format(pkg="ds", fn="main()"))
    }
    assert parse_tasks(Config(PATH, data)) == expected

    # call outside of pyproject.toml not allowed
    data = {"scripts": {"a": {"call": "ds:main"}}}
    with pytest.raises(SyntaxError):
        parse_tasks(Config(Path("ds.toml"), data))


def test_task_composite() -> None:
    """`composite` task."""
    data = nest(KEY, {"a": "b", "c": "d", "e": {"composite": ["a", "c"]}})
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

    # short-form
    data = {"scripts": {"a": "b", "c": "d", "e": ["a", "c"]}}
    expected = {
        "a": replace(TASK2, name="a", cmd="b"),
        "c": replace(TASK2, name="c", cmd="d"),
        "e": replace(
            TASK2,
            name="e",
            depends=[
                replace(TASK2, name=TASK_COMPOSITE, cmd="a"),
                replace(TASK2, name=TASK_COMPOSITE, cmd="c"),
            ],
        ),
    }
    assert parse_tasks(Config(Path("ds.toml"), data)) == expected


def test_task_keep_going() -> None:
    """`keep_going` option."""
    data = nest(
        KEY,
        {
            "a": "b",
            "c": "d",
            "e": {"composite": ["a", "c"], "keep_going": True},
        },
    )
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
            keep_going=True,
        ),
    }
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_env() -> None:
    """`env` option."""
    data = nest(KEY, {"a": {"cmd": "flask $PORT", "env": {"PORT": 8080}}})
    expected = {
        "a": replace(TASK, name="a", cmd="flask $PORT", env={"PORT": "8080"}),
    }
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_env_file() -> None:
    """`env_file` option."""
    path = EXAMPLE_FORMATS / "pyproject.toml"
    data = nest(KEY, {"a": {"cmd": "flask $PORT", "env_file": ".env"}})
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


def test_working_dir() -> None:
    """`working_dir` option."""
    data = nest(KEY, {"a": {"cmd": "ls -la", "working_dir": "test"}})
    expected = {
        "a": replace(TASK, name="a", cmd="ls -la", cwd=Path("test").resolve()),
    }
    assert parse_tasks(Config(PATH, data)) == expected

    # don't allow multiple aliases for same value
    data = {"scripts": {"a": {"cmd": "ls -la", "cwd": "test1", "working_dir": "test2"}}}
    with pytest.raises(SyntaxError):
        parse_tasks(Config(Path("ds.toml"), data))


def test_shared_options() -> None:
    """Shared options."""
    data = nest(
        KEY,
        {
            "_": {"env": {"PORT": 8080}},  # shared
            "a": "flask",
            "b": {"cmd": "python -m http.server", "env": {"OTHER": "val"}},
        },
    )
    expected = {
        "a": replace(TASK, name="a", cmd="flask", env={"PORT": "8080"}),
        "b": replace(
            TASK,
            name="b",
            cmd="python -m http.server",
            env={"PORT": "8080", "OTHER": "val"},
        ),
    }
    assert parse_tasks(Config(PATH, data)) == expected


def test_bad_syntax() -> None:
    """Syntax errors."""
    data = nest(KEY, {"a": False})
    with pytest.raises(TypeError):
        parse_tasks(Config(PATH, data))
