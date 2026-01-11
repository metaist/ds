"""Shared parser utilities."""

PYTHON_CALL = "python -c 'import sys; import {pkg} as _1; sys.exit(_1.{fn})'"
"""Template for Python call commands."""


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
