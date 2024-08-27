"""Test configuration loading / parsing."""

# std
from pathlib import Path

# lib
import pytest

# pkg
from ds.parsers import Config
from ds.searchers import glob_paths
from ds.symbols import GLOB_EXCLUDE

EXAMPLES = Path("examples")
"""Path to examples."""

WORKSPACE = EXAMPLES / "workspace"
"""Path to workspace examples."""


def test_no_config() -> None:
    """Fail to find a config."""
    with pytest.raises(FileNotFoundError):
        assert Config.find(Path("/")) is None


def test_config_find() -> None:
    """Successfully find a config."""
    assert Config.find(Path(__file__)) is not None


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
    assert Config.load(path / "pyproject-ds.toml").parse()
    assert Config.load(path / "pyproject-pdm.toml").parse()


def test_unknown_name() -> None:
    """Try to parse a file with an unknown file name."""
    assert Config.load(EXAMPLES / "misc" / "unknown.json").parse()


def test_unknown_suffix() -> None:
    """Try to read a file with an unknown suffix."""
    with pytest.raises(LookupError):
        Config.load(Path("unknown-suffix.txt"))


def test_no_section() -> None:
    """Try to parse a file with no scripts."""
    assert Config.find(EXAMPLES / "misc")


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

    got = glob_paths(
        WORKSPACE, ["*"], allow_all=False, allow_excludes=True, allow_new=True
    )
    want = {p: True for p in WORKSPACE.glob("*")}
    assert got == want

    got = glob_paths(
        WORKSPACE,
        [f"{GLOB_EXCLUDE}*"],
        allow_all=False,
        allow_excludes=True,
        allow_new=True,
    )
    want = {p: False for p in WORKSPACE.glob("*")}
    assert got == want

    got = glob_paths(
        WORKSPACE,
        ["members/*", "!members/x"],
        allow_all=False,
        allow_excludes=True,
        allow_new=True,
    )
    want = {m / "a": True, m / "b": True, m / "x": False}
    assert got == want


def test_glob_paths() -> None:
    """Constrain some values."""
    m = WORKSPACE / "members"

    start = {m / "a": False, m / "b": False, m / "x": False}
    assert glob_paths(
        WORKSPACE,
        ["members/a"],
        previous=start,
        allow_all=True,
        allow_excludes=True,
        allow_new=False,
    ) == {**start, **{m / "a": True}}
    assert glob_paths(
        WORKSPACE,
        ["**/b", "!*", "*/x"],
        previous=start,
        allow_all=True,
        allow_excludes=True,
        allow_new=False,
    ) == {
        **start,
        **{m / "x": True},
    }

    # prevent new entries
    start = {m / "a": False, m / "b": False}
    assert (
        glob_paths(
            WORKSPACE,
            ["members/x"],
            previous=start,
            allow_all=True,
            allow_excludes=True,
            allow_new=False,
        )
        == start
    )


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
