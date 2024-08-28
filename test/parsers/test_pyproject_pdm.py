"""Test `pyproject.toml` parser using `pdm`."""

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
from . import nest
from ds.args import Args
from ds.parsers import Config
from ds.parsers.pyproject_pdm import loads
from ds.parsers.pyproject_pdm import parse_tasks
from ds.parsers.pyproject_pdm import parse_workspace
from ds.parsers.pyproject_rye import PYTHON_CALL
from ds.symbols import TASK_COMPOSITE
from ds.tasks import Task

PATH = Path("project.toml")
"""Default path."""

KEY = "tool.pdm.scripts"
"""Default key."""

TASK = Task(origin=PATH, origin_key=KEY)
"""Default task data."""


def test_workspace_missing() -> None:
    """Missing workspace."""
    with pytest.raises(KeyError):
        parse_workspace(Config(Path(), {}))


def test_workspace_empty() -> None:
    """Empty workspace."""
    data = nest("tool.pdm.workspace", {})
    assert parse_workspace(Config(PATH, data)) == {}


def test_workspace_basic() -> None:
    """Workspace members."""
    path = EXAMPLE_WORKSPACE / "pyproject.toml"
    data = nest("tool.pdm.workspace.packages", ["members/*", "!members/x"])
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        path.parent / "members" / "x": False,  # member/x is excluded
    }
    assert parse_workspace(Config(path, data)) == expected


def test_format() -> None:
    """End-to-end test of the format."""
    path = EXAMPLE_FORMATS / "pyproject-pdm.toml"
    config = Config(path, loads(path.read_text()))
    tasks = parse_tasks(Args(file=path), config)
    assert tasks


def test_tasks_missing() -> None:
    """Missing tasks."""
    with pytest.raises(KeyError):
        parse_tasks(Args(), Config(PATH, {}))


def test_tasks_empty() -> None:
    """Empty tasks."""
    data = nest(KEY, {})
    assert parse_tasks(Args(), Config(PATH, data)) == {}


def test_task_disabled() -> None:
    """Disabled task."""
    data = nest(KEY, {"#a": "b"})
    assert parse_tasks(Args(), Config(PATH, data)) == {}


def test_task_help() -> None:
    """Task help."""
    data = nest(KEY, {"a": {"cmd": "b", "help": "run things"}})
    expected = {"a": replace(TASK, name="a", cmd="b", help="run things")}
    assert parse_tasks(Args(), Config(PATH, data)) == expected


def test_task_cmd() -> None:
    """`cmd` task."""
    data = nest(KEY, {"a": "b"})
    expected = {"a": replace(TASK, name="a", cmd="b")}
    assert parse_tasks(Args(), Config(PATH, data)) == expected

    data = nest(KEY, {"a": {"cmd": ["ls", "-lah"]}})
    expected = {"a": replace(TASK, name="a", cmd="ls -lah")}
    assert parse_tasks(Args(), Config(PATH, data)) == expected

    data = nest(KEY, {"a": {"shell": "ls -lah"}})
    expected = {"a": replace(TASK, name="a", cmd="ls -lah")}
    assert parse_tasks(Args(), Config(PATH, data)) == expected


def test_task_call() -> None:
    """`call` task."""
    data = nest(KEY, {"a": {"call": "ds:main"}})
    expected = {
        "a": replace(TASK, name="a", cmd=PYTHON_CALL.format(pkg="ds", fn="main()"))
    }
    assert parse_tasks(Args(), Config(PATH, data)) == expected


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
    assert parse_tasks(Args(), Config(PATH, data)) == expected


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
    assert parse_tasks(Args(), Config(PATH, data)) == expected


def test_task_env() -> None:
    """`env` option."""
    data = nest(KEY, {"a": {"cmd": "flask $PORT", "env": {"PORT": 8080}}})
    expected = {
        "a": replace(TASK, name="a", cmd="flask $PORT", env={"PORT": "8080"}),
    }
    assert parse_tasks(Args(), Config(PATH, data)) == expected


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
    assert parse_tasks(Args(), Config(path, data)) == expected


def test_working_dir() -> None:
    """`working_dir` option."""
    data = nest(KEY, {"a": {"cmd": "ls -la", "working_dir": "test"}})
    expected = {
        "a": replace(TASK, name="a", cmd="ls -la", cwd=Path("test").resolve()),
    }
    assert parse_tasks(Args(), Config(PATH, data)) == expected


def test_shared_options() -> None:
    """Shared options."""
    data = nest(
        KEY,
        {
            "_": {"env": {"PORT": "8080"}},  # shared
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
    assert parse_tasks(Args(), Config(PATH, data)) == expected


def test_bad_syntax() -> None:
    """Syntax errors."""
    data = nest(KEY, {"a": False})
    with pytest.raises(SyntaxError):
        parse_tasks(Args(), Config(PATH, data))

    data = nest(KEY, {"a": {"unknown": "missing required keys"}})
    with pytest.raises(SyntaxError):
        parse_tasks(Args(), Config(PATH, data))
