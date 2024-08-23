"""Parse and run tasks."""

# std
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field
from fnmatch import fnmatch
from os import environ as ENV
from os.path import relpath
from pathlib import Path
from shlex import join
from shlex import split
from subprocess import run
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
import json
import logging
import os
import sys

# Coverage disabled to cover all python versions.
# TODO 2026-10-04 [3.10 EOL]: remove conditional
if sys.version_info >= (3, 11):  # pragma: no cover
    import tomllib as toml
else:  # pragma: no cover
    import tomli as toml

# Coverage disabled to cover all python versions.
# TODO 2024-10-31 [3.8 EOL]: remove conditional
if sys.version_info >= (3, 9):  # pragma: no cover
    import graphlib
else:  # pragma: no cover
    import graphlib  # type: ignore

# pkg
from .env import interpolate_args
from .env import makefile_loads
from .env import read_env
from .env import TempEnv
from .env import wrap_cmd
from .symbols import GLOB_DELIMITER
from .symbols import GLOB_EXCLUDE
from .symbols import KEY_DELIMITER
from .symbols import starts
from .symbols import TASK_COMPOSITE
from .symbols import TASK_DISABLED
from .symbols import TASK_KEEP_GOING
from .searchers import get_key
from .searchers import GlobMatches
from .searchers import glob_names
from .searchers import glob_apply

log = logging.getLogger(__name__)

Tasks = Dict[str, "Task"]
"""Mapping of task names to `Task` objects."""

CycleError = graphlib.CycleError
"""Error thrown where there is a cycle in the tasks."""

ORIGINAL_CWD = Path.cwd()
"""Save a reference to the original working directory."""

Loader = Callable[[str], Dict[str, Any]]
"""A loader takes text and returns a mapping of strings to values."""

LOADERS: Dict[str, Loader] = {
    "*.json": json.loads,
    "*.toml": toml.loads,
    "*[Mm]akefile": makefile_loads,
}
"""Mapping of file patterns to load functions."""

