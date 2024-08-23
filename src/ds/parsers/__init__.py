"""Parsers for supported formats."""

# std
from __future__ import annotations
from fnmatch import fnmatch
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Tuple
from typing import Optional
import json
import logging
import sys
import dataclasses

# Coverage disabled to cover all python versions.
# TODO 2026-10-04 [3.10 EOL]: remove conditional
if sys.version_info >= (3, 11):  # pragma: no cover
    import tomllib as toml
else:  # pragma: no cover
    import tomli as toml

# pkg
from ..env import read_env
from ..searchers import get_key
from ..searchers import glob_apply
from ..searchers import glob_parents
from ..searchers import GlobMatches
from ..symbols import GLOB_EXCLUDE
from ..symbols import KEY_DELIMITER
from ..symbols import SHELL_CONTINUE
from ..symbols import starts
from ..symbols import TASK_COMPOSITE
from ..symbols import TASK_DISABLED
from ..symbols import TASK_KEEP_GOING
from ..tasks import Task
from ..tasks import Tasks

log = logging.getLogger(__name__)


Loader = Callable[[str], Dict[str, Any]]
"""A loader takes text and returns a mapping of strings to values."""

# NOTE: Used by cog in README.md
SEARCH_FILES = [
    "ds.toml",
    "pyproject.toml",  # python
    "package.json",  # node
    "Cargo.toml",  # rust
    "composer.json",  # php
    "[Mm]akefile",
    ".ds.toml",
]
"""Search order for configuration file names."""

# NOTE: Used by cog in README.md
SEARCH_KEYS_TASKS = [
    "scripts",  # ds.toml, .ds.toml, package.json, composer.json
    "tool.ds.scripts",  # pyproject.toml
    "tool.pdm.scripts",  # pyproject.toml
    "tool.rye.scripts",  # pyproject.toml
    "package.metadata.scripts",  # Cargo.toml
    "workspace.metadata.scripts",  # Cargo.toml
    "Makefile",  # Makefile
]
"""Search order for configuration keys."""

# NOTE: Used by cog in README.md
SEARCH_KEYS_WORKSPACE = [
    "workspace.members",  # ds.toml, .ds.toml, Cargo.toml
    "tool.ds.workspace.members",  # project.toml
    "tool.rye.workspace.members",  # pyproject.toml
    "tool.uv.workspace.members",  # pyproject.toml
    "workspaces",  # package.json
]
"""Search for workspace configuration keys."""


@dataclasses.dataclass
class Config:
    """ds configuration."""

    path: Path
    """Path to the configuration file."""

    config: Dict[str, Any]
    """Configuration data."""

    tasks: Tasks = dataclasses.field(default_factory=dict)
    """Task definitions."""

    members: GlobMatches = dataclasses.field(default_factory=dict)
    """Workspace members mapped to `True` for active members."""

    @staticmethod
    def find(start: Path, require_workspace: bool = False) -> Config:
        """Return the config file in `start` or its parents."""
        log.debug(f"require_workspace={require_workspace}")
        for _, check in glob_parents(start, {v: v for v in SEARCH_FILES}):
            try:
                return Config.load(check).parse(require_workspace)
            except LookupError:
                continue  # No valid sections.
        raise FileNotFoundError("No valid configuration file found.")

    @staticmethod
    def load(path: Path) -> Config:
        """Try to load a configuration file."""
        for pattern, loader in LOADERS.items():
            if fnmatch(path.name, pattern):
                return Config(path, loader(path.read_text()))
        raise LookupError(f"Not sure how to read file: {path}")

    def parse(self, require_workspace: bool = False) -> Config:
        """Parse a configuration file."""
        found, self.members = parse_workspace(self.path.parent, self.config)
        if require_workspace and not found:
            raise LookupError("Could not find workspace configuration.")

        found, self.tasks = parse_tasks(self.config, self.path)
        if not require_workspace and not found:
            raise LookupError("Could not find task configuration.")

        return self


def parse_workspace(
    path: Path, config: Dict[str, Any]
) -> Tuple[bool, Dict[Path, bool]]:
    """Parse workspace configurations."""
    found = False
    members: Dict[Path, bool] = {}
    key = ""
    patterns: List[str] = []
    for key in SEARCH_KEYS_WORKSPACE:
        patterns = get_key(config, key)
        if patterns is not None:
            found = True
            break
    if not found:
        return found, members

    members = glob_apply(path, patterns)

    # special case: Cargo.toml exclude patterns
    if KEY_DELIMITER in key:
        patterns = get_key(config, key.split(KEY_DELIMITER)[:-1] + ["exclude"])
        if patterns:  # remove all of these
            patterns = [f"{GLOB_EXCLUDE}{p}" for p in patterns]
            members = glob_apply(path, patterns, members)
    return found, members


