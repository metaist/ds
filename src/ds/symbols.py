"""Special symbols and their meanings."""

# std
from typing import Tuple

ARG_OPTION = "-"
"""Implicit start of task arguments."""

ARG_BEG = ":"
"""Explicit start of task arguments."""

ARG_END = "--"
"""Explicit end of task arguments."""

ARG_PREFIX = "$"
"""Prefix of an interpolated argument."""

ARG_REST = "@"
"""Interpolate remaining arguments."""

GLOB_ALL = "*"
"""Match all current values."""

GLOB_EXCLUDE = "!"
"""Prefix to exclude a glob match."""

GLOB_DELIMITER = ";"
"""Separator between globs."""

KEY_DELIMITER = "."
"""Separator between key parts."""

SHELL_CONTINUE = "\\\n"
"""Line continuation."""

SHELL_TERMINATORS = ";; && |& || ; & |".split()
"""No line continuation needed after these."""

SHELL_BREAK = "; &&".split()
"""Prefer line breaks after these."""

TASK_COMPOSITE = "#composite"
"""Composite task name."""

TASK_DISABLED = "#"
"""Prefix of a disabled task."""

TASK_KEEP_GOING = "+"
"""Prefix of an error-suppressed task."""


def starts(haystack: str, needle: str) -> Tuple[bool, str]:
    """Return whether `haystack` starts with `needle` and a stripped version.

    >>> starts("!foo", "!") == (True, "foo")
    True

    >>> starts("foo", "!") == (False, "foo")
    True
    """
    if haystack.startswith(needle):
        return True, haystack[len(needle) :]
    return False, haystack


def ends(haystack: str, needle: str) -> Tuple[bool, str]:
    """Return whether `haystack` ends with `needle` and a stripped version.

    >>> ends("foo", "oo") == (True, "f")
    True

    >>> ends("foo", "-") == (False, "foo")
    True
    """
    if haystack.endswith(needle):
        return True, haystack[: -len(needle)]
    return False, haystack


def peek_start(haystack: str, *needles: str) -> str:
    """Return the first `needle` starts `haystack`.

    >>> peek_start("abc", "a", "b", "c")
    'a'
    >>> peek_start("abc", "x")
    ''
    """
    for needle in needles:
        if haystack.startswith(needle):
            return needle
    return ""


def peek_end(haystack: str, *needles: str) -> str:
    """Return the first `needle` that ends `haystack`.

    >>> peek_end("abc", "a", "b", "c")
    'c'
    >>> peek_end("abc", "x")
    ''
    """
    for needle in needles:
        if haystack.endswith(needle):
            return needle
    return ""
