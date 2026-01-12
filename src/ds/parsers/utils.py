"""Shared parser utilities."""

# std
from typing import Any

# pkg
from ..configs import Config
from ..configs import Membership
from ..searchers import glob_paths
from ..symbols import GLOB_EXCLUDE

PYTHON_CALL = "python -c 'import sys; import {pkg} as _1; sys.exit(_1.{fn})'"
"""Template for Python call commands."""


def parse_workspace_globs(
    config: Config,
    data: dict[str, Any],
    members_key: str = "members",
    exclude_key: str | None = "exclude",
    allow_inline_excludes: bool = True,
    initial: Membership | None = None,
) -> Membership:
    """Parse workspace member globs from config data.

    Args:
        config: The configuration object
        data: Dict containing member patterns (e.g., {"members": ["pkg/*"]})
        members_key: Key for member patterns (default: "members")
        exclude_key: Key for exclude patterns (default: "exclude"), None to skip
        allow_inline_excludes: Whether members can have inline excludes like "!pkg/skip"
        initial: Initial membership dict to extend

    Returns:
        Membership dict mapping paths to inclusion status
    """
    members = initial if initial is not None else {}

    if members_key in data:
        members = glob_paths(
            config.path.parent,
            data[members_key],
            allow_all=False,
            allow_excludes=allow_inline_excludes,
            allow_new=True,
            previous=members,
        )

    if exclude_key and exclude_key in data:
        members = glob_paths(
            config.path.parent,
            [f"{GLOB_EXCLUDE}{p}" for p in data[exclude_key]],
            allow_all=False,
            allow_excludes=True,
            allow_new=False,
            previous=members,
        )

    return members


def python_call(call: str) -> str:
    """Return a formatted `call` string.

    See: https://rye.astral.sh/guide/pyproject/#call

    >>> python_call("http.server")
    'python -m http.server'

    >>> python_call("builtins:help") == PYTHON_CALL.format(pkg="builtins", fn="help()")
    True

    >>> python_call("builtins:print('Hello World!')") == PYTHON_CALL.format(
    ...     pkg="builtins", fn="print('Hello World!')")
    True
    """
    if ":" not in call:
        return f"python -m {call}"

    pkg, fn = call.split(":", 1)
    if not fn.endswith(")"):
        fn = f"{fn}()"
    return PYTHON_CALL.format(pkg=pkg, fn=fn)
