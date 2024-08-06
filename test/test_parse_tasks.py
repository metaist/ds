"""Test generic config parsing."""

# std

# lib
import pytest

# pkg
from ds.configs import parse_tasks
from ds.tasks import check_cycles
from ds.tasks import CycleError
from ds.tasks import Task


def test_skipped() -> None:
    """Parse configs that are skipped."""
    # tasks that start with a hash (#) are disabled
    assert parse_tasks({"scripts": {"#disabled": "ls -la"}})[1] == {}

    # tasks with empty or all-whitespace names are disabled
    assert parse_tasks({"scripts": {"": "ls -la", "  ": "exit 1"}})[1] == {}


def test_nop() -> None:
    """Parse an empty task."""
    assert parse_tasks({"scripts": {"nop": ""}})[1] == {"nop": Task(name="nop")}


def test_string() -> None:
    """Parse basic string command."""
    assert parse_tasks({"scripts": {"ls": "ls -la"}})[1] == {
        "ls": Task(name="ls", cmd="ls -la")
    }

    # Task commands that start with a hyphen suppress errors.
    assert parse_tasks({"scripts": {"ls": "+ls -la"}})[1] == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }


def test_composite() -> None:
    """Parse a `composite` command."""
    # ds-style
    assert parse_tasks({"scripts": {"all": ["+clean", "build"]}})[1] == {
        "all": Task(
            name="all",
            depends=[
                Task(name="#composite", cmd="clean", keep_going=True),
                Task(name="#composite", cmd="build"),
            ],
        )
    }

    # pdm-style
    assert parse_tasks({"scripts": {"all": {"composite": ["clean", "build"]}}})[1] == {
        "all": Task(
            name="all",
            depends=[
                Task(name="#composite", cmd="clean"),
                Task(name="#composite", cmd="build"),
            ],
        )
    }


def test_shell_cmd() -> None:
    """Parse a `shell` or `cmd` command."""
    # shell
    assert parse_tasks({"scripts": {"ls": {"shell": "+ls -la"}}})[1] == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }

    # cmd (str)
    assert parse_tasks({"scripts": {"ls": {"cmd": "+ls -la"}}})[1] == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }

    # cmd (list)
    assert parse_tasks({"scripts": {"ls": {"cmd": ["+ls", "-la"]}}})[1] == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }


def test_call() -> None:
    """Try to parse a `call` command."""
    with pytest.raises(ValueError):
        parse_tasks({"scripts": {"ls": {"call": "ds:main"}}})


def test_bad_types() -> None:
    """Handle bad types."""
    # Basic unsupported command type.
    with pytest.raises(TypeError):
        parse_tasks({"scripts": {"X": False}})

    # Unsupported mapping type.
    with pytest.raises(TypeError):
        parse_tasks({"scripts": {"X": {"bad": ["A", "B", "C"]}}})


def test_bad_loop() -> None:
    """Try to parse a loop."""
    with pytest.raises(CycleError):
        check_cycles(
            {
                "a": Task(depends=[Task(name="#composite", cmd="b")]),
                "b": Task(depends=[Task(name="#composite", cmd="a")]),
            }
        )
