"""Test main entry point."""

# std
from pathlib import Path
from shlex import split

# lib
from _pytest.capture import CaptureFixture
import pytest

# pkg
from ds import __version__
from ds import main
from ds import pushd
from ds.env import TempEnv

PATH_WK = Path("examples") / "workspace"


def test_help() -> None:
    """-h and --help show help"""
    main(split("ds -h"))
    main(split("ds --help"))


def test_version(capsys: CaptureFixture[str]) -> None:
    """--version shows the version"""
    main(split("ds --version"))

    captured = capsys.readouterr()
    assert captured.out.startswith(__version__)


def test_list() -> None:
    """--list shows available tasks"""
    for arg in ["", "-l", "--list"]:
        main(split(f"ds {arg}"))


def test_task() -> None:
    """Run some dummy tasks."""
    main(split("ds --cwd test -f examples/formats/ds.toml tests"))
    main(split("ds -f examples/formats/ds.toml --debug tests"))
    main(split("ds --cwd . -f examples/full.toml composite"))


def test_good_loop() -> None:
    """Run some loop-looking tasks."""
    main(split("ds -f examples/loop-good.toml ls"))  # ok
    main(split("ds -f examples/loop-good.toml df"))  # ok
    main(split("ds -f examples/loop-good.toml ls2"))  # ok


def test_bad_loop() -> None:
    """Try to run bad loops."""
    with pytest.raises(SystemExit) as e:
        main(split("ds -f examples/loop-bad.toml bad"))
    assert e.value.code == 1


def test_no_task() -> None:
    """Try to run a missing task."""
    with pytest.raises(SystemExit) as e:
        main(split("ds _does_not_exist"))
    assert e.value.code == 1


def test_bad_cwd() -> None:
    """Try to point to a non-existent directory."""
    with pytest.raises(SystemExit) as e:
        main(split("ds --cwd /does-not-exist"))
    assert e.value.code == 1


def test_bad_config() -> None:
    """Try to load a non-existent config file."""
    with pytest.raises(SystemExit) as e:
        main(split("ds -f /does-not-exist.toml"))
    assert e.value.code == 1


def test_no_config() -> None:
    """Fail to find a config file."""
    with pushd("/"):
        with pytest.raises(SystemExit):
            main(split("ds tests"))


def test_stay_in_file() -> None:
    """Use the same file when calling `ds` in a task."""
    main(split("ds --debug -f examples/formats/package.json inside"))
    main(split("ds -f examples/formats/package.json outside"))


def test_get_file_from_env() -> None:
    """Get config file from environment variable."""
    path = str(Path("examples") / "formats" / "package.json")
    with TempEnv(_DS_CURRENT_FILE=path):
        main(split("ds"))

    with TempEnv(_DS_CURRENT_FILE=path):
        main(split("ds --debug"))

    with TempEnv(_DS_CURRENT_FILE=None):
        main(split("ds"))


def test_run_workspace() -> None:
    """Run a workspace."""
    with TempEnv(_DS_CURRENT_FILE=None):
        with pushd(PATH_WK):
            main(split("ds --debug -w*"))


def test_run_some_workspaces() -> None:
    """Run in only one workspace."""
    with TempEnv(_DS_CURRENT_FILE=None):
        with pushd(PATH_WK):
            main(split("ds -w '*/a'"))


def test_workspace_same_name() -> None:
    """Run files with same name."""
    with TempEnv(_DS_CURRENT_FILE=None):
        with pushd(PATH_WK):
            main(split("ds --file 'package.json' -w*"))
