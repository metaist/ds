"""Test env vars and interpolation."""

# std
from typing import Union
from typing import Optional

# lib
import pytest

# pkg
from ds.env import interpolate_args
from ds.env import makefile_loads
from ds.env import wrap_cmd
from ds.symbols import ARG_PREFIX
from ds.symbols import ARG_REST


def arg(
    n: Union[int, str, None] = None,
    b: bool = False,
    d: Optional[str] = None,
) -> str:
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
        "$ echo \\\n"
        "    'This is a really long string that cannot be broken.' \\\n"
        "    ;"
    )


def test_makefile_loads() -> None:
    """Parse basic `Makefile`."""
    # empty
    assert makefile_loads("", debug=True) == {"Makefile": {}}

    # not supported: variables
    assert makefile_loads("foo = bar", debug=True) == {"Makefile": {}}

    # comments
    assert makefile_loads("# Commented Line") == {"Makefile": {}}
    assert makefile_loads("\n\n") == {"Makefile": {}}

    # empty target
    assert makefile_loads("target:") == {
        "Makefile": {"target": {"composite": [], "shell": "", "verbatim": True}}
    }

    # has prerequisites, no recipe
    assert makefile_loads("target: pre1 pre2") == {
        "Makefile": {
            "target": {"composite": ["pre1", "pre2"], "shell": "", "verbatim": True}
        }
    }

    # no prerequisites, has recipe
    assert makefile_loads("target:\n\techo Works") == {
        "Makefile": {
            "target": {"composite": [], "shell": "echo Works\n", "verbatim": True}
        }
    }

    # has prerequisites and recipe
    assert makefile_loads("target : pre1 pre2\n\techo Works") == {
        "Makefile": {
            "target": {
                "composite": ["pre1", "pre2"],
                "shell": "echo Works\n",
                "verbatim": True,
            }
        }
    }

    # has prerequisites and recipe starting on same line
    assert makefile_loads("target : pre1 -pre2 ;echo Hello\n\techo world") == {
        "Makefile": {
            "target": {
                "composite": ["pre1", "+pre2"],
                "shell": "echo Hello\necho world\n",
                "verbatim": True,
            }
        }
    }

    # no prerequisites, but recipe starting on same line
    assert makefile_loads("target : ;echo Hello\n\t-echo world") == {
        "Makefile": {
            "target": {
                "composite": [],
                "shell": "echo Hello\necho world\n",
                "verbatim": True,
                "keep_going": True,
            }
        }
    }

    # line continuation & .RECIPEPREFIX
    # are exercised in the sample file