def parse_tasks(
    config: Dict[str, Any], origin: Optional[Path] = None
) -> Tuple[bool, Tasks]:
    """Parse task configurations."""
    found = False
    tasks: Tasks = {}
    key, section = "", {}
    for key in SEARCH_KEYS_TASKS:
        section = get_key(config, key)
        if section is not None:
            found = True
            break

    if not found:
        return found, tasks

    assert isinstance(section, Dict)
    for name, cmd in section.items():
        name = str(name).strip()
        if not name or name.startswith(TASK_DISABLED):
            continue

        # special case: rye bare cmd as list
        if key == "tool.rye.scripts" and isinstance(cmd, list):
            cmd = {"cmd": cmd}

        task = parse_task(cmd, origin, key)
        task.name = name
        tasks[name] = task

    return found, tasks


def parse_task(config: Any, origin: Optional[Path] = None, key: str = "") -> Task:
    """Parse a config into a `Task`."""
    task = Task(origin=origin, origin_key=key)
    if isinstance(config, list):
        for item in config:
            parsed = parse_task(item, origin, key)
            parsed.name = TASK_COMPOSITE
            task.depends.append(parsed)

    elif isinstance(config, str):
        task.keep_going, task.cmd = starts(config, TASK_KEEP_GOING)

    elif isinstance(config, Dict):
        if "verbatim" in config:
            task.verbatim = config["verbatim"]
        if "help" in config:
            task.help = config["help"]

        if "keep_going" in config:
            task.keep_going = config["keep_going"]

        # Working directory
        if "cwd" in config:  # `working_dir` alias (ds)
            assert origin is not None
            task.cwd = origin.parent / config["cwd"]
        elif "working_dir" in config:  # `cwd` alias (pdm)
            assert origin is not None
            task.cwd = origin.parent / config["working_dir"]

        # Environment File
        if "env_file" in config:  # `env-file` alias (pdm)
            assert origin is not None
            task.env.update(read_env((origin.parent / config["env_file"]).read_text()))
        elif "env-file" in config:  # `env_file` alias (rye)
            assert origin is not None
            task.env.update(read_env((origin.parent / config["env-file"]).read_text()))

        # Environment Variables
        if "env" in config:
            assert isinstance(config["env"], dict)
            task.env.update(config["env"])

        found = False
        # Composite Task
        if "composite" in config:  # `chain` alias
            found = True
            assert isinstance(config["composite"], list)
            parsed = parse_task(config["composite"], origin, key)
            task.name = parsed.name
            task.cmd = parsed.cmd
            task.depends = parsed.depends
        elif "chain" in config:  # `composite` alias
            found = True
            assert isinstance(config["chain"], list)
            parsed = parse_task(config["chain"], origin, key)
            task.name = parsed.name
            task.cmd = parsed.cmd
            task.depends = parsed.depends

        # Basic Task
        if "shell" in config:
            found = True
            parsed = parse_task(str(config["shell"]), origin, key)
            task.cmd = parsed.cmd
            task.keep_going = parsed.keep_going
        elif "cmd" in config:
            found = True
            cmd = config["cmd"]
            parsed = parse_task(
                " ".join(cmd) if isinstance(cmd, list) else str(cmd),
                origin,
                key,
            )
            task.cmd = parsed.cmd
            task.keep_going = parsed.keep_going

        if not found:
            if "call" in config:
                raise ValueError(f"`call` commands not supported: {config}")
            raise TypeError(f"Unknown task type: {config}")
    else:
        raise TypeError(f"Unknown task type: {config}")
    return task


def makefile_loads(text: str, debug: bool = False) -> Dict[str, Dict[str, Any]]:
    """Load a `Makefile`."""
    # debug = True
    log.warning("EXPERIMENTAL: Trying to parse simplified Makefile format.")

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


LOADERS: Dict[str, Loader] = {
    "*.json": json.loads,
    "*.toml": toml.loads,
    "*[Mm]akefile": makefile_loads,
}
"""Mapping of file patterns to load functions."""
