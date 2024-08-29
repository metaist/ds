"""Test configuration loading / parsing."""

# std
from pathlib import Path

# lib
import pytest

# pkg
from ds.parsers import find_and_parse
from ds.parsers import parse

EXAMPLES = Path("examples")
"""Path to examples."""

WORKSPACE = EXAMPLES / "workspace"
"""Path to workspace examples."""


def test_no_config() -> None:
    """Fail to find a config."""
    with pytest.raises(FileNotFoundError):
        assert find_and_parse(Path("/"))


def test_config_find() -> None:
    """Find a config."""
    assert find_and_parse(Path(__file__)) is not None


def test_no_section() -> None:
    """Skip files without scripts."""
    assert find_and_parse(EXAMPLES / "misc")


def test_load_readme() -> None:
    """Load README examples."""
    path = EXAMPLES / "readme"
    assert parse(path / "basic.toml")
    assert parse(path / "composite.toml")
    assert parse(path / "error-suppression.toml")
    assert parse(path / "example.toml")


def test_unknown_name() -> None:
    """Try to parse a file with an unknown file name."""
    assert parse(EXAMPLES / "misc" / "unknown.json")


def test_unknown_suffix() -> None:
    """Try to read a file with an unknown suffix."""
    with pytest.raises(LookupError):
        parse(EXAMPLES / "misc" / "unknown-suffix.txt")


def test_bad_key() -> None:
    """Try to parse a file with an unknown format."""
    with pytest.raises(LookupError):
        parse(EXAMPLES / "misc" / "bad-key.toml")


def test_bad_value() -> None:
    """Try to parse a file with an invalid type."""
    with pytest.raises(LookupError):
        parse(EXAMPLES / "misc" / "bad-value.toml")


def test_load_no_workspace() -> None:
    """Try loading when there's no workspace config."""
    with pytest.raises(LookupError):
        parse(WORKSPACE / "members" / "a" / "Cargo.toml", require_workspace=True)


def test_load_workspace() -> None:
    """Test loading a workspace configuration."""
    pkgs = WORKSPACE / "members"
    expected = {pkgs / "a": True, pkgs / "b": True, pkgs / "x": False}

    config = parse(WORKSPACE / "Cargo.toml", True)
    assert config.members == expected

    config = parse(WORKSPACE / "ds.toml", True)
    assert config.members == expected

    config = parse(WORKSPACE / "package.json", True)
    assert config.members == expected

    config = parse(WORKSPACE / "pyproject-ds.toml", True)
    assert config.members == expected

    config = parse(WORKSPACE / "pyproject-rye.toml", True)
    assert config.members == {**{WORKSPACE.resolve(): True}, **expected}

    config = parse(WORKSPACE / "pyproject-uv.toml", True)
    assert config.members == expected
