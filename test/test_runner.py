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
from ds.runner import find_project
from ds.runner import Runner
from ds.runner import venv_activate_cmd
from ds.tasks import Task
from ds import pushd


def test_venv_activate() -> None:
    """Return the correct .venv command."""
    venv = Path(".venv")
    with TempEnv(SHELL="/bin/bash"):
        assert venv_activate_cmd(venv) == "source .venv/bin/activate;"
    with TempEnv(SHELL="/bin/zsh"):
        assert venv_activate_cmd(venv) == "source .venv/bin/activate;"
    with TempEnv(SHELL="/bin/csh"):
        assert venv_activate_cmd(venv) == "source .venv/bin/activate.csh;"
    with TempEnv(SHELL="/bin/fish"):
        assert venv_activate_cmd(venv) == "source .venv/bin/activate.fish;"
    with TempEnv(SHELL="/bin/unknown"):  # unknown POSIX
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
    with pytest.raises(SystemExit):
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
