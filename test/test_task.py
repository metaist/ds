"""Test running tasks."""

# lib
import pytest

# pkg
from ds.tasks import Task
from ds.tasks import Tasks


def test_missing() -> None:
    """Try to run a missing task."""
    with pytest.raises(ValueError):
        task = Task.parse("ls")
        task.allow_shell = False
        task.run({})


def test_single() -> None:
    """Run a task."""
    tasks: Tasks = {"ls": Task.parse("ls -la")}
    tasks["ls"].run(tasks)
    tasks["ls"].run(tasks, ["-h"])
    tasks["ls"].run(tasks, ["test"])


def test_multiple() -> None:
    """Run multiple tasks."""
    tasks: Tasks = {"ls": Task.parse("ls -la"), "all": Task.parse(["ls"])}
    tasks["all"].run(tasks)


def test_failing() -> None:
    """Run a failing task."""
    tasks: Tasks = {"fail": Task.parse("exit 123")}
    with pytest.raises(SystemExit) as e_info:
        tasks["fail"].run(tasks)
    assert e_info.value.code == 123
