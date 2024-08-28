"""Test `Makefile` parser."""

# std
from dataclasses import replace
from pathlib import Path

# lib
import pytest

# pkg
from . import EXAMPLE_FORMATS
from . import nest
from ds.args import Args
from ds.parsers import Config
from ds.parsers.makefile import loads
from ds.parsers.makefile import parse_tasks
from ds.parsers.makefile import parse_workspace
from ds.tasks import Task

PATH = Path("Makefile")
"""Default path."""

KEY = "recipes"
"""Default key."""

TASK = Task(origin=PATH, origin_key=KEY)
"""Default task data."""


def test_workspace() -> None:
    """Workspace not implemented."""
    with pytest.raises(NotImplementedError):
        parse_workspace(Config(PATH, {}))


def test_format() -> None:
    """End-to-end test of the format."""
    path = EXAMPLE_FORMATS / "Makefile"
    config = Config(path, loads(path.read_text()))
    tasks = parse_tasks(Args(file=path), config)
    assert tasks


def test_tasks_basic() -> None:
    """Basic task."""
    data = nest(KEY, {"a": {"composite": [], "shell": "b", "verbatim": True}})
    expected = {"a": replace(TASK, name="a", cmd="b", verbatim=True)}
    assert parse_tasks(Args(), Config(PATH, data)) == expected


def test_makefile_loads() -> None:
    """Parse basic `Makefile`."""
    # empty
    assert loads("", debug=True) == {"recipes": {}}

    # not supported: variables
    assert loads("foo = bar", debug=True) == {"recipes": {}}

    # comments
    assert loads("# Commented Line") == {"recipes": {}}
    assert loads("\n\n") == {"recipes": {}}

    # empty target
    assert loads("target:") == {
        "recipes": {"target": {"composite": [], "shell": "", "verbatim": True}}
    }

    # has prerequisites, no recipe
    assert loads("target: pre1 pre2") == {
        "recipes": {
            "target": {"composite": ["pre1", "pre2"], "shell": "", "verbatim": True}
        }
    }

    # no prerequisites, has recipe
    assert loads("target:\n\techo Works") == {
        "recipes": {
            "target": {"composite": [], "shell": "echo Works\n", "verbatim": True}
        }
    }

    # has prerequisites and recipe
    assert loads("target : pre1 pre2\n\techo Works") == {
        "recipes": {
            "target": {
                "composite": ["pre1", "pre2"],
                "shell": "echo Works\n",
                "verbatim": True,
            }
        }
    }

    # has prerequisites and recipe starting on same line
    assert loads("target : pre1 -pre2 ;echo Hello\n\techo world") == {
        "recipes": {
            "target": {
                "composite": ["pre1", "+pre2"],
                "shell": "echo Hello\necho world\n",
                "verbatim": True,
            }
        }
    }

    # no prerequisites, but recipe starting on same line
    assert loads("target : ;echo Hello\n\t-echo world") == {
        "recipes": {
            "target": {
                "composite": [],
                "shell": "echo Hello\necho world\n",
                "verbatim": True,
                "keep_going": True,
            }
        }
    }

    # line continuation & .RECIPEPREFIX
    assert loads(
        """
.RECIPEPREFIX=>
target:
>echo "Hello \\
>world"
"""
    ) == {
        "recipes": {
            "target": {
                "composite": [],
                "shell": 'echo "Hello \\\nworld"\n',
                "verbatim": True,
            }
        }
    }
