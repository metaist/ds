"""Test parsing formats."""

# std
from dataclasses import replace
from pathlib import Path
from shlex import split

# lib
import pytest

# pkg
from ds.parsers import parse_tasks
from ds.symbols import TASK_COMPOSITE
from ds.symbols import TASK_DISABLED
from ds.symbols import TASK_KEEP_GOING
from ds.tasks import check_cycles
from ds.tasks import CycleError
from ds.tasks import Task


def test_no_key() -> None:
    """Parse an empty config."""
    assert parse_tasks({}) == (False, {})


def test_skipped() -> None:
    """Parse configs that are skipped."""
    # tasks can be disabled
    assert parse_tasks({"scripts": {f"{TASK_DISABLED}disabled": "ls -la"}})[1] == {}

    # tasks with empty or all-whitespace names are disabled
    assert parse_tasks({"scripts": {"": "ls -la", "  ": "exit 1"}})[1] == {}


def test_nop() -> None:
    """Parse an empty task."""
    assert parse_tasks({"scripts": {"nop": ""}})[1] == {
        "nop": Task(origin_key="scripts", name="nop")
    }


def test_string() -> None:
    """Parse basic string task."""
    assert parse_tasks({"scripts": {"ls": "ls -la"}})[1] == {
        "ls": Task(origin_key="scripts", name="ls", cmd="ls -la")
    }

    # Tasks can suppress errors.
    assert parse_tasks({"scripts": {"ls": f"{TASK_KEEP_GOING}ls -la"}})[1] == {
        "ls": Task(
            origin_key="scripts",
            name="ls",
            cmd="ls -la",
            keep_going=True,
        )
    }


def test_composite() -> None:
    """Parse a `composite` task."""
    cmd = [f"{TASK_KEEP_GOING}clean", "build"]
    expected = {
        "all": Task(
            origin_key="scripts",
            name="all",
            depends=[
                Task(
                    origin_key="scripts",
                    name=TASK_COMPOSITE,
                    cmd="clean",
                    keep_going=True,
                ),
                Task(
                    origin_key="scripts",
                    name=TASK_COMPOSITE,
                    cmd="build",
                ),
            ],
        )
    }
    expected["all"].pprint()  # test printing

    # ds-style
    assert parse_tasks({"scripts": {"all": cmd}})[1] == expected

    # pdm-style
    assert parse_tasks({"scripts": {"all": {"composite": cmd}}})[1] == expected

    # rye-style
    assert parse_tasks({"scripts": {"all": {"chain": cmd}}})[1] == expected


def test_composite_and_shell() -> None:
    """Parse a `composite` with a `shell`."""
    expected = {
        "build": Task(
            origin_key="scripts",
            name="build",
            depends=[Task(origin_key="scripts", name=TASK_COMPOSITE, cmd="cd ..")],
            cmd="ls -la",
            verbatim=True,
        )
    }

    assert (
        parse_tasks(
            {
                "scripts": {
                    "build": {
                        "composite": ["cd .."],
                        "shell": "ls -la",
                        "verbatim": True,
                    }
                }
            }
        )[1]
        == expected
    )


def test_shell_cmd() -> None:
    """Parse a `shell` or `cmd` task."""
    cmd = f"{TASK_KEEP_GOING}ls -la"
    expected = {
        "ls": Task(
            origin_key="scripts",
            name="ls",
            cmd="ls -la",
            keep_going=True,
        )
    }
    expected["ls"].pprint()  # test printing

    # shell
    assert parse_tasks({"scripts": {"ls": {"shell": cmd}}})[1] == expected

    # cmd (str)
    assert parse_tasks({"scripts": {"ls": {"cmd": cmd}}})[1] == expected

    # cmd (list)
    assert parse_tasks({"scripts": {"ls": {"cmd": split(cmd)}}})[1] == expected

    # rye-style
    task2 = replace(expected["ls"], origin_key="tool.rye.scripts")
    assert parse_tasks({"tool": {"rye": {"scripts": {"ls": split(cmd)}}}})[1] == {
        "ls": task2
    }


def test_call() -> None:
    """Fail to parse `call` task."""
    with pytest.raises(ValueError):
        parse_tasks({"scripts": {"ls": {"call": "ds:main"}}})


def test_cwd() -> None:
    """Parse `cwd` and `working_dir` options."""
    cmd = "ls -la"
    expected = {
        "ls": Task(
            origin=Path(), origin_key="scripts", name="ls", cmd=cmd, cwd=Path("test")
        )
    }
    expected["ls"].pprint()  # test printing
    assert (
        parse_tasks({"scripts": {"ls": {"cmd": cmd, "cwd": "test"}}}, Path())[1]
        == expected
    )


def test_bad_types() -> None:
    """Handle bad types."""
    # Unsupported task type.
    with pytest.raises(TypeError):
        parse_tasks({"scripts": {"X": False}})

    # Unsupported mapping type.
    with pytest.raises(TypeError):
        parse_tasks({"scripts": {"X": {"bad": ["A", "B", "C"]}}})


def test_ok_loop() -> None:
    """Parse a ok loop."""
    task = Task(name=TASK_COMPOSITE, cmd="a")
    check_cycles({"a": Task(depends=[task])})


def test_bad_loop() -> None:
    """Try to parse a loop."""
    with pytest.raises(CycleError):
        check_cycles(
            {
                "a": Task(depends=[Task(name=TASK_COMPOSITE, cmd="b")]),
                "b": Task(depends=[Task(name=TASK_COMPOSITE, cmd="a")]),
            }
        )
