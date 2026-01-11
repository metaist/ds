"""Test running tasks."""

# std
from pathlib import Path

# lib
import pytest

# pkg
from ds.args import Args
from ds.runner import Runner
from ds.tasks import print_tasks
from ds.tasks import print_tree
from ds.tasks import Task
from ds.tasks import Tasks
from ds.parsers.ds_toml import parse_task


def _run(task: Task, tasks: Tasks | None = None) -> int:
    return Runner(Args(), tasks or {}).run(task, Task())


def test_print() -> None:
    """Print tasks."""
    # long task
    task = parse_task("echo " * 100)
    task.pprint()

    task.verbatim = True
    task.pprint()

    print_tasks(Path(), {})
    print_tasks(Path(), {"echo": task})


def test_print_tree() -> None:
    """Print task tree."""
    # empty tasks
    print_tree(Path(), {})

    # simple tasks
    tasks: Tasks = {
        "build": parse_task("echo build"),
        "clean": parse_task("rm -rf build"),
    }
    print_tree(Path(), tasks)

    # nested composite tasks: A -> B -> D, E
    tasks = {
        "D": parse_task("echo D"),
        "E": parse_task("echo E"),
        "B": parse_task(["D", "E"]),
        "C": parse_task("echo C"),
        "A": parse_task(["B", "C"]),
    }
    print_tree(Path(), tasks)


def test_as_args() -> None:
    """Render task as args."""
    assert Task().as_args() == "ds"

    task = Task(name="run")
    assert task.as_args() == "ds run"

    task = Task(name="run", keep_going=True)
    assert task.as_args() == "ds +run"

    task = Task(name="run", cwd=Path("test"))
    assert task.as_args() == "ds --cwd test run"

    task = Task(name="run", env=dict(VAR="value"))
    assert task.as_args() == "ds -e VAR=value run"

    task = Task(name="run", env_file=Path(".env"))
    assert task.as_args() == "ds --env-file .env run"


def test_missing() -> None:
    """Try to run a missing task."""
    with pytest.raises(SystemExit) as e_info:
        task = parse_task("task-and-command-not-found")
        _run(task)
    assert e_info.value.code == 127  # command not found


def test_single() -> None:
    """Run a task."""
    tasks: Tasks = {"ls": parse_task("ls -la")}

    _run(tasks["ls"], tasks)
    Runner(Args(), tasks).run(tasks["ls"], Task(args=["-h"]))
    Runner(Args(dry_run=True), tasks).run(tasks["ls"], Task(args=["test"]))


def test_multiple() -> None:
    """Run multiple tasks."""
    tasks: Tasks = {"ls": parse_task("ls -la"), "all": parse_task(["ls"])}
    _run(tasks["all"], tasks)


def test_composite_shell() -> None:
    """Run a shell command in a composite task."""
    tasks: Tasks = {"all": parse_task(["ls -la"])}
    _run(tasks["all"], tasks)


def test_failing() -> None:
    """Run a failing task."""
    tasks: Tasks = {"fail": parse_task("exit 123")}
    with pytest.raises(SystemExit) as e_info:
        _run(tasks["fail"], tasks)
    assert e_info.value.code == 123
