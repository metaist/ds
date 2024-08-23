"""Test task runner."""

# std
from pathlib import Path

# pkg
from ds.args import Args
from ds.env import TempEnv
from ds.runner import Runner
from ds.runner import venv_activate_cmd
from ds.tasks import Task


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

    # handle unknown linux / macOS shell
    with TempEnv(SHELL="/bin/unknown"):
        assert venv_activate_cmd(venv) == "source .venv/bin/activate;"


def test_run_composite() -> None:
    """Run a composite test."""
    runner = Runner(Args(), {})
    runner.run(Args.parse(["ls"]).task, Task())
