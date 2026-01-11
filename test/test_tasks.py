"""Test running tasks."""

# std
from pathlib import Path

# lib
import pytest

# pkg
from ds.args import Args
from ds.runner import Runner
from ds.tasks import get_original_cwd
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


def test_print_tree_with_help() -> None:
    """Print task tree with task help text."""
    tasks: Tasks = {
        "build": parse_task({"cmd": "echo build", "help": "Build the project"}),
    }
    print_tree(Path(), tasks)


def test_print_tree_non_composite_dep() -> None:
    """Print task tree with non-composite dependencies."""
    # Create a task with a named (non-composite) dependency
    dep_task = Task(name="dep", cmd="echo dep")
    main_task = Task(name="main", depends=[dep_task])
    tasks: Tasks = {
        "dep": dep_task,
        "main": main_task,
    }
    print_tree(Path(), tasks)


def test_print_tree_empty_cmd() -> None:
    """Print task tree with empty command in composite."""
    # Composite task with empty cmd
    dep = Task(name="<composite>", cmd="")
    main_task = Task(name="main", depends=[dep])
    tasks: Tasks = {"main": main_task}
    print_tree(Path(), tasks)


def test_get_original_cwd() -> None:
    """get_original_cwd() returns a valid path (issue #106)."""
    cwd = get_original_cwd()
    assert isinstance(cwd, Path)
    assert cwd.exists()
    # Calling again returns the same cached value
    assert get_original_cwd() is cwd


def test_composite_no_shared_mutables() -> None:
    """Composite tasks should not share mutable fields (issue #105)."""
    tasks: Tasks = {
        "a": parse_task("echo a"),
        "b": parse_task("echo b"),
        "all": parse_task(["a", "b"]),
    }
    # Modify one dependency's mutable fields
    dep1 = tasks["all"].depends[0]
    dep2 = tasks["all"].depends[1]

    dep1.args.append("modified")
    dep1.env["KEY"] = "value"

    # The other dependency should not be affected
    assert dep2.args == []
    assert dep2.env == {}


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
