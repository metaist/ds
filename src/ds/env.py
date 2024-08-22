"""Shell environment variables."""

# std
from __future__ import annotations
from os import environ as ENV
from os import get_terminal_size
from typing import Any
from typing import Dict
from typing import Iterator
from typing import Tuple
from typing import List
from typing import Mapping
from typing import Match
from typing import Optional
import re

# pkg
from .symbols import ARG_PREFIX
from .symbols import ARG_REST
from .symbols import SHELL_BREAK
from .symbols import SHELL_CONTINUE
from .symbols import SHELL_TERMINATORS
from .symbols import starts
from .symbols import peek_end

RE_ARGS = re.compile(r"(?:\$(@|\d+)|\$\{(@|\d+)(?::-(.*?))?\})")
"""Regex for matching an argument to be interpolated."""

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
"""Default width for warping commands."""

try:
    DEFAULT_WIDTH = min(100, max(80, get_terminal_size().columns - 2))
except OSError:
    DEFAULT_WIDTH = 80


def interpolate_args(cmd: str, args: List[str]) -> str:
    """Return `args` interpolated into `cmd`."""
    not_done: List[Optional[str]] = [arg for arg in args]

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


def expand(value: str, store: Optional[Mapping[str, str]] = None) -> str:
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


def read_env(text: str) -> Dict[str, str]:
    """Read an environment file.

    >>> read_env('''# IGNORE=line
    ... export INCLUDE=value
    ... 'key name'="value with space"
    ... ''')
    {'INCLUDE': 'value', 'key name': 'value with space'}
    """
    result: Dict[str, str] = {}
    for line in text.replace("\r\n", "\n").split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue  # skip blank lines and comments

        _, line = starts(line, "export ")  # remove any export prefix
        key, value = line.split("=", 1)

        key = key.strip()
        if len(key) >= 2 and key.startswith("'") and key.endswith("'"):
            key = key[1:-1]  # unquote key

        # expand with the current values and then all ENV values
        value = expand(value, result)
        value = expand(value)

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
    result = []
    line = ""
    space = " " * 2
    for item in RE_SPLIT.split(cmd.replace(SHELL_CONTINUE, "").strip()):
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


def makefile_loads(text: str, debug: bool = False) -> Dict[str, Dict[str, Any]]:
    """Load a `Makefile`."""
    # debug = True
    print("WARNING: Makefile support is experimental.")

    result: Dict[str, Dict[str, Any]] = {}
    prefix = "\t"
    n, lines = 0, text.split("\n")
    targets: List[str] = []
    in_recipe = False

    def _log(*args: Any, **kwargs: Any) -> None:
        if debug:
            print(*args, **kwargs)

    def _strip_comment(line: str) -> str:
        if "#" in line:
            line = line[: line.index("#")]
        return line

    def _key_val(line: str) -> Tuple[str, str]:
        key, val = "", ""
        line = _strip_comment(line)
        if " = " in line:  # spaces around equals
            key, val = line.split(" = ", 1)
        elif "=" in line:  # no spaces
            key, val = line.split("=", 1)
        else:
            key, val = line, ""
        return key, val

    while lines:
        n, line = n + 1, lines.pop(0)
        _log(f"{n:03}/{len(lines):03}", repr(line))

        # 5.1: "Blank lines and lines of just comments may appear among the
        # recipe lines; they are ignored. [...] A comment in a recipe is not
        # a `make` comment; it will be passed to the shell as-is."
        if in_recipe:
            has_prefix, line = starts(line, prefix)
            if not has_prefix:  # end of recipe
                for target in targets:
                    _log(f"{n:03}|>>>", "end", target, result[target])
                targets, in_recipe = [], False
            else:
                # https://www.gnu.org/software/make/manual/make.html#Splitting-Recipe-Lines
                # 5.1.1: "[...] backslash/newline pairs are not removed from the
                # recipe. Both the backslash and the newline characters are
                # preserved and passed to the shell."
                while lines and line.endswith(SHELL_CONTINUE[0]):  # merge next line
                    n, next_line = n + 1, lines.pop(0)
                    _, next_line = starts(next_line, prefix)  # remove prefix
                    # continuation and new line are preserved
                    line = line + "\n" + next_line
                    _log(f"{n:03}/{len(lines):03}", repr(line))

                # handle error suppression
                if line.startswith("-"):
                    line = line[1:]
                    for target in targets:
                        result[target]["keep_going"] = True
                # put the newline back
                for target in targets:
                    result[target]["shell"] += line + "\n"

        if not in_recipe:
            if not line or line.startswith("#"):
                continue

            # https://www.gnu.org/software/make/manual/make.html#Splitting-Lines
            # 3.1.1: Outside of recipe lines, backslash/newlines are converted
            # into a single space character. Once that is done, all whitespace
            # around the backslash/newline is condensed into a single space:
            # this includes all whitespace preceding the backslash, all
            # whitespace at the beginning of the line after the
            # backslash/newline, and any consecutive backslash/newline
            # combinations."
            while lines and line.endswith(SHELL_CONTINUE[0]):  # merge next line
                n, next_line = n + 1, lines.pop(0)
                # whitespace is consolidated
                line = line[:-1].rstrip() + " " + next_line.lstrip()
                _log(f"{n:03}/{len(lines):03}", repr(line))

            if line.startswith(".PHONY"):  # we treat all targets as phony
                continue
            if line.startswith(".RECIPEPREFIX"):  # change prefix
                _, prefix = _key_val(line)
                if not prefix:
                    prefix = "\t"
                if len(prefix) > 1:
                    prefix = prefix[0]
                _log(f"{n:03}|>>>", "prefix", repr(prefix))
                continue
            if ":" in line:  # start recipe
                # {target1} {target2} : {dep1} {dep2} ; {cmd1} # {help}
                in_recipe = True
                value, rest = line.split(":", 1)
                targets = value.split()
                for target in targets:
                    # Overwrite previous definition, if any.
                    result[target] = {"composite": [], "shell": "", "verbatim": True}

                # NONSTANDARD: take comment on target line as description
                if "#" in rest:
                    rest, value = rest.split("#", 1)
                    for target in targets:
                        result[target]["help"] = value.strip()

                # 5.1: "[...] the first recipe line may be attached to the
                # target-and-prerequisites line with a semicolon in between."
                if ";" in rest:
                    rest, value = rest.split(";", 1)
                    for target in targets:
                        result[target]["shell"] += value + "\n"

                # prerequisites
                for d in rest.split():
                    d = d.strip()
                    if d.startswith("-"):
                        d = f"+{d[1:]}"
                    for target in targets:
                        result[target]["composite"].append(d)

                for target in targets:
                    _log(f"{n:03}|>>>", "start", target, result[target])

    # https://www.gnu.org/software/make/manual/make.html#Automatic-Variables
    for name, rule in result.items():
        cmd = rule["shell"]
        deps = rule["composite"]

        cmd = cmd.replace("$@", name)  # name of the rule
        if deps:
            cmd = cmd.replace("$<", deps[0])  # first prerequisite
        cmd = cmd.replace("$?", " ".join(deps))  # all "newer" prerequisites
        cmd = cmd.replace("$^", " ".join(set(deps)))  # all prerequisites
        rule["shell"] = cmd

    # print(result)
    return {"Makefile": result}
