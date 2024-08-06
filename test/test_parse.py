"""Test generic config parsing."""

# std
from pathlib import Path
import sys

# lib
import pytest

# pkg
from ds.configs import Config
from ds.configs import parse_tasks
from ds.tasks import check_cycles
from ds.tasks import Task


# TODO 2024-10-31 [3.8 EOL]: remove conditional
if sys.version_info >= (3, 9):  # pragma: no cover
    from graphlib import CycleError
else:  # pragma: no cover
    from graphlib import CycleError  # type: ignore


def test_skipped() -> None:
    """Parse configs that are skipped."""
    # tasks that start with a hash (#) are disabled
    assert parse_tasks({"scripts": {"#disabled": "ls -la"}})[1] == {}

    # tasks with empty or all-whitespace names are disabled
    assert parse_tasks({"scripts": {"": "ls -la", "  ": "exit 1"}})[1] == {}


def test_nop() -> None:
    """Parse an empty task."""
    assert parse_tasks({"scripts": {"nop": ""}})[1] == {"nop": Task(name="nop")}


def test_string() -> None:
    """Parse basic string command."""
    assert parse_tasks({"scripts": {"ls": "ls -la"}})[1] == {
        "ls": Task(name="ls", cmd="ls -la")
    }

    # Task commands that start with a hyphen suppress errors.
    assert parse_tasks({"scripts": {"ls": "+ls -la"}})[1] == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }


def test_composite() -> None:
    """Parse a `composite` command."""
    # ds-style
    assert parse_tasks({"scripts": {"all": ["+clean", "build"]}})[1] == {
        "all": Task(
            name="all",
            depends=[
                Task(name="#composite", cmd="clean", keep_going=True),
                Task(name="#composite", cmd="build"),
            ],
        )
    }

    # pdm-style
    assert parse_tasks({"scripts": {"all": {"composite": ["clean", "build"]}}})[1] == {
        "all": Task(
            name="all",
            depends=[
                Task(name="#composite", cmd="clean"),
                Task(name="#composite", cmd="build"),
            ],
        )
    }


def test_shell_cmd() -> None:
    """Parse a `shell` or `cmd` command."""
    # shell
    assert parse_tasks({"scripts": {"ls": {"shell": "+ls -la"}}})[1] == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }

    # cmd (str)
    assert parse_tasks({"scripts": {"ls": {"cmd": "+ls -la"}}})[1] == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }

    # cmd (list)
    assert parse_tasks({"scripts": {"ls": {"cmd": ["+ls", "-la"]}}})[1] == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }


def test_call() -> None:
    """Try to parse a `call` command."""
    with pytest.raises(ValueError):
        parse_tasks({"scripts": {"ls": {"call": "ds:main"}}})


def test_bad_types() -> None:
    """Handle bad types."""
    # Basic unsupported command type.
    with pytest.raises(TypeError):
        parse_tasks({"scripts": {"X": False}})

    # Unsupported mapping type.
    with pytest.raises(TypeError):
        parse_tasks({"scripts": {"X": {"bad": ["A", "B", "C"]}}})


def test_load_formats() -> None:
    """Load known formats."""
    path = Path("examples") / "formats"
    assert Config.load(path / "Cargo.toml").parse()
    assert Config.load(path / "composer.json").parse()
    assert Config.load(path / "ds.toml").parse()
    assert Config.load(path / "package.json").parse()
    assert Config.load(path / "pyproject-ds.toml").parse()
    assert Config.load(path / "pyproject-pdm.toml").parse()
    assert Config.load(path / "pyproject-rye.toml").parse()


def test_load_readme() -> None:
    """Load README examples."""
    path = Path("examples") / "readme"
    assert Config.load(path / "basic.toml").parse()
    assert Config.load(path / "composite.toml").parse()
    assert Config.load(path / "error-suppression.toml").parse()
    assert Config.load(path / "example.toml").parse()


def test_load_full() -> None:
    """Load complex toml file."""
    assert Config.load(Path("examples") / "full.toml").parse()


def test_unknown_name() -> None:
    """Try to parse a file with an unknown file name."""
    assert Config.load(Path("examples") / "unknown.json").parse()


def test_unknown_suffix() -> None:
    """Try to read a file with an unknown suffix."""
    with pytest.raises(LookupError):
        Config.load(Path("unknown-suffix.txt"))


def test_bad_key() -> None:
    """Try to parse a file with an unknown format."""
    with pytest.raises(LookupError):
        Config.load(Path("examples") / "bad-key.toml").parse()


def test_bad_value() -> None:
    """Try to parse a file with an invalid type."""
    with pytest.raises(TypeError):
        Config.load(Path("examples") / "bad-value.toml").parse()


def test_bad_loop() -> None:
    """Try to parse a loop."""
    with pytest.raises(CycleError):
        check_cycles(
            {
                "a": Task(depends=[Task(name="#composite", cmd="b")]),
                "b": Task(depends=[Task(name="#composite", cmd="a")]),
            }
        )
