"""Test task runner."""

# std
from pathlib import Path
import os
import tempfile

# lib
import pytest

# pkg
from ds.args import Args
from ds.env import TempEnv
from ds.exceptions import ConfigError
from ds.runner import _is_powershell
from ds.runner import find_project
from ds.runner import Runner
from ds.runner import venv_activate_cmd
from ds.tasks import Task
from ds import pushd


def test_is_powershell() -> None:
    """Detect PowerShell environment (issue #109)."""
    # Not PowerShell by default (in test environment)
    with TempEnv(
        SHELL="/bin/bash", POWERSHELL_DISTRIBUTION_CHANNEL=None, PSModulePath=None
    ):
        assert _is_powershell() is False

    # PowerShell Core sets POWERSHELL_DISTRIBUTION_CHANNEL
    with TempEnv(POWERSHELL_DISTRIBUTION_CHANNEL="PSCore"):
        assert _is_powershell() is True

    # SHELL contains pwsh
    with TempEnv(
        SHELL="/usr/bin/pwsh", POWERSHELL_DISTRIBUTION_CHANNEL=None, PSModulePath=None
    ):
        assert _is_powershell() is True

    # SHELL contains powershell (case-insensitive)
    with TempEnv(
        SHELL="C:\\Windows\\PowerShell\\powershell.exe",
        POWERSHELL_DISTRIBUTION_CHANNEL=None,
        PSModulePath=None,
    ):
        assert _is_powershell() is True

    # PSModulePath with 3+ paths (fallback heuristic)
    folders = os.pathsep.join(["path1", "path2", "path3"])
    with TempEnv(
        SHELL="/bin/bash", POWERSHELL_DISTRIBUTION_CHANNEL=None, PSModulePath=folders
    ):
        assert _is_powershell() is True

    # PSModulePath with fewer than 3 paths - not enough
    folders = os.pathsep.join(["path1", "path2"])
    with TempEnv(
        SHELL="/bin/bash", POWERSHELL_DISTRIBUTION_CHANNEL=None, PSModulePath=folders
    ):
        assert _is_powershell() is False


def test_venv_activate() -> None:
    """Return the correct .venv command."""
    venv = Path(".venv")
    with TempEnv(
        SHELL="/bin/bash", POWERSHELL_DISTRIBUTION_CHANNEL=None, PSModulePath=None
    ):
        assert venv_activate_cmd(venv) == "source .venv/bin/activate;"
    with TempEnv(
        SHELL="/bin/zsh", POWERSHELL_DISTRIBUTION_CHANNEL=None, PSModulePath=None
    ):
        assert venv_activate_cmd(venv) == "source .venv/bin/activate;"
    with TempEnv(
        SHELL="/bin/csh", POWERSHELL_DISTRIBUTION_CHANNEL=None, PSModulePath=None
    ):
        assert venv_activate_cmd(venv) == "source .venv/bin/activate.csh;"
    with TempEnv(
        SHELL="/bin/fish", POWERSHELL_DISTRIBUTION_CHANNEL=None, PSModulePath=None
    ):
        assert venv_activate_cmd(venv) == "source .venv/bin/activate.fish;"
    with TempEnv(
        SHELL="/bin/unknown", POWERSHELL_DISTRIBUTION_CHANNEL=None, PSModulePath=None
    ):  # unknown POSIX
        assert venv_activate_cmd(venv) == "source .venv/bin/activate;"

    # simulate PowerShell
    # https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_psmodulepath?view=powershell-7.4
    folders = os.pathsep.join(
        [
            "$HOME/.local/share/powershell/Modules",
            "/usr/local/share/powershell/Modules",
            "/opt/microsoft/powershell/6/Modules",
        ]
    )
    with TempEnv(SHELL="/usr/bin/pwsh", PSModulePath=folders):
        assert venv_activate_cmd(venv) == "source .venv/bin/Activate.ps1;"


def test_run_composite() -> None:
    """Run a composite test."""
    runner = Runner(Args(), {})
    runner.run(Args.parse(["ls"]).task, Task())

    runner.run(Args.parse(["--parallel", "echo hello", "echo world"]).task, Task())
    runner.cleanup()  # simulate exit


def test_run_env_file() -> None:
    """Load an env-file."""
    args = Args.parse(["--env-file", "examples/formats/.env", "echo $IN_DOT_ENV"])
    runner = Runner(args, {})
    runner.run(args.task, Task())

    # non-existent file
    with pytest.raises(ConfigError, match="Env file not found"):
        args = Args.parse(["--env-file", ".env", "echo $IN_DOT_ENV"])
        runner = Runner(args, {})
        runner.run(args.task, Task())


