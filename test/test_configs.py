"""Test configuration loading / parsing."""

# std
from pathlib import Path

# lib
import pytest

# pkg
from ds.configs import Config


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
