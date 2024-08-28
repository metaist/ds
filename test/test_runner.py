"""Test task runner."""

# std
from pathlib import Path
import os

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
