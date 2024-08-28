"""Subset of Makefile parser."""

# std
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
import logging

# pkg
from ..configs import Config
from . import ds_toml
from ..configs import Membership
from ..symbols import SHELL_CONTINUE
from ..symbols import starts
from ..tasks import Tasks

log = logging.getLogger(__name__)

NestedDict = Dict[str, Dict[str, Any]]
"""Generic mapping of a nested dict object."""


def parse_workspace(config: Config, key: str = "") -> Membership:
    """`Makefile` does not support workspaces."""
    raise NotImplementedError("`Makefile` does not support workspaces.")


def parse_tasks(config: Config, key: str = "recipes") -> Tasks:
    """Tasks are defined in `recipes`."""
    return ds_toml.parse_tasks(config, key)


def loads(text: str, debug: bool = False) -> NestedDict:
    """Load a `Makefile`."""
    # debug = True
    log.warning("EXPERIMENTAL: Parsing simplified `Makefile` format.")

    result: NestedDict = {}
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
    return {"recipes": result}
