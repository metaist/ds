"""Test running tasks."""

# std
from pathlib import Path

# lib
import pytest

# pkg
from ds.args import Args
from ds.exceptions import TaskError
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


def test_print_tree_parallel() -> None:
    """Print task tree with parallel tasks (line 280)."""
    tasks: Tasks = {
        "a": parse_task("echo a"),
        "b": parse_task("echo b"),
        "parallel": parse_task({"composite": ["a", "b"], "parallel": True}),
    }
    print_tree(Path(), tasks)


def test_print_tree_dedup_with_deps() -> None:
    """Print task tree with deduplication for tasks with dependencies (lines 300-301)."""
    # B has dependencies, so when it appears twice it should show (*)
    tasks: Tasks = {
        "D": parse_task("echo D"),
        "E": parse_task("echo E"),
        "B": parse_task(["D", "E"]),  # B has deps
        "C": parse_task(["B"]),  # C depends on B
        "A": parse_task(["B", "C"]),  # A depends on B and C; B appears twice
    }
    # When printing A's tree, B should show (*) the second time under C
    cli_task = Task(depends=[tasks["A"]])
    print_tree(Path(), tasks, cli_task)


def test_print_tasks_with_cli_tasks() -> None:
    """Print tasks for CLI-specified tasks (lines 217, 221)."""
    tasks: Tasks = {
        "build": parse_task("echo build"),
        "test": parse_task("echo test"),
    }
    # Create a CLI task with composite dependencies
    cli_task = parse_task(["build", "test"])
    print_tasks(Path(), tasks, cli_task)


def test_print_tasks_with_raw_command() -> None:
    """Print tasks with raw command not in tasks dict (line 221)."""
    tasks: Tasks = {
        "build": parse_task("echo build"),
    }
    # CLI task includes a raw command that's not a known task
    cli_task = parse_task(["build", "echo hello"])
    print_tasks(Path(), tasks, cli_task)


def test_print_tasks_non_composite_dep() -> None:
    """Print tasks with non-composite dependency (line 217)."""
    # Create a task with a named (non-composite) dependency
    dep_task = Task(name="dep", cmd="echo dep")
    cli_task = Task(depends=[dep_task])
    tasks: Tasks = {"dep": dep_task}
    print_tasks(Path(), tasks, cli_task)


def test_print_tasks_json() -> None:
    """Print tasks in JSON format."""
    tasks: Tasks = {
        "build": parse_task({"cmd": "echo build", "help": "Build the project"}),
        "test": parse_task("echo test"),
    }
    # All tasks
    print_tasks(Path(), tasks, output_format="json")

    # Specific tasks
    cli_task = parse_task(["build"])
    print_tasks(Path(), tasks, cli_task, output_format="json")


def test_print_tasks_json_with_deps() -> None:
    """Print tasks with dependencies in JSON format."""
    tasks: Tasks = {
        "a": parse_task("echo a"),
        "b": parse_task("echo b"),
        "all": parse_task(["a", "b"]),
    }
    print_tasks(Path(), tasks, output_format="json")


def test_print_tasks_json_non_composite_dep() -> None:
    """Print tasks with non-composite dependencies in JSON format (line 205, 241)."""
    # Create a task with a named (non-composite) dependency
    dep_task = Task(name="dep", cmd="echo dep")
    main_task = Task(name="main", depends=[dep_task])
    tasks: Tasks = {"dep": dep_task, "main": main_task}
    # Test all tasks JSON output
    print_tasks(Path(), tasks, output_format="json")
    # Test CLI-specified tasks with non-composite dep
    cli_task = Task(depends=[dep_task])
    print_tasks(Path(), tasks, cli_task, output_format="json")


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
    with pytest.raises(TaskError) as e_info:
        task = parse_task("task-and-command-not-found")
        _run(task)
    assert e_info.value.exit_code == 127  # command not found


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
    with pytest.raises(TaskError) as e_info:
        _run(tasks["fail"], tasks)
    assert e_info.value.exit_code == 123
