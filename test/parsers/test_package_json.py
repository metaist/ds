"""Test `npm` parser."""

# std
from dataclasses import replace
from pathlib import Path
from typing import Any
from typing import Dict

# lib
import pytest

# pkg
from ds.args import Args
from ds.parsers import Config
from ds.parsers.package_json import parse_tasks
from ds.parsers.package_json import parse_workspace
from ds.tasks import Task
from ds.symbols import TASK_COMPOSITE
from ds.symbols import TASK_KEEP_GOING

EXAMPLES = Path(__file__).parent.parent.parent / "examples"
EXAMPLE_WORKSPACE = EXAMPLES / "workspace"
EXAMPLE_FORMAT = EXAMPLES / "formats" / "package.json"

TASK = Task(origin=Path("package.json"), origin_key="scripts")
"""Default task to manipulate."""


def test_workspace_missing() -> None:
    """Missing workspace."""
    with pytest.raises(KeyError):
        parse_workspace(Config(Path(), {}))


def test_workspace_empty() -> None:
    """Empty workspace."""
    data: Dict[str, Any] = {"workspaces": []}
    assert parse_workspace(Config(Path(), data)) == {}


def test_workspace_basic() -> None:
    """Workspace members using strings."""
    path = EXAMPLE_WORKSPACE / "package.json"
    data: Dict[str, Any] = {"workspaces": ["members/a", "members/b", "does-not-exist"]}
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        # non-existent member is skipped
    }
    assert parse_workspace(Config(path, data)) == expected


def test_workspace_glob() -> None:
    """Workspace members using globs."""
    path = EXAMPLE_WORKSPACE / "package.json"
    data: Dict[str, Any] = {"workspaces": ["members/*", "!members/x"]}
    expected = {
        path.parent / "members" / "a": True,
        path.parent / "members" / "b": True,
        path.parent / "members" / "x": False,  # members/x is excluded
    }
    assert parse_workspace(Config(path, data)) == expected


def test_tasks_missing() -> None:
    """File without scripts."""
    args = Args()
    config = Config(Path("package.json"), {})
    with pytest.raises(KeyError):
        parse_tasks(args, config)


def test_tasks_empty() -> None:
    """Empty scripts."""
    args = Args()
    config = Config(Path("package.json"), {"scripts": {}})
    assert parse_tasks(args, config) == {}


def test_task_disabled() -> None:
    """Disabled task."""
    args = Args()
    config = Config(Path("package.json"), {"scripts": {"#a": "b"}})
    assert parse_tasks(args, config) == {}


def test_task_help() -> None:
    """Task help."""
    args = Args()
    config = Config(Path("package.json"), {"scripts": {"#a": "run things", "a": "b"}})
    expected = {"a": replace(TASK, name="a", cmd="b", help="run things")}
    assert parse_tasks(args, config) == expected


def test_task_cmd() -> None:
    """Basic task."""
    args = Args()
    config = Config(Path("package.json"), {"scripts": {"a": "b"}})
    expected = {"a": replace(TASK, name="a", cmd="b")}
    assert parse_tasks(args, config) == expected


def test_task_args() -> None:
    """Task args."""
    args = Args()

    # argument interpolation: via reference
    config = Config(Path("package.json"), {"scripts": {"a": "ls", "b": "a -lah"}})
    expected = {
        "a": replace(TASK, name="a", cmd="ls"),
        "b": replace(TASK, name="b", cmd="a -lah"),
    }
    assert parse_tasks(args, config) == expected

    # argument interpolation: via CLI
    config = Config(Path("package.json"), {"scripts": {"a": "ls $1", "b": "a -lah"}})
    expected = {
        "a": replace(TASK, name="a", cmd="ls $1"),
        "b": replace(TASK, name="b", cmd="a -lah"),
    }
    assert parse_tasks(args, config) == expected


