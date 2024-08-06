"""Test generic config parsing."""

# std
from pathlib import Path
import sys

# lib
import pytest

# pkg
from ds.configs import load_config
from ds.configs import parse_config
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
    assert parse_config({"scripts": {"#disabled": "ls -la"}}) == {}

    # tasks with empty or all-whitespace names are disabled
    assert parse_config({"scripts": {"": "ls -la", "  ": "exit 1"}}) == {}


def test_nop() -> None:
    """Parse an empty task."""
    assert parse_config({"scripts": {"nop": ""}}) == {"nop": Task(name="nop")}


def test_string() -> None:
    """Parse basic string command."""
    assert parse_config({"scripts": {"ls": "ls -la"}}) == {
        "ls": Task(name="ls", cmd="ls -la")
    }

    # Task commands that start with a hyphen suppress errors.
    assert parse_config({"scripts": {"ls": "+ls -la"}}) == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }


def test_composite() -> None:
    """Parse a `composite` command."""
    # ds-style
    assert parse_config({"scripts": {"all": ["+clean", "build"]}}) == {
        "all": Task(
            name="all",
            depends=[
                Task(name="#composite", cmd="clean", keep_going=True),
                Task(name="#composite", cmd="build"),
            ],
        )
    }

    # pdm-style
    assert parse_config({"scripts": {"all": {"composite": ["clean", "build"]}}}) == {
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
    assert parse_config({"scripts": {"ls": {"shell": "+ls -la"}}}) == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }

    # cmd (str)
    assert parse_config({"scripts": {"ls": {"cmd": "+ls -la"}}}) == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }

    # cmd (list)
    assert parse_config({"scripts": {"ls": {"cmd": ["+ls", "-la"]}}}) == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }


def test_call() -> None:
    """Try to parse a `call` command."""
    with pytest.raises(ValueError):
        parse_config({"scripts": {"ls": {"call": "ds:main"}}})


def test_bad_types() -> None:
    """Handle bad types."""
    # Basic unsupported command type.
    with pytest.raises(TypeError):
        parse_config({"scripts": {"X": False}})

    # Unsupported mapping type.
    with pytest.raises(TypeError):
        parse_config({"scripts": {"X": {"bad": ["A", "B", "C"]}}})


def test_load_formats() -> None:
    """Load known formats."""
    path = Path("examples") / "formats"
    assert load_config(path / "Cargo.toml")
    assert load_config(path / "composer.json")
    assert load_config(path / "ds.toml")
    assert load_config(path / "package.json")
    assert load_config(path / "pyproject-ds.toml")
    assert load_config(path / "pyproject-pdm.toml")
    assert load_config(path / "pyproject-rye.toml")


def test_load_readme() -> None:
    """Load README examples."""
    path = Path("examples") / "readme"
    assert load_config(path / "basic.toml")
    assert load_config(path / "composite.toml")
    assert load_config(path / "error-suppression.toml")
    assert load_config(path / "example.toml")


def test_load_full() -> None:
    """Load complex toml file."""
    assert load_config(Path("examples") / "full.toml")


def test_unknown_name() -> None:
    """Try to parse a file with an unknown file name."""
    assert load_config(Path("examples") / "unknown.json")


def test_unknown_suffix() -> None:
    """Try to read a file with an unknown suffix."""
    with pytest.raises(LookupError):
        load_config(Path("foo.txt"))


def test_bad_key() -> None:
    """Try to parse a file with an unknown format."""
    with pytest.raises(LookupError):
        assert parse_config({}) == {}

    with pytest.raises(LookupError):
        assert load_config(Path("examples") / "bad-key.toml") == {}


def test_bad_value() -> None:
    """Try to parse a file with an invalid type."""
    with pytest.raises(TypeError):
        load_config(Path("examples") / "bad-value.toml")


def test_bad_loop() -> None:
    """Try to parse a loop."""
    with pytest.raises(CycleError):
        check_cycles(
            {
                "a": Task(depends=[Task(name="#composite", cmd="b")]),
                "b": Task(depends=[Task(name="#composite", cmd="a")]),
            }
        )