# NOTE: Used by cog in README.md
SEARCH_FILES = [
    "ds.toml",
    ".ds.toml",
    "Cargo.toml",
    "composer.json",
    "package.json",
    "pyproject.toml",
    "Makefile",
    "makefile",
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


@dataclass
class Config:
    """ds configuration."""

    path: Path
    """Path to the configuration file."""

    config: Dict[str, Any]
    """Configuration data."""

    tasks: Tasks = field(default_factory=dict)
    """Task definitions."""

    members: GlobMatches = field(default_factory=dict)
    """Workspace members mapped to `True` for active members."""

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


@dataclass
class Task:
    """Represents a thing to be done."""

    origin: Optional[Path] = None
    """File from which this configuration came."""

    origin_key: str = ""
    """Key from which this task came."""

    name: str = ""
    """Task name."""

    help: str = ""
    """Task description."""

    verbatim: bool = False
    """Whether to format the command at all."""

    depends: List[Task] = field(default_factory=list)
    """Tasks to execute before this one."""

    cmd: str = ""
    """Shell command to execute after `depends`."""

    code: int = 0
    """Return code from running this task."""

    # NOTE: args, cwd, env, keep_going are overridable
    # via the CLI or when calling a composite command.

    args: List[str] = field(default_factory=list)
    """Additional arguments to `cmd`."""

    cwd: Optional[Path] = None
    """Task working directory."""

    env: Dict[str, str] = field(default_factory=dict)
    """Task environment variables."""

    _env: Dict[str, str] = field(default_factory=dict)
    """Hidden environment variables."""

    keep_going: bool = False
    """Ignore a non-zero return code."""

    @staticmethod
    def parse(config: Any, origin: Optional[Path] = None, key: str = "") -> Task:
        """Parse a config into a `Task`."""
        task = Task(origin=origin, origin_key=key)
        if isinstance(config, list):
            for item in config:
                parsed = Task.parse(item, origin, key)
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
                task.env.update(
                    read_env((origin.parent / config["env_file"]).read_text())
                )
            elif "env-file" in config:  # `env_file` alias (rye)
                assert origin is not None
                task.env.update(
                    read_env((origin.parent / config["env-file"]).read_text())
                )

            # Environment Variables
            if "env" in config:
                assert isinstance(config["env"], dict)
                task.env.update(config["env"])

            found = False
            # Composite Task
            if "composite" in config:  # `chain` alias
                found = True
                assert isinstance(config["composite"], list)
                parsed = Task.parse(config["composite"], origin, key)
                task.name = parsed.name
                task.cmd = parsed.cmd
                task.depends = parsed.depends
            elif "chain" in config:  # `composite` alias
                found = True
                assert isinstance(config["chain"], list)
                parsed = Task.parse(config["chain"], origin, key)
                task.name = parsed.name
                task.cmd = parsed.cmd
                task.depends = parsed.depends

            # Basic Task
            if "shell" in config:
                found = True
                parsed = Task.parse(str(config["shell"]), origin, key)
                task.cmd = parsed.cmd
                task.keep_going = parsed.keep_going
            elif "cmd" in config:
                found = True
                cmd = config["cmd"]
                parsed = Task.parse(
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

    def pprint(self) -> None:
        """Pretty-print a representation of this task."""
        if self.help:
            print("#", self.help)
        print(">", wrap_cmd(self.as_args()))
        if self.depends:
            print(
                [
                    f"{TASK_KEEP_GOING if t.keep_going else ''}{t.cmd}"
                    for t in self.depends
                ]
            )
        if self.cmd:
            if self.verbatim:
                print("$", self.cmd.strip().replace("\n", "\n$ "))
            else:
                print(f"$ {wrap_cmd(self.cmd)}")
        print()

    def as_args(
        self,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        keep_going: bool = False,
    ) -> str:
        """Return a shell representation of running this task."""
        args = ["ds"]
        if cwd or self.cwd:
            args.extend(["--cwd", str(cwd or self.cwd)])
        for key, val in (env or self.env or {}).items():
            args.extend(["-e", f"{key}={val}"])

        prefix = ""
        if keep_going or self.keep_going:
            prefix = TASK_KEEP_GOING
        if self.name == TASK_COMPOSITE:
            args.append(f"{prefix}{self.cmd}")
        elif self.name:
            args.append(f"{prefix}{self.name}")
        return join(args)

    def run(
        self,
        tasks: Tasks,
        extra: Optional[List[str]] = None,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        keep_going: bool = False,
        dry_run: bool = False,
    ) -> int:
        """Run this task."""
        extra = extra or []
        cwd = cwd or self.cwd
        env = env or self.env
        keep_going = keep_going or self.keep_going

        # 1. Run all the dependencies.
        for dep in self.depends:
            dep.run(tasks, extra, cwd, env, keep_going, dry_run)

        # 2. Check if we have anything to do.
        if not self.cmd.strip():  # nothing to do
            return 0

        # 3. Check if a part of a composite task is calling another task.
        if self.name == TASK_COMPOSITE:
            cmd, *args = split(self.cmd)
            others = glob_names(tasks.keys(), cmd.split(GLOB_DELIMITER))
            ran, code = False, 0
            for other_name in others:
                other = tasks.get(other_name)
                if other and other != self and self not in other.depends:
                    ran = True
                    code = other.run(tasks, args + extra, cwd, env, keep_going, dry_run)
            if ran:
                return code

        # 4. Run in the shell.
        cmd = interpolate_args(self.cmd, extra)
        with proxy_cmd(self, cwd or Path(), cmd) as cmd:
            dry_prefix = "[DRY RUN]\n" if dry_run else ""
            print(f"\n{dry_prefix}>", wrap_cmd(self.as_args(cwd, env, keep_going)))
            if self.verbatim:
                print("$", cmd.strip().replace("\n", "\n$ "))
            else:
                print(f"$ {wrap_cmd(cmd)}")
            if dry_run:  # do not actually run the command
                return 0

            combined_env = {**ENV, **env}
            proc = run(
                cmd,
                shell=True,
                text=True,
                cwd=cwd,
                env=combined_env,
                executable=combined_env.get("SHELL"),
            )

        code = proc.returncode
        if code != 0 and not keep_going:
            log.error(f"return code = {code}")
            sys.exit(code)
        return 0  # either it was zero or we keep going


@contextmanager
def proxy_cmd(task: Task, cwd: Path, cmd: str) -> Iterator[str]:
    """Change conditions for a command."""
    # node: add ./node_modules/bin to PATH
    node_modules = Path("node_modules") / ".bin"
    checks = [node_modules]
    if task.origin:
        checks.append(task.origin / node_modules)

    node_bin = Path(".") / "node_modules" / ".bin"
    if cwd and not node_bin.exists():
        node_bin = cwd / "node_modules" / ".bin"

    if node_bin.exists():
        prev_path = ENV.get("PATH", "")
        next_path = f"{node_bin}{os.pathsep if prev_path else ''}{prev_path}"
        with TempEnv(PATH=next_path):
            yield cmd
        return

    # default: return command unchanged
    yield cmd


def check_cycles(tasks: Tasks) -> List[str]:
    """Raise a `CycleError` if there is a cycle in the task graph."""
    graph = {}
    for name, task in tasks.items():
        edges = set()
        for dep in task.depends:
            other = split(dep.cmd)[0]
            if other != name:
                edges.add(other)
        graph[name] = edges
    return list(graphlib.TopologicalSorter(graph).static_order())


def print_tasks(path: Path, tasks: Tasks) -> None:
    """Pretty print task names."""
    count = len(tasks)
    plural = "s" if count != 1 else ""

    path_abs = str(path.resolve())
    path_rel = relpath(path, ORIGINAL_CWD)
    location = path_abs if len(path_abs) < len(path_rel) else path_rel

    print(f"# Found {count} task{plural} in {location}\n")
    for task in tasks.values():
        task.pprint()


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

        task = Task.parse(cmd, origin, key)
        task.name = name
        tasks[name] = task

    return found, tasks


def find_config(
    start: Path, require_workspace: bool = False, debug: bool = False
) -> Config:
    """Return the config file in `start` or its parents."""
    log.debug(f"require_workspace={require_workspace}")
    for path in (start / "x").resolve().parents:  # to include start
        for name in SEARCH_FILES:
            check = path / name
            log.debug(f"check {check.resolve()}")
            if not check.exists():
                continue
            try:
                return Config.load(check).parse(require_workspace)
            except LookupError:
                continue  # No valid sections.
    raise FileNotFoundError("No valid configuration file found.")
