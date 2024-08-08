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

    assert parse_args(split("-l")) == Args(list_=True)
    assert parse_args(split("--list")) == Args(list_=True)

    assert parse_args(split("--cwd foo")) == Args(list_=True, cwd=Path("foo").resolve())
    assert parse_args(split("-f foo")) == Args(list_=True, file_=Path("foo").resolve())
    assert parse_args(split("--file foo")) == Args(
        list_=True, file_=Path("foo").resolve()
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
                Task(name=TASK_COMPOSITE, cmd="a", allow_shell=False),
                Task(name=TASK_COMPOSITE, cmd="b", allow_shell=False),
                Task(name=TASK_COMPOSITE, cmd="c", allow_shell=False),
            ]
        )
    )


def test_implicit_args() -> None:
    """Implicit task args."""
    assert parse_args(split("a --arg1 --arg2")) == Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a --arg1 --arg2", allow_shell=False),
            ]
        ),
    )


def test_implicit_arg_start() -> None:
    """Implicit task arg start / explicit end."""
    assert parse_args(split(f"a --arg {ARG_END} b")) == Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a --arg", allow_shell=False),
                Task(name=TASK_COMPOSITE, cmd="b", allow_shell=False),
            ]
        ),
    )


def test_explicit_task_args() -> None:
    """Explicit task args."""
    # separate
    assert parse_args(split(f"a {ARG_BEG} b {ARG_END} c")) == Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a b", allow_shell=False),
                Task(name=TASK_COMPOSITE, cmd="c", allow_shell=False),
            ]
        ),
    )

    # attached
    assert parse_args(split(f"a{ARG_BEG} b {ARG_END} c")) == Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a b", allow_shell=False),
                Task(name=TASK_COMPOSITE, cmd="c", allow_shell=False),
            ]
        ),
    )


def test_as_argv() -> None:
    """Test converting `Args` to `argv`."""
    assert Args(help=True).as_argv() == ["ds", "--help"]
    assert Args(version=True).as_argv() == ["ds", "--version"]
    assert Args(debug=True).as_argv() == ["ds", "--debug"]
    assert Args(cwd=Path()).as_argv() == ["ds", "--cwd", str(Path())]
    assert Args(file_=Path()).as_argv() == ["ds", "--file", str(Path())]
    assert Args(workspace=["*"]).as_argv() == ["ds", "--workspace", "*"]
    assert Args(list_=True).as_argv() == ["ds", "--list"]
    assert Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a b", allow_shell=False),
                Task(name=TASK_COMPOSITE, cmd="c", allow_shell=False),
            ]
        ),
    ).as_argv() == ["ds", "a", ARG_BEG, "b", ARG_END, "c", ARG_BEG, ARG_END]
