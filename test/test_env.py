"""Test env vars and interpolation."""

# lib
import pytest

# pkg
from ds.env import interpolate_args
from ds.env import read_env
from ds.env import wrap_cmd
from ds.symbols import ARG_PREFIX
from ds.symbols import ARG_REST


def arg(n: int | str | None = None, b: bool = False, d: str | None = None) -> str:
    """Helper to produce args.

    >>> arg(1)
    '$1'
    >>> arg()
    '$@'

    Add braces:
    >>> arg(2, b=True)
    '${2}'

    Provide defaults:
    >>> arg(d="")
    '${@:-}'
    """
    name = n or ARG_REST
    if d is not None:
        b = True
        name = f"{name}:-{d}"
    return f"{ARG_PREFIX}{{{name}}}" if b else f"{ARG_PREFIX}{name}"


def test_interpolate_args() -> None:
    """Interpolate args properly."""
    assert interpolate_args("a b", ["c"]) == "a b c"
    assert interpolate_args(f"a {arg(1)} c", ["b"]) == "a b c"
    assert (
        interpolate_args(
            f"a {arg(1)} {arg(b=True)} {arg(3)} {arg()}",
            ["b", "c", "d"],
        )
        == "a b c d d c"
    )


def test_missing_args() -> None:
    """Try to interpolate with insufficient args."""
    with pytest.raises(IndexError):
        interpolate_args(f"ls {arg(1)}", [])


def test_default_args() -> None:
    """Add a default value for a missing arg."""
    cmd = f"ls {arg(1, d='foo')}"
    assert interpolate_args(cmd, []) == "ls foo"
    assert interpolate_args(cmd, ["bar"]) == "ls bar"
    assert interpolate_args(cmd, [""]) == "ls"


def test_pdm_args() -> None:
    """Test `pdm`-style arg interpolation."""
    cmd = "echo '--before {args} --after'"
    assert (
        interpolate_args(cmd, ["--something"]) == "echo '--before --something --after'"
    )

    cmd = "echo '--before {args:--default --value} --after'"
    assert (
        interpolate_args(cmd, ["--something"]) == "echo '--before --something --after'"
    )
    assert interpolate_args(cmd, []) == "echo '--before --default --value --after'"


def test_shell_metachars_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Warn when args contain shell metacharacters (issue #97)."""
    # Should warn for shell metacharacters
    interpolate_args("echo", ["; rm -rf /"])
    assert "shell metacharacters" in caplog.text
    assert "; rm -rf /" in caplog.text

    caplog.clear()

    # Should not warn for safe arguments
    interpolate_args("echo", ["hello", "world"])
    assert "shell metacharacters" not in caplog.text


def test_read_env_malformed_line(caplog: pytest.LogCaptureFixture) -> None:
    """Skip lines without '=' and warn (issue #104)."""
    # Should skip malformed lines and warn
    result = read_env("VALID=value\nmalformed line without equals\nALSO_VALID=ok")
    assert result == {"VALID": "value", "ALSO_VALID": "ok"}
    assert "malformed line" in caplog.text
    assert "malformed line without equals" in caplog.text


def test_read_env_self_referential(caplog: pytest.LogCaptureFixture) -> None:
    """Warn about self-referential variables (issue #118)."""
    from ds.env import TempEnv

    # Clear FOO from environment to ensure it's not set
    with TempEnv(FOO=None):
        result = read_env("FOO=$FOO")
        assert result == {"FOO": "$FOO"}  # value unchanged
        assert "Unresolved variable" in caplog.text
        assert "FOO" in caplog.text
        assert "Self-referential" in caplog.text

    caplog.clear()

    # Dollar sign not followed by valid variable name - no warning
    result = read_env("CMD=echo $")
    assert result == {"CMD": "echo $"}
    assert "Unresolved variable" not in caplog.text


def test_wrap_cmd() -> None:
    """Wrap commands."""
    # basic
    assert wrap_cmd("ls -lah") == "ls -lah"

    # duplicate spaces removed
    assert wrap_cmd("ls    -lah") == "ls -lah"

    # cleans up multiple commands
    assert "$ " + wrap_cmd("ls&&ls") == "$ ls &&\n  ls"
    assert "$ " + wrap_cmd("ls;ls") == "$ ls;\n  ls"

    assert (
        "$ " + wrap_cmd("what if a command is just really long", 20)
        == "$ what if a \\\n    command is \\\n    just really \\\n    long"
    )

    # no line continuation for list terminators
    assert "$ " + wrap_cmd(
        "cmd --with-long-options --another || "
        "call --and=another --some value that is big",
        40,
    ) == (
        "$ cmd --with-long-options --another ||\n"
        "  call --and=another --some value that \\\n"
        "    is big"
    )

    # long wrap with indent
    assert "$ " + wrap_cmd(
        "coverage run --branch --source=src -m pytest "
        "--doctest-modules "
        "--doctest-ignore-import-errors "
        "src test; "
        "coverage report --omit=src/cog_helpers.py -m"
    ) == (
        "$ coverage run --branch --source=src -m pytest --doctest-modules \\\n"
        "    --doctest-ignore-import-errors src test;\n"
        "  coverage report --omit=src/cog_helpers.py -m"
    )

    # long unbreakable line
    assert "$ " + wrap_cmd(
        "echo 'This is a really long string that cannot be broken.';", 40
    ) == (
        "$ echo \\\n    'This is a really long string that cannot be broken.' \\\n    ;"
    )


def test_wrap_cmd_length_limit() -> None:
    """Skip wrapping for very long commands (issue #116)."""
    from ds.env import MAX_WRAP_LENGTH

    # Normal length command is wrapped
    short_cmd = "echo hello world"
    assert wrap_cmd(short_cmd) == "echo hello world"

    # Command exceeding MAX_WRAP_LENGTH is returned as-is (just stripped)
    long_cmd = "echo " + "x" * (MAX_WRAP_LENGTH + 100)
    result = wrap_cmd(long_cmd)
    # Should return the command without wrapping
    assert result == long_cmd.strip()
    assert "\\" not in result  # no line continuation added