def test_node_modules_already_in_path() -> None:
    """Skip adding node_modules/.bin if already in PATH."""
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        node_bin = root / "node_modules" / ".bin"
        node_bin.mkdir(parents=True, exist_ok=True)

        # Set PATH to already include node_modules/.bin
        with TempEnv(DS_INTERNAL__FILE=None, VIRTUAL_ENV=None, PATH=str(node_bin)):
            with pushd(root):
                args = Args()
                task = Task(cmd="echo hello")
                result = find_project(args, task)
                # node_bin should not be added again since it's already in PATH
                assert "_env" not in result.__dict__ or "PATH" not in result._env


def test_parallel_does_not_propagate() -> None:
    """Parallel flag should not propagate to grandchildren (issue #92)."""
    from ds.symbols import TASK_COMPOSITE

    # Create task hierarchy:
    # A (parallel=True) -> [B, C]
    # B -> [D, E] (should run sequentially, not parallel)
    tasks = {
        "D": Task(name="D", cmd="echo D"),
        "E": Task(name="E", cmd="echo E"),
        "B": Task(
            name="B",
            depends=[
                Task(name=TASK_COMPOSITE, cmd="D"),
                Task(name=TASK_COMPOSITE, cmd="E"),
            ],
        ),
        "C": Task(name="C", cmd="echo C"),
    }

    # Parent task with parallel=True
    parent = Task(
        name="A",
        parallel=True,
        depends=[
            Task(name=TASK_COMPOSITE, cmd="B"),
            Task(name=TASK_COMPOSITE, cmd="C"),
        ],
    )

    args = Args()
    runner = Runner(args, tasks)

    # Track which tasks ran with parallel=True
    parallel_tasks: list[str] = []
    original_run_in_shell = runner.run_in_shell

    def tracking_run_in_shell(task: Task, resolved: Task) -> Task:
        if resolved.parallel:
            parallel_tasks.append(resolved.cmd.strip())
        return original_run_in_shell(task, resolved)

    runner.run_in_shell = tracking_run_in_shell  # type: ignore[method-assign]

    runner.run(parent, Task())
    runner.cleanup()

    # C should run in parallel (direct child of parallel parent)
    # D and E should NOT run in parallel (grandchildren)
    assert "echo C" in parallel_tasks, "C should be parallel (direct child)"
    assert "echo D" not in parallel_tasks, "D should not be parallel (grandchild)"
    assert "echo E" not in parallel_tasks, "E should not be parallel (grandchild)"


def test_parallel_sync_point(caplog: pytest.LogCaptureFixture) -> None:
    """Parallel children complete before parent continues (issue #92)."""
    import logging

    caplog.set_level(logging.DEBUG)

    from ds.symbols import TASK_COMPOSITE

    # Parent with parallel=True and a cmd that runs after children
    parent = Task(
        name="build",
        parallel=True,
        cmd="echo done",
        depends=[
            Task(name=TASK_COMPOSITE, cmd="echo A"),
            Task(name=TASK_COMPOSITE, cmd="echo B"),
        ],
    )

    args = Args()
    runner = Runner(args, {})
    runner.run(parent, Task())
    runner.cleanup()

    # Verify sync point was hit (waiting for parallel tasks)
    assert "waiting for 2 parallel tasks" in caplog.text


def test_parallel_error_handling() -> None:
    """Parallel task failures are reported (issue #92)."""
    from ds.exceptions import TaskError
    from ds.symbols import TASK_COMPOSITE

    # Parent with parallel children, one of which fails
    parent = Task(
        name="build",
        parallel=True,
        depends=[
            Task(name=TASK_COMPOSITE, cmd="echo A"),
            Task(name=TASK_COMPOSITE, cmd="exit 1"),  # This will fail
        ],
    )

    args = Args()
    runner = Runner(args, {})

    with pytest.raises(TaskError, match="parallel task failed"):
        runner.run(parent, Task())

    runner.cleanup()


def test_parallel_error_with_keep_going() -> None:
    """Parallel task failures are ignored with keep_going (issue #92)."""
    from ds.symbols import TASK_COMPOSITE

    # Parent with parallel children, one fails but has keep_going
    parent = Task(
        name="build",
        parallel=True,
        depends=[
            Task(name=TASK_COMPOSITE, cmd="echo A"),
            Task(
                name=TASK_COMPOSITE, cmd="exit 1", keep_going=True
            ),  # Fails but ignored
        ],
    )

    args = Args()
    runner = Runner(args, {})

    # Should not raise because failing task has keep_going=True
    runner.run(parent, Task())
    runner.cleanup()
