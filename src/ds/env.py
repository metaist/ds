"""Shell environment variables."""

# std
from __future__ import annotations
from os import environ as ENV
from os import get_terminal_size
from typing import Any
from typing import Iterator
from typing import Mapping
from typing import Match
import logging
import re

# pkg
from .symbols import ARG_PREFIX
from .symbols import ARG_REST
from .symbols import SHELL_BREAK
from .symbols import SHELL_CONTINUE
from .symbols import SHELL_TERMINATORS
from .symbols import starts
from .symbols import peek_end

log = logging.getLogger(__name__)

RE_ARGS = re.compile(r"(?:\$(@|\d+)|\$\{(@|\d+)(?::-(.*?))?\})")
"""Regex for matching an argument to be interpolated."""

RE_SHELL_METACHARS = re.compile(r"[;&|`$\\\"'<>(){}*?#!]")
"""Regex for detecting shell metacharacters in arguments."""

RE_EXPAND = re.compile(r"\$(\w+|\{[^}]*\})", re.ASCII)
"""Regex for finding variable expansions."""

RE_SPLIT = re.compile(
    r"""(
    (?<!\\)             # not preceded by backslash
    (?:
        (?:'[^']*')     # single quoted
        |(?:\"[^\"]*\") # double quoted
        |[\s;&]+        # one or more space, semicolon or ampersand
    ))""",
    flags=re.VERBOSE,
)
"""Regex for splitting commands."""

DEFAULT_WIDTH = 80
"""Default width for wrapping commands."""

MAX_WRAP_LENGTH = 10_000
"""Maximum command length to attempt wrapping (prevents ReDoS)."""

try:
    DEFAULT_WIDTH = min(100, max(80, get_terminal_size().columns - 2))
except OSError:
    DEFAULT_WIDTH = 80


def interpolate_args(cmd: str, args: list[str]) -> str:
    """Return `args` interpolated into `cmd`."""
    # Warn about shell metacharacters in arguments
    for arg in args:
        if RE_SHELL_METACHARS.search(arg):
            log.warning(
                f"Argument contains shell metacharacters: {arg!r}. "
                "This may have unintended effects."
            )
            break  # Only warn once per command

    not_done: list[str | None] = [arg for arg in args]

    # Replace `pdm`-style args.
    cmd = cmd.replace("{args}", "${@}")
    cmd = cmd.replace("{args:", "${@:-")

    # By default, we append all args to the end.
    if not RE_ARGS.search(cmd):
        cmd = f"{cmd} {ARG_PREFIX}{ARG_REST}"

    def _replace_arg(match: re.Match[str]) -> str:
        """Return the argument replacement."""
        arg = (match[1] or "") + (match[2] or "")
        default = match[3]
        if arg == ARG_REST:  # remaining args
            default = default or ""
            unused = [arg for arg in not_done if arg is not None]
            return " ".join(unused) if unused else default

        idx = int(arg) - 1
        if idx >= len(args):
            if default is None:
                raise IndexError(f"Not enough arguments provided: ${idx + 1}")
            return default

        not_done[idx] = None
        return args[idx]

    return RE_ARGS.sub(_replace_arg, cmd).rstrip()


class TempEnv:
    """Temporary environment variables."""

    def __init__(self, **initial: str | None):
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
        self.saved: dict[str, str | None] = {}
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

    def __getitem__(self, key: str) -> str | None:
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


def expand(value: str, store: Mapping[str, str] | None = None) -> str:
    """Expand variables of the form `$var` and `${var}`.

    Regular expansion works as expected:
    >>> with TempEnv(a='hello', b='world'):
    ...     expand("$a ${b}")
    'hello world'

    >>> expand("nothing")
    'nothing'

    Unknown variables are left unchanged:
    >>> with TempEnv(a='this'):
    ...     expand("$a is $b")
    'this is $b'
    """
    if "$" not in value:
        return value

    values = store or ENV

    def _repl(match: Match[str]) -> str:
        value = match.group(0)
        name = match.group(1)
        if name.startswith("{") and name.endswith("}"):
            name = name[1:-1]  # remove braces
        if name in values:  # can't use .get()
            value = values[name]
        return value

    return RE_EXPAND.sub(_repl, value)


def read_env(text: str) -> dict[str, str]:
    """Read an environment file.

    >>> read_env('''# IGNORE=line
    ... export INCLUDE=value
    ... 'key name'="value with space"
    ... ''')
    {'INCLUDE': 'value', 'key name': 'value with space'}
    """
    result: dict[str, str] = {}
    for line in text.replace("\r\n", "\n").split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue  # skip blank lines and comments

        _, line = starts(line, "export ")  # remove any export prefix
        if "=" not in line:
            log.warning(f"Skipping malformed line in env file (no '='): {line!r}")
            continue
        key, value = line.split("=", 1)

        key = key.strip()
        if len(key) >= 2 and key.startswith("'") and key.endswith("'"):
            key = key[1:-1]  # unquote key

        # expand with the current values and then all ENV values
        value = expand(value, result)
        value = expand(value)

        # warn about unresolved variables (e.g., self-referential FOO=$FOO)
        if "$" in value:
            unresolved = RE_EXPAND.findall(value)
            if unresolved:
                log.warning(
                    f"Unresolved variable(s) in {key!r}: {', '.join(unresolved)}. "
                    "Self-referential variables are not supported."
                )

        value = value.strip()
        if len(value) >= 2 and (
            (value.startswith("'") and value.endswith("'"))
            or (value.startswith('"') and value.endswith('"'))
        ):
            value = value[1:-1]  # unquote value
        result[key] = value
    return result


def wrap_cmd(cmd: str, width: int = DEFAULT_WIDTH) -> str:
    """Return a nicely wrapped command."""
    cmd = cmd.replace(SHELL_CONTINUE, "").strip()

    # Skip wrapping for very long commands (prevents potential ReDoS)
    if len(cmd) > MAX_WRAP_LENGTH:
        return cmd

    result: list[str] = []
    line: str = ""
    space: str = " " * 2
    item: str
    for item in RE_SPLIT.split(cmd):
        item = item.strip()
        if not item:
            continue

        check = f"{line} {item}" if line else item
        if item in [";", ";;"]:
            check = f"{line}{item}"

        if len(check) <= width - 4:
            line = check
            # Coverage incorrectly thinks this branch is not covered.
            # See: nedbatchelder.com/blog/202406/coverage_at_a_crossroads.html
            if peek_end(line, *SHELL_BREAK):  # pragma: no cover
                result.extend([line, "\n"])
                line = ""
            continue

        # How should we terminate this line?
        if peek_end(line, *SHELL_TERMINATORS):  # no continuation
            result.append(f"{line}\n")
        else:
            result.append(f"{line} {SHELL_CONTINUE}")

        # Indent next line?
        if space and not peek_end(line, *SHELL_TERMINATORS):
            line = f"{space}{item}"
        else:
            line = item  # next line

    if line:  # add last line
        result.append(line)

    return "".join(result).replace("\n", f"\n{space}").strip()
