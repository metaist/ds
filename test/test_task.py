"""Test running tasks."""

# lib
import pytest

# pkg
from ds import run_task
from ds import Task
from ds import Tasks


def test_missing() -> None:
    """Try to run a missing task."""
    with pytest.raises(ValueError):
        run_task({}, "ls")


def test_single() -> None:
    """Run a task."""
    tasks: Tasks = {"ls": Task.parse("ls -la")}
    run_task(tasks, "ls")
    run_task(tasks, "ls", ["-h"])
    run_task(tasks, "ls", ["test"])


def test_multiple() -> None:
    """Run multiple tasks."""
    tasks: Tasks = {"ls": Task.parse("ls -la"), "all": Task.parse(["ls"])}
    run_task(tasks, "all")


def test_failing() -> None:
    tasks: Tasks = {"fail": Task.parse("exit 123")}
    with pytest.raises(SystemExit) as e_info:
        run_task(tasks, "fail")
    assert e_info.value.code == 123
