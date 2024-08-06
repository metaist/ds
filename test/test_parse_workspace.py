"""Test workspace configurations."""

# std
from pathlib import Path

# lib
import pytest

# pkg
from ds.configs import Config

BASE_PATH = Path("examples") / "workspace"


def test_load() -> None:
    """Test loading a workspace configuration."""
    pkgs = BASE_PATH / "members"
    config = Config.load(BASE_PATH / "package.json").parse(True)
    assert config.members == [pkgs / "a", pkgs / "b"]

    config = Config.load(BASE_PATH / "pyproject-rye.toml").parse(True)
    assert config.members == [pkgs / "a", pkgs / "b"]

    config = Config.load(BASE_PATH / "Cargo.toml").parse(True)
    assert config.members == [pkgs / "a", pkgs / "b"]


def test_load_no_workspace() -> None:
    """Try loading when there's no workspace config."""
    with pytest.raises(LookupError):
        Config.load(BASE_PATH / "members" / "a" / "Cargo.toml").parse(True)
