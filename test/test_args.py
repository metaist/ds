"""Test parsing args."""

# std
from pathlib import Path
from shlex import split

# pkg
from ds.args import Args
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
    assert Args.parse(split("-h")) == Args(help=True)
    assert Args.parse(split("--help")) == Args(help=True)
    assert Args.parse(split("--version")) == Args(version=True)

    assert Args.parse(split("--debug")) == Args(debug=True, list_=True)
    assert Args.parse(split("--dry-run")) == Args(dry_run=True, list_=True)

    assert Args.parse(split("-l")) == Args(list_=True)
    assert Args.parse(split("--list")) == Args(list_=True)

    assert Args.parse(split("--cwd foo")) == Args(
        list_=True, cwd=Path("foo").resolve(), task=Task(cwd=Path("foo").resolve())
    )
    assert Args.parse(split("-f foo")) == Args(list_=True, file=Path("foo").resolve())
    assert Args.parse(split("--file foo")) == Args(
        list_=True, file=Path("foo").resolve()
    )

    assert Args.parse(split("--env-file ./examples/formats/.env")) == Args(
        list_=True,
        env_file=Path("examples/formats/.env").resolve(),
        task=Task(env_file=Path("examples/formats/.env").resolve()),
    )
    assert Args.parse(split("-e VAR=VAL")) == Args(
        list_=True, env={"VAR": "VAL"}, task=Task(env={"VAR": "VAL"})
    )

    assert Args.parse(split("--parallel")) == Args(
        parallel=True, list_=True, task=Task(parallel=True)
    )

    assert Args.parse(split(f"-w '{GLOB_ALL}'")) == Args(
        list_=True, workspace=[GLOB_ALL]
    )

    assert Args.parse(split(f"-w{GLOB_ALL}")) == Args(list_=True, workspace=[GLOB_ALL])


def test_parse_no_args() -> None:
    """Tasks without arguments."""
    assert Args.parse(split("a b c")) == Args(
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
    assert Args.parse(split("a --arg1 --arg2")) == Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a --arg1 --arg2"),
            ]
        ),
    )


def test_implicit_arg_start() -> None:
    """Implicit task arg start / explicit end."""
    assert Args.parse(split(f"a --arg {ARG_END} b")) == Args(
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
    assert Args.parse(split(f"a {ARG_BEG} b {ARG_END} c")) == Args(
        task=Task(
            depends=[
                Task(name=TASK_COMPOSITE, cmd="a b"),
                Task(name=TASK_COMPOSITE, cmd="c"),
            ]
        ),
    )

    # attached
    assert Args.parse(split(f"a{ARG_BEG} b {ARG_END} c")) == Args(
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
    assert Args(parallel=True).as_argv() == ["ds", "--parallel"]
    assert Args(list_=True).as_argv() == ["ds", "--list"]
    assert Args(cwd=Path()).as_argv() == ["ds", "--cwd", str(Path())]
    assert Args(file=Path()).as_argv() == ["ds", "--file", str(Path())]

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
    ).as_argv() == ["ds", "'a b'", "c"]
