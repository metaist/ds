"""Test generic config parsing."""

# std
from pathlib import Path

# lib
import pytest

# pkg
from ds import load_config
from ds import parse_config
from ds import Task
from ds import PYTHON_CALL


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
    assert parse_config({"scripts": {"ls": "-ls -la"}}) == {
        "ls": Task(name="ls", cmd="ls -la", keep_going=True)
    }


def test_composite() -> None:
    """Parse a `composite` command."""
    # ds-style
    assert parse_config({"scripts": {"all": ["clean", "build"]}}) == {
        "all": Task(name="all", depends=[Task(cmd="clean"), Task(cmd="build")])
    }

    # pdm-style
    assert parse_config({"scripts": {"all": {"composite": ["clean", "build"]}}}) == {
        "all": Task(name="all", depends=[Task(cmd="clean"), Task(cmd="build")])
    }


def test_shell_cmd() -> None:
    """Parse a `shell` or `cmd` command."""
    # shell
    assert parse_config({"scripts": {"ls": {"shell": "ls -la"}}}) == {
        "ls": Task(name="ls", cmd="ls -la")
    }

    # cmd (str)
    assert parse_config({"scripts": {"ls": {"cmd": "ls -la"}}}) == {
        "ls": Task(name="ls", cmd="ls -la")
    }

    # cmd (list)
    assert parse_config({"scripts": {"ls": {"cmd": ["ls", "-la"]}}}) == {
        "ls": Task(name="ls", cmd="ls -la")
    }


def test_call() -> None:
    """Parse a `call` command."""
    assert parse_config({"scripts": {"ls": {"call": "ds:main"}}}) == {
        "ls": Task(name="ls", cmd=PYTHON_CALL.format(module="ds", func="main()"))
    }

    # you can provide static arguments
    assert parse_config({"scripts": {"ls": {"call": "ds:main(['ds'])"}}}) == {
        "ls": Task(name="ls", cmd=PYTHON_CALL.format(module="ds", func="main(['ds'])"))
    }


def test_bad_types() -> None:
    """Handle bad types."""
    # Basic unsupported command type.
    with pytest.raises(TypeError):
        parse_config({"scripts": {"X": False}})

    # Unsupported mapping type.
    with pytest.raises(TypeError):
        parse_config({"scripts": {"X": {"bad": ["A", "B", "C"]}}})


def test_load_ds() -> None:
    """Load ds.toml file."""
    assert load_config(Path("examples") / "ds.toml")


def test_load_full() -> None:
    """Load complex toml file."""
    assert load_config(Path("examples") / "full.toml")


def test_pyproject() -> None:
    """Load pyproject.toml file."""
    assert load_config(Path("examples") / "pyproject.toml")


def test_load_npm() -> None:
    """Load package.json file."""
    assert load_config(Path("examples") / "package.json")


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
