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

KEY_DELIMITER = "."
"""Separator between key parts."""

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
