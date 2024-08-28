"""Test `composer.json` parser."""

# std
from dataclasses import replace
from pathlib import Path

# lib
import pytest

# pkg
from . import EXAMPLE_FORMATS
from . import nest
from ds.args import Args
from ds.parsers import Config
from ds.parsers.composer_json import loads
from ds.parsers.composer_json import parse_tasks
from ds.parsers.composer_json import parse_workspace
from ds.parsers.composer_json import PHP_CALL
from ds.symbols import TASK_COMPOSITE
from ds.symbols import TASK_KEEP_GOING
from ds.tasks import Task

PATH = Path("composer.json")
"""Default path."""

KEY = "scripts"
"""Default key."""

TASK = Task(origin=PATH, origin_key=KEY)
"""Default task data."""


def test_workspace() -> None:
    """Workspace not supported."""
    with pytest.raises(NotImplementedError):
        parse_workspace(Config(Path("composer.json"), {}))


def test_format() -> None:
    """End-to-end test of the format."""
    path = EXAMPLE_FORMATS / "composer.json"
    args = Args(file=path)
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
    data = nest(KEY, {"a": "b"})
    data["scripts-descriptions"] = {"a": "run things"}
    expected = {"a": replace(TASK, name="a", cmd="b", help="run things")}
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_aliases() -> None:
    """Task aliases."""
    data = nest(KEY, {"a": "b"})
    data["scripts-aliases"] = {"a": ["c", "d"]}
    expected = {
        "a": replace(TASK, name="a", cmd="b"),
        "c": replace(
            TASK,
            origin_key="scripts-aliases",
            name="c",
            depends=[replace(TASK, name=TASK_COMPOSITE, cmd="a")],
        ),
        "d": replace(
            TASK,
            origin_key="scripts-aliases",
            name="d",
            depends=[replace(TASK, name=TASK_COMPOSITE, cmd="a")],
        ),
    }
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_cmd() -> None:
    """Basic task."""
    data = nest(KEY, {"a": "b"})
    expected = {"a": replace(TASK, name="a", cmd="b")}
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_call() -> None:
    """`call` task."""
    # auto-loadable class
    data = nest(KEY, {"a": "MyPackage\\MyClass"})
    expected = {
        "a": replace(TASK, name="a", cmd=PHP_CALL.format(fn="MyPackage\\MyClass"))
    }
    assert parse_tasks(Config(PATH, data)) == expected

    # static method
    data = nest(KEY, {"a": "MyPackage\\MyClass::func"})
    expected = {
        "a": replace(TASK, name="a", cmd=PHP_CALL.format(fn="MyPackage\\MyClass::func"))
    }
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_composite() -> None:
    """Composite tasks."""
    data = nest(KEY, {"a": ["b", "c"]})
    expected = {
        "a": replace(
            TASK,
            name="a",
            depends=[
                replace(TASK, name=TASK_COMPOSITE, cmd="b"),
                replace(TASK, name=TASK_COMPOSITE, cmd="c"),
            ],
        )
    }
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_args() -> None:
    """Task args."""
    # argument interpolation: via reference
    data = nest(KEY, {"a": "ls", "b": "@a -lah"})
    expected = {
        "a": replace(TASK, name="a", cmd="ls"),
        "b": replace(
            TASK, name="b", depends=[replace(TASK, name=TASK_COMPOSITE, cmd="a -lah")]
        ),
    }
    assert parse_tasks(Config(PATH, data)) == expected

    # argument interpolation: via CLI
    data = nest(KEY, {"a": "ls $1"})
    expected = {"a": replace(TASK, name="a", cmd="ls $1")}
    assert parse_tasks(Config(PATH, data)) == expected


def test_keep_going() -> None:
    """Not supported: error suppression"""
    data = nest(KEY, {"a": f"{TASK_KEEP_GOING}b"})
    expected = {"a": replace(TASK, name="a", cmd=f"{TASK_KEEP_GOING}b")}
    # NOTE: `keep_going` NOT set
    assert parse_tasks(Config(PATH, data)) == expected


def test_task_env() -> None:
    """`@putenv`"""
    data = nest(KEY, {"a": ["@putenv PORT=8080", "flask $PORT"]})
    expected = {
        "a": replace(
            TASK,
            name="a",
            env={"PORT": "8080"},
            depends=[replace(TASK, name=TASK_COMPOSITE, cmd="flask $PORT")],
        ),
    }
    assert parse_tasks(Config(PATH, data)) == expected


def test_bad_syntax() -> None:
    """Syntax errors."""
    data = nest(KEY, {"a": False})
    with pytest.raises(TypeError):
        parse_tasks(Config(PATH, data))
