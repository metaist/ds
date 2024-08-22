"""Test configuration loading / parsing."""

# std
from pathlib import Path

# lib
import pytest

# pkg
from ds.configs import Config
from ds.configs import find_config
from ds.configs import glob_apply
from ds.configs import glob_refine
from ds.symbols import GLOB_EXCLUDE

EXAMPLES = Path("examples")
"""Path to examples."""

WORKSPACE = EXAMPLES / "workspace"
"""Path to workspace examples."""


def test_no_config() -> None:
    """Fail to find a config."""
    with pytest.raises(FileNotFoundError):
        assert find_config(Path("/")) is None

    with pytest.raises(FileNotFoundError):
        assert find_config(Path("/"), debug=True) is None


def test_find_config() -> None:
    """Successfully find a config."""
    assert find_config(Path(__file__)) is not None


def test_load_readme() -> None:
    """Load README examples."""
    path = EXAMPLES / "readme"
    assert Config.load(path / "basic.toml").parse()
    assert Config.load(path / "composite.toml").parse()
    assert Config.load(path / "error-suppression.toml").parse()
    assert Config.load(path / "example.toml").parse()


def test_load_formats() -> None:
    """Load known formats."""
    path = EXAMPLES / "formats"
    assert Config.load(path / "Cargo.toml").parse()
    assert Config.load(path / "composer.json").parse()
    assert Config.load(path / "ds.toml").parse()
    assert Config.load(path / "Makefile").parse()
    assert Config.load(path / "package.json").parse()
    assert Config.load(path / "pyproject-ds.toml").parse()
    assert Config.load(path / "pyproject-pdm.toml").parse()
    assert Config.load(path / "pyproject-rye.toml").parse()


def test_unknown_name() -> None:
    """Try to parse a file with an unknown file name."""
    assert Config.load(EXAMPLES / "misc" / "unknown.json").parse()


def test_unknown_suffix() -> None:
    """Try to read a file with an unknown suffix."""
    with pytest.raises(LookupError):
        Config.load(Path("unknown-suffix.txt"))


def test_no_section() -> None:
    """Try to parse a file with no scripts."""
    assert find_config(EXAMPLES / "misc")


def test_bad_key() -> None:
    """Try to parse a file with an unknown format."""
    with pytest.raises(LookupError):
        Config.load(EXAMPLES / "misc" / "bad-key.toml").parse()


def test_bad_value() -> None:
    """Try to parse a file with an invalid type."""
    with pytest.raises(TypeError):
        Config.load(EXAMPLES / "misc" / "bad-value.toml").parse()


def test_glob_apply() -> None:
    """Apply globs."""
    m = WORKSPACE / "members"

    got = glob_apply(WORKSPACE, ["*"])
    want = {p: True for p in WORKSPACE.glob("*")}
    assert got == want

    got = glob_apply(WORKSPACE, [f"{GLOB_EXCLUDE}*"])
    want = {p: False for p in WORKSPACE.glob("*")}
    assert got == want

    got = glob_apply(WORKSPACE, ["members/*", "!members/x"])
    want = {m / "a": True, m / "b": True, m / "x": False}
    assert got == want


def test_glob_refine() -> None:
    """Constrain some values."""
    m = WORKSPACE / "members"

    start = {m / "a": False, m / "b": False, m / "x": False}
    assert glob_refine(WORKSPACE, ["members/a"], start) == {**start, **{m / "a": True}}
    assert glob_refine(WORKSPACE, ["**/b", "!*", "*/x"], start) == {
        **start,
        **{m / "x": True},
    }

    # prevent new entries
    start = {m / "a": False, m / "b": False}
    assert glob_refine(WORKSPACE, ["members/x"], start) == start


def test_load_no_workspace() -> None:
    """Try loading when there's no workspace config."""
    with pytest.raises(LookupError):
        Config.load(WORKSPACE / "members" / "a" / "Cargo.toml").parse(True)


def test_load_workspace() -> None:
    """Test loading a workspace configuration."""
    pkgs = WORKSPACE / "members"
    expected = {pkgs / "a": True, pkgs / "b": True, pkgs / "x": False}

    config = Config.load(WORKSPACE / "Cargo.toml").parse(True)
    assert config.members == expected

    config = Config.load(WORKSPACE / "ds.toml").parse(True)
    assert config.members == expected

    config = Config.load(WORKSPACE / "package.json").parse(True)
    assert config.members == expected

    config = Config.load(WORKSPACE / "pyproject-ds.toml").parse(True)
    assert config.members == expected

    config = Config.load(WORKSPACE / "pyproject-rye.toml").parse(True)
    assert config.members == expected

    config = Config.load(WORKSPACE / "pyproject-uv.toml").parse(True)
    assert config.members == expected
