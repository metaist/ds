"""Parse command-line arguments."""

# std
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from shlex import join
from typing import Dict
from typing import List
from typing import Optional
import dataclasses

# pkg
from .env import read_env
from .symbols import ARG_BEG
from .symbols import ARG_END
from .symbols import ARG_OPTION
from .tasks import parse_task
from .tasks import Task

# from .parsers import parse_task

# NOTE: Used by cog in README.md
USAGE = """ds: Run dev scripts.

Usage: ds [--help | --version] [--debug]
          [--dry-run]
          [--no-config]
          [--no-project]
          [--list]
          [--cwd PATH]
          [--file PATH]
          [--env-file PATH]
          [(--env NAME=VALUE)...]
          [--workspace GLOB]...
          [--pre][--post]
          [<task>...]

Options:
  -h, --help
    Show this message and exit.

  --version
    Show program version and exit.

  --debug
    Show debug messages.

  --cwd PATH
    Set the starting working directory (default: --file parent).
    PATH is resolved relative to the current working directory.

  --dry-run
    Show which tasks would be run, but don't actually run them.

  --env-file PATH
    File with environment variables. This file is read before --env
    values are applied.

  -e NAME=VALUE, --env NAME=VALUE
    Set one or more environment variables. Supersedes any values set in
    an `--env-file`.

  -f PATH, --file PATH
    File with task and workspace definitions (default: search in parents).

    Read more about the configuration file:
    https://github.com/metaist/ds

  -l, --list
    List available tasks and exit.

  --no-config
    Do not search for or load a configuration file. Supersedes `--file`.

  --no-project
    Do not search for project dependencies, e.g., `.venv`, `node_modules`

  -w GLOB, --workspace GLOB
    Patterns which indicate in which workspaces to run tasks.

    GLOB filters the list of workspaces defined in `--file`.
    The special pattern '*' matches all of the workspaces.

    Read more about configuring workspaces:
    https://github.com/metaist/ds#workspaces

  --pre, --post
    EXPERIMENTAL: Run tasks with pre- and post- names.

  <task>
    One or more tasks to run with task-specific arguments.

    The simplest way to pass arguments to tasks is to put them in quotes:

    $ ds 'echo "Hello world"'

    For more complex cases you can use a colon (`:`) to indicate start of arguments and double-dash (`--`) to indicate the end:

    $ ds echo: "Hello from" -- echo: "the world"

    If the first <option> starts with a hyphen (`-`), you may omit the
    colon (`:`). If there are no more tasks after the last option, you
    may omit the double-dash (`--`).

    Tasks are executed in order across any relevant workspaces. If any
    task returns a non-zero code, task execution stops unless the
    <task> was prefixed with a (`+`) in which case execution continues.

    Read more about error suppression:
    https://github.com/metaist/ds#error-suppression

Examples:
List the available tasks:
$ ds

Run one or more tasks:
$ ds build
$ ds clean build

If a task fails, subsequent tasks are not run unless errors are suppressed:
$ ds +lint test

will run `test` even if `lint` fails.

Provide arguments to one or more tasks (the following are equivalent):
$ ds clean --all -- build test --no-gpu
$ ds clean --all && ds build && ds test --no-gpu
"""


def _opt_prop(option: str) -> str:
    return option[2:].replace("-", "_")


@dataclass
class Args:
    """Type-checked arguments."""

    help: bool = False
    """Whether to show the usage."""

    version: bool = False
    """Whether to show the version."""

    debug: bool = False
    """Whether to show debug messages"""

    dry_run: bool = False
    """Whether to skip actually running tasks."""

    no_config: bool = False
    """Disable searching for config."""

    no_project: bool = False
    """Disable searching for project dependencies (`.venv`, `node_modules`)."""

    list_: bool = False
    """Whether to show available tasks"""

    cwd: Optional[Path] = None
    """Path to run tasks in."""

    env: Dict[str, str] = field(default_factory=dict)
    """Environment variable overrides."""

    env_file: Optional[Path] = None
    """Path to environment variables."""

    file: Optional[Path] = None
    """Path to task definitions."""

    workspace: List[str] = field(default_factory=list)
    """List of workspace patterns to run tasks in."""

    pre: bool = False
    """EXPERIMENTAL: Whether to run pre- tasks."""

    post: bool = False
    """EXPERIMENTAL: Whether to run post- tasks."""

    task: Task = field(default_factory=Task)
    """A composite task for the tasks given on the command-line."""

    def copy(self) -> Args:
        """Return a copy of this object."""
        return dataclasses.replace(self)

    def as_argv(self) -> List[str]:
        """Return args as a string."""
        result = ["ds"]

        # bool
        for option in [
            "--help",
            "--version",
            "--debug",
            "--dry-run",
            "--no-config",
            "--no-project",
            "--pre",
            "--post",
        ]:
            if getattr(self, _opt_prop(option)):
                result.append(option)
        if self.list_:
            result.append("--list")

        # path
        for option in ["--cwd", "--env-file", "--file"]:
            value = getattr(self, _opt_prop(option))
            if value:
                result.extend([option, str(value)])

        # workspace
        if self.workspace:
            for w in self.workspace:
                result.extend(["--workspace", w])

        # env
        for key, val in self.env.items():
            result.extend(["--env", f"'{key}={val}'"])

        # tasks
        for t in self.task.depends:
            parts = join([t.cmd, *t.args])
            result.append(parts)
        return result

    @staticmethod
    def parse(argv: List[str]) -> Args:
        """Parse command-line arguments in a docopt-like way."""
        args = Args()
        tasks: List[str] = []
        task = ""
        is_ours = True
        is_task = False
        while argv:
            arg = argv.pop(0)
            if is_ours:
                # bool
                if arg in [
                    "--help",
                    "--version",
                    "--debug",
                    "--dry-run",
                    "--no-config",
                    "--no-project",
                    "--pre",
                    "--post",
                ]:
                    attr = _opt_prop(arg)
                    setattr(args, attr, True)
                elif arg == "-h":
                    args.help = True
                elif arg in ["-l", "--list"]:
                    args.list_ = True

                # path
                elif arg in ["--cwd", "--env-file", "--file"]:
                    attr = _opt_prop(arg)
                    setattr(args, attr, Path(argv.pop(0)).resolve())
                elif arg == "-f":
                    args.file = Path(argv.pop(0)).resolve()

                # other
                elif arg in ["-e", "--env"]:
                    key, val = argv.pop(0).split("=")
                    args.env[key] = val
                elif arg in ["-w", "--workspace"]:
                    args.workspace.append(argv.pop(0))
                elif arg == "-w*":  # special shorthand
                    args.workspace.append("*")
                else:
                    is_ours = False

            if is_ours:
                continue  # processed
            # our args processed

            if task and arg == ARG_BEG:  # explicit arg start
                is_task = True
                continue  # not an argument

            if arg == ARG_END:  # explicit arg end
                task, is_task = "", False
                continue  # not an argument

            if task and arg.startswith(ARG_OPTION):  # implicit arg start
                is_task = True

            if is_task:  # append task args
                tasks[-1] += f" {arg}"
                continue  # processed

            if arg.endswith(ARG_BEG):  # task name + explicit arg start
                arg = arg[: -len(ARG_BEG)]
                is_task = True

            task = arg
            tasks.append(task)

        args.task = parse_task(tasks)
        args.task.cwd = args.cwd

        args.task.env = args.env
        args.task.env_file = args.env_file

        if not args.help and not args.version and not args.task.depends:
            # default action
            args.list_ = True

        # all args processed
        return args
