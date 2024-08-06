"""Test parsing args."""

# std
import shlex

# pkg
from ds.args import Args
from ds.args import parse_args
from ds.tasks import COMPOSITE_NAME
from ds.tasks import Task


def test_parse_args() -> None:
    """Parse arguments."""
    assert parse_args(shlex.split("--debug")) == Args(debug=True)

    # no args
    assert parse_args(shlex.split("a b c")) == Args(
        task=Task(
            depends=[
                Task(name=COMPOSITE_NAME, cmd="a", allow_shell=False),
                Task(name=COMPOSITE_NAME, cmd="b", allow_shell=False),
                Task(name=COMPOSITE_NAME, cmd="c", allow_shell=False),
            ]
        )
    )


def test_implicit_arg_start() -> None:
    """Test parsing implicit task arg start / explicit end."""
    assert parse_args(shlex.split("--debug a --debug -- b")) == Args(
        debug=True,
        task=Task(
            depends=[
                Task(name=COMPOSITE_NAME, cmd="a --debug", allow_shell=False),
                Task(name=COMPOSITE_NAME, cmd="b", allow_shell=False),
            ]
        ),
    )


def test_explicit_arg_start_end() -> None:
    """Test parsing explicit task args."""
    # separate
    assert parse_args(shlex.split("a : b -- c")) == Args(
        task=Task(
            depends=[
                Task(name=COMPOSITE_NAME, cmd="a b", allow_shell=False),
                Task(name=COMPOSITE_NAME, cmd="c", allow_shell=False),
            ]
        ),
    )

    # attached
    assert parse_args(shlex.split("a: b -- c")) == Args(
        task=Task(
            depends=[
                Task(name=COMPOSITE_NAME, cmd="a b", allow_shell=False),
                Task(name=COMPOSITE_NAME, cmd="c", allow_shell=False),
            ]
        ),
    )
