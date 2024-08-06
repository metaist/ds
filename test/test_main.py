"""Test main entry point."""

# std
import shlex

# lib
from _pytest.capture import CaptureFixture
import pytest

# pkg
from ds import __version__
from ds import main
from ds import pushd


def test_help() -> None:
    """-h and --help show help"""
    with pytest.raises(SystemExit) as e:
        main(shlex.split("ds -h"))
    assert e.value.code == 0

    with pytest.raises(SystemExit) as e:
        main(shlex.split("ds --help"))
    assert e.value.code == 0


def test_version(capsys: CaptureFixture[str]) -> None:
    """--version shows the version"""
    with pytest.raises(SystemExit) as e:
        main(shlex.split("ds --version"))

    captured = capsys.readouterr()
    assert e.value.code == 0
    assert captured.out.startswith(__version__)


def test_list() -> None:
    """--list shows available tasks"""
    for arg in ["", "-l", "--list"]:
        with pytest.raises(SystemExit) as e:
            main(shlex.split(f"ds {arg}"))
        assert e.value.code == 0


def test_task() -> None:
    """Run some dummy tasks."""
    main(shlex.split("ds --cwd test -f examples/formats/ds.toml tests"))
    main(shlex.split("ds -f examples/formats/ds.toml --debug tests"))
    main(shlex.split("ds --cwd . -f examples/full.toml composite"))


def test_good_loop() -> None:
    """Run some loop-looking tasks."""
    main(shlex.split("ds -f examples/loop-good.toml ls"))  # ok
    main(shlex.split("ds -f examples/loop-good.toml df"))  # ok
    main(shlex.split("ds -f examples/loop-good.toml ls2"))  # ok


def test_bad_loop() -> None:
    """Try to run bad loops."""
    with pytest.raises(SystemExit) as e:
        main(shlex.split("ds -f examples/loop-bad.toml bad"))
    assert e.value.code == 1


def test_no_task() -> None:
    """Try to run a missing task."""
    with pytest.raises(SystemExit) as e:
        main(shlex.split("ds _does_not_exist"))
    assert e.value.code == 1


def test_bad_cwd() -> None:
    """Try to point to a non-existent directory."""
    with pytest.raises(SystemExit) as e:
        main(shlex.split("ds --cwd /does-not-exist"))
    assert e.value.code == 1


def test_bad_config() -> None:
    """Try to load a non-existent config file."""
    with pytest.raises(SystemExit) as e:
        main(shlex.split("ds -f /does-not-exist.toml"))
    assert e.value.code == 1


def test_no_config() -> None:
    """Fail to find a config file."""
    with pushd("/"):
        with pytest.raises(SystemExit):
            main(shlex.split("ds tests"))


def test_stay_in_file() -> None:
    """Use the same file when calling `ds` in a task."""
    main(shlex.split("ds -f examples/formats/package.json inside"))
    main(shlex.split("ds -f examples/formats/package.json outside"))
