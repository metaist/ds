"""Subset of Makefile parser."""

# std
from typing import Any
import logging

# pkg
from ..configs import Config
from . import ds_toml
from ..configs import Membership
from ..symbols import SHELL_CONTINUE
from ..symbols import starts
from ..tasks import Tasks

log = logging.getLogger(__name__)

NestedDict = dict[str, dict[str, Any]]
"""Generic mapping of a nested dict object."""


def _find_unquoted(line: str, char: str) -> int:
    """Find first occurrence of char outside quoted strings. Returns -1 if not found."""
    in_single = False
    in_double = False
    for i, c in enumerate(line):
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif c == char and not in_single and not in_double:
            return i
    return -1


def _strip_comment(line: str) -> str:
    """Strip comment from line, respecting quoted strings."""
    pos = _find_unquoted(line, "#")
    return line[:pos] if pos >= 0 else line


def _parse_key_val(line: str) -> tuple[str, str]:
    """Parse a key=value assignment from a line."""
    line = _strip_comment(line)
    if " = " in line:  # spaces around equals
        key, val = line.split(" = ", 1)
        return key, val
    if "=" in line:  # no spaces
        key, val = line.split("=", 1)
        return key, val
    return line, ""


def _expand_auto_vars(result: NestedDict) -> None:
    """Expand automatic variables in recipe commands.

    See: https://www.gnu.org/software/make/manual/make.html#Automatic-Variables

    Supported: $@, $<, $?, $^, $+
    Not supported: $*, $|, $(@D), $(@F), $(<D), $(<F), $(VAR), etc.
    """
    for name, rule in result.items():
        cmd = rule["shell"]
        deps = rule["composite"]

        cmd = cmd.replace("$@", name)  # target name
        if deps:
            cmd = cmd.replace("$<", deps[0])  # first prerequisite
        # prerequisites (NOTE: ds doesn't track "newer")
        cmd = cmd.replace("$?", " ".join(deps))
        # prerequisites, no duplicates
        cmd = cmd.replace("$^", " ".join(dict.fromkeys(deps)))
        # prerequisites, with duplicates
        cmd = cmd.replace("$+", " ".join(deps))
        rule["shell"] = cmd


def _parse_target_line(line: str, result: NestedDict) -> tuple[list[str], str]:
    """Parse a target definition line.

    Format: {target1} {target2} : {dep1} {dep2} ; {cmd1} # {help}

    Returns:
        Tuple of (target names, remaining prerequisites string)
    """
    value, rest = line.split(":", 1)
    targets = value.split()

    for target in targets:
        # Overwrite previous definition, if any.
        result[target] = {"composite": [], "shell": "", "verbatim": True}

    # NONSTANDARD: take comment on target line as description
    comment_pos = _find_unquoted(rest, "#")
    if comment_pos >= 0:
        help_text = rest[comment_pos + 1 :].strip()
        rest = rest[:comment_pos]
        for target in targets:
            result[target]["help"] = help_text

    # 5.1: "[...] the first recipe line may be attached to the
    # target-and-prerequisites line with a semicolon in between."
    semi_pos = _find_unquoted(rest, ";")
    if semi_pos >= 0:
        inline_cmd = rest[semi_pos + 1 :]
        rest = rest[:semi_pos]
        for target in targets:
            result[target]["shell"] += inline_cmd + "\n"

    # prerequisites
    for dep in rest.split():
        dep = dep.strip()
        if dep.startswith("-"):
            dep = f"+{dep[1:]}"
        for target in targets:
            result[target]["composite"].append(dep)

    return targets, rest


def parse_workspace(config: Config, key: str = "") -> Membership:
    """`Makefile` does not support workspaces."""
    raise NotImplementedError("`Makefile` does not support workspaces.")


def parse_tasks(config: Config, key: str = "recipes") -> Tasks:
    """Tasks are defined in `recipes`."""
    return ds_toml.parse_tasks(config, key)


def loads(text: str, debug: bool = False) -> NestedDict:
    """Load a `Makefile`."""
    log.warning(
        "EXPERIMENTAL: Parsing simplified `Makefile` format. "
        "Only automatic variables ($@, $<, $?, $^, $+) are supported. "
        "User-defined variables and pattern rules are not supported."
    )

    def _log(*args: Any, **kwargs: Any) -> None:
        """Print debug output if debug mode is enabled."""
        if debug:
            print(*args, **kwargs)

    result: NestedDict = {}
    prefix = "\t"
    n, lines = 0, text.split("\n")
    targets: list[str] = []
    in_recipe = False

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
            # around the backslash/newline is condensed into a single space.
            while lines and line.endswith(SHELL_CONTINUE[0]):  # merge next line
                n, next_line = n + 1, lines.pop(0)
                # whitespace is consolidated
                line = line[:-1].rstrip() + " " + next_line.lstrip()
                _log(f"{n:03}/{len(lines):03}", repr(line))

            if line.startswith(".PHONY"):  # we treat all targets as phony
                continue
            if line.startswith(".RECIPEPREFIX"):  # change prefix
                _, prefix = _parse_key_val(line)
                if not prefix:
                    prefix = "\t"
                if len(prefix) > 1:
                    prefix = prefix[0]
                _log(f"{n:03}|>>>", "prefix", repr(prefix))
                continue
            if ":" in line:  # start recipe
                in_recipe = True
                targets, _ = _parse_target_line(line, result)
                for target in targets:
                    _log(f"{n:03}|>>>", "start", target, result[target])

    _expand_auto_vars(result)
    return {"recipes": result}
