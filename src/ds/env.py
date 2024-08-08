"""Shell environment variables."""

# std
from __future__ import annotations
from os import environ as ENV
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
import re

# pkg
from .symbols import ARG_PREFIX
from .symbols import ARG_REST

RE_ARGS = re.compile(r"(?:\$(@|\d+)|\$\{(@|\d+)(?::-(.*?))?\})")
"""Regex for matching an argument to be interpolated."""


def interpolate_args(cmd: str, args: List[str]) -> str:
    """Return `args` interpolated into `cmd`."""
    not_done: List[Optional[str]] = [arg for arg in args]

    # By default, we append all args to the end.
    if not RE_ARGS.search(cmd):
        cmd = f"{cmd} {ARG_PREFIX}{ARG_REST}"

    def _replace_arg(match: re.Match[str]) -> str:
        """Return the argument replacement."""
        arg = (match[1] or "") + (match[2] or "")
        if arg == ARG_REST:  # remaining args
            return " ".join(arg for arg in not_done if arg is not None)

        idx = int(arg) - 1
        default = match[3]
        if idx >= len(args):
            if default is None:
                raise IndexError(f"Not enough arguments provided: ${idx+1}")
            return default

        not_done[idx] = None
        return args[idx]

    return RE_ARGS.sub(_replace_arg, cmd).rstrip()


class TempEnv:
    """Temporary environment variables."""

    def __init__(self, **initial: Optional[str]):
        """Construct a temporary environment object.

        Args:
            **initial (str): initial environment variables to set

        Examples:
        >>> with TempEnv(foo="bar") as env1:
        ...     env1["foo"] == "bar"
        True
        >>> with TempEnv(a="b", c="d", x=None) as env1:
        ...     with TempEnv(a=None, c="e", f="g") as env2:
        ...         env2["a"] is None and env2["c"] == "e"
        True
        """
        self.saved: Dict[str, Optional[str]] = {}
        for key, value in initial.items():
            if value is None:
                del self[key]
            else:
                self[key] = value

    def __enter__(self) -> TempEnv:
        """Return self when entering a context."""
        return self

    def __exit__(self, *_: Any) -> None:
        """Reset all keys back to their previous values/existence."""
        for key, old in self.saved.items():
            if old is None:
                if key in ENV:
                    del ENV[key]
            else:
                ENV[key] = old

    def __iter__(self) -> Iterator[str]:
        """Return the iterator for ENV.

        >>> list(TempEnv()) != []
        True
        """
        return ENV.__iter__()

    def __len__(self) -> int:
        """Return len(ENV).

        >>> len(TempEnv()) > 0
        True
        """
        return len(ENV)

    def __contains__(self, key: str) -> bool:
        """Return True if the key is in ENV.

        >>> with TempEnv(a="b") as env1:
        ...     "a" in env1
        True
        """
        return key in ENV

    def __getitem__(self, key: str) -> Optional[str]:
        """Return the current value of `key` or `None` if it isn't set."""
        return ENV.get(key, None)

    def __setitem__(self, key: str, value: str) -> None:
        """Set the value of an environment variable.

        >>> with TempEnv(a="b") as env1:
        ...     env1["a"] = "c"
        """
        if key not in self.saved:
            self.saved[key] = ENV.get(key)
        ENV[key] = str(value)

    def __delitem__(self, key: str) -> None:
        """Delete an environment variable.

        >>> with TempEnv(a=None) as env1:
        ...     del env1["a"]
        """
        if key not in self.saved:
            self.saved[key] = ENV.get(key)
        if key in ENV:
            del ENV[key]