def test_task_pre() -> None:
    args = Args(pre=True)
    config = Config(
        Path("package.json"),
        {
            "scripts": {
                "prefix": "echo prefix",
                "fix": "echo fix",
                "postfix": "echo postfix",
            }
        },
    )
    expected = {
        "prefix": Task(
            origin=config.path, origin_key="scripts", name="prefix", cmd="echo prefix"
        ),
        "fix": Task(
            origin=config.path,
            origin_key="scripts",
            name="fix",
            depends=[
                Task(
                    origin=config.path,
                    origin_key="scripts",
                    name=TASK_COMPOSITE,
                    cmd="prefix",
                ),
                Task(
                    origin=config.path,
                    origin_key="scripts",
                    name=TASK_COMPOSITE,
                    cmd="echo fix",
                ),
            ],
        ),
        "postfix": Task(
            origin=config.path, origin_key="scripts", name="postfix", cmd="echo postfix"
        ),
    }
    assert parse_tasks(args, config) == expected


def test_task_post() -> None:
    args = Args(post=True)
    config = Config(
        Path("package.json"),
        {
            "scripts": {
                "prefix": "echo prefix",
                "fix": "echo fix",
                "postfix": "echo postfix",
            }
        },
    )
    expected = {
        "prefix": Task(
            origin=config.path, origin_key="scripts", name="prefix", cmd="echo prefix"
        ),
        "fix": Task(
            origin=config.path,
            origin_key="scripts",
            name="fix",
            depends=[
                Task(
                    origin=config.path,
                    origin_key="scripts",
                    name=TASK_COMPOSITE,
                    cmd="echo fix",
                ),
                Task(
                    origin=config.path,
                    origin_key="scripts",
                    name=TASK_COMPOSITE,
                    cmd="postfix",
                ),
            ],
        ),
        "postfix": Task(
            origin=config.path, origin_key="scripts", name="postfix", cmd="echo postfix"
        ),
    }
    assert parse_tasks(args, config) == expected


def test_task_depends() -> None:
    """Task depends."""
    args = Args(pre=True, post=True)
    config = Config(
        Path("package.json"),
        {
            "scripts": {
                "prefix": "echo prefix",
                "fix": "echo fix",
                "postfix": "echo postfix",
            }
        },
    )
    expected = {
        "prefix": Task(
            origin=config.path, origin_key="scripts", name="prefix", cmd="echo prefix"
        ),
        "fix": Task(
            origin=config.path,
            origin_key="scripts",
            name="fix",
            depends=[
                Task(
                    origin=config.path,
                    origin_key="scripts",
                    name=TASK_COMPOSITE,
                    cmd="prefix",
                ),
                Task(
                    origin=config.path,
                    origin_key="scripts",
                    name=TASK_COMPOSITE,
                    cmd="echo fix",
                ),
                Task(
                    origin=config.path,
                    origin_key="scripts",
                    name=TASK_COMPOSITE,
                    cmd="postfix",
                ),
            ],
        ),
        "postfix": Task(
            origin=config.path, origin_key="scripts", name="postfix", cmd="echo postfix"
        ),
    }
    assert parse_tasks(args, config) == expected


def test_task_reference() -> None:
    """Non-standard: task reference"""
    args = Args()

    # task reference: apparent self-reference (but actually ok)
    config = Config(Path("package.json"), {"scripts": {"ls": "ls"}})
    expected = {
        "ls": replace(TASK, name="ls", cmd="ls"),
    }
    assert parse_tasks(args, config) == expected

    # task reference: loop (not ok)
    config = Config(Path("package.json"), {"scripts": {"a": "b", "b": "a"}})
    expected = {
        "a": replace(TASK, name="a", cmd="b"),
        "b": replace(TASK, name="b", cmd="a"),
    }
    assert parse_tasks(args, config) == expected


def test_keep_going() -> None:
    """Not supported: error suppression"""
    args = Args()
    config = Config(Path("package.json"), {"scripts": {"a": f"{TASK_KEEP_GOING}b"}})
    expected = {
        "a": Task(
            origin=config.path,
            origin_key="scripts",
            name="a",
            cmd=f"{TASK_KEEP_GOING}b",
            # NOTE: `keep_going` is not set
        )
    }
    assert parse_tasks(args, config) == expected
