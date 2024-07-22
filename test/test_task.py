"""Test running tasks."""

# lib
import pytest

# pkg
from ds import run_task
from ds import Tasks


def test_missing() -> None:
    """Try to run a missing task."""
    with pytest.raises(ValueError):
        run_task({}, "ls")


def test_single() -> None:
    """Run a task."""
    tasks: Tasks = {"ls": "ls -la"}
    run_task(tasks, "ls")


def test_multiple() -> None:
    """Run multiple tasks."""
    tasks: Tasks = {"ls": "ls -la", "all": ["ls"]}
    run_task(tasks, "all")


def test_failing() -> None:
    tasks: Tasks = {"fail": "exit 123"}
    with pytest.raises(SystemExit) as e_info:
        run_task(tasks, "fail")
    assert e_info.value.code == 123
