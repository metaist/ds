"""Test main entry point."""

# std
import os
import shlex

# lib
from _pytest.capture import CaptureFixture
import pytest

# pkg
from ds import __version__
from ds import Args
from ds import main
from ds import parse_args


def test_parse_args() -> None:
    """Parse arguments."""
    assert parse_args(shlex.split("--debug")) == Args(debug=True)
    assert parse_args(shlex.split("a b c")) == Args(task=["a", "b", "c"])


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


def test_task() -> None:
    """Run some dummy tasks."""
    main(shlex.split("ds _tests"))
    main(shlex.split("ds --debug _tests"))


def test_no_config() -> None:
    """Fail to find a config file."""
    os.chdir("/")
    with pytest.raises(SystemExit):
        main(shlex.split("ds _tests"))