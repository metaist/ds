"""Test parsing args."""

# std
from pathlib import Path
from shlex import split

# pkg
from ds.args import Args
from ds.args import parse_args
from ds.symbols import ARG_BEG
from ds.symbols import ARG_END
from ds.symbols import GLOB_ALL
from ds.symbols import TASK_COMPOSITE
from ds.tasks import Task


def test_arg_copy() -> None:
    """Arg.copy"""
    args = Args()
    assert args.copy() == args


def test_parse_options() -> None:
    """Parse standard options."""
    assert parse_args(split("-h")) == Args(help=True)
    assert parse_args(split("--help")) == Args(help=True)
    assert parse_args(split("--version")) == Args(version=True)

    assert parse_args(split("--debug")) == Args(debug=True, list_=True)
    assert parse_args(split("--dry-run")) == Args(dry_run=True, list_=True)

    assert parse_args(split("-l")) == Args(list_=True)
    assert parse_args(split("--list")) == Args(list_=True)

    assert parse_args(split("--cwd foo")) == Args(
        list_=True, cwd=Path("foo").resolve(), task=Task(cwd=Path("foo").resolve())
    )
    assert parse_args(split("-f foo")) == Args(list_=True, file_=Path("foo").resolve())
    assert parse_args(split("--file foo")) == Args(
        list_=True, file_=Path("foo").resolve()
    )

    assert parse_args(split("--env-file ./examples/formats/.env")) == Args(
        list_=True,
        env_file=Path("examples/formats/.env").resolve(),
        task=Task(env={"IN_DOT_ENV": "yes"}),
    )
    assert parse_args(split("-e VAR=VAL")) == Args(
        list_=True, env={"VAR": "VAL"}, task=Task(env={"VAR": "VAL"})
    )

    assert parse_args(split(f"-w '{GLOB_ALL}'")) == Args(
        list_=True, workspace=[GLOB_ALL]
    )

    assert parse_args(split(f"-w{GLOB_ALL}")) == Args(list_=True, workspace=[GLOB_ALL])


def test_parse_no_args() -> None:
    """Tasks without arguments."""
    assert parse_args(split("a b c")) == Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a"),
                Task(name=TASK_COMPOSITE, cmd="b"),
                Task(name=TASK_COMPOSITE, cmd="c"),
            ]
        )
    )


def test_implicit_args() -> None:
    """Implicit task args."""
    assert parse_args(split("a --arg1 --arg2")) == Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a --arg1 --arg2"),
            ]
        ),
    )


def test_implicit_arg_start() -> None:
    """Implicit task arg start / explicit end."""
    assert parse_args(split(f"a --arg {ARG_END} b")) == Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a --arg"),
                Task(name=TASK_COMPOSITE, cmd="b"),
            ]
        ),
    )


def test_explicit_task_args() -> None:
    """Explicit task args."""
    # separate
    assert parse_args(split(f"a {ARG_BEG} b {ARG_END} c")) == Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a b"),
                Task(name=TASK_COMPOSITE, cmd="c"),
            ]
        ),
    )

    # attached
    assert parse_args(split(f"a{ARG_BEG} b {ARG_END} c")) == Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a b"),
                Task(name=TASK_COMPOSITE, cmd="c"),
            ]
        ),
    )


def test_as_argv() -> None:
    """Test converting `Args` to `argv`."""
    assert Args(help=True).as_argv() == ["ds", "--help"]
    assert Args(version=True).as_argv() == ["ds", "--version"]
    assert Args(debug=True).as_argv() == ["ds", "--debug"]
    assert Args(dry_run=True).as_argv() == ["ds", "--dry-run"]
    assert Args(list_=True).as_argv() == ["ds", "--list"]
    assert Args(cwd=Path()).as_argv() == ["ds", "--cwd", str(Path())]
    assert Args(file_=Path()).as_argv() == ["ds", "--file", str(Path())]

    assert Args(env_file=Path("examples") / "formats" / ".env").as_argv() == [
        "ds",
        "--env-file",
        str(Path("examples") / "formats" / ".env"),
    ]
    assert Args(env={"NAME": "VALUE"}).as_argv() == ["ds", "--env", "'NAME=VALUE'"]
    assert Args(workspace=["*"]).as_argv() == ["ds", "--workspace", "*"]
    assert Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a b"),
                Task(name=TASK_COMPOSITE, cmd="c"),
            ]
        ),
    ).as_argv() == ["ds", "a", ARG_BEG, "b", ARG_END, "c", ARG_BEG, ARG_END]
