# CLI Reference
<!--
[[[cog from cog_helpers import * ]]]
[[[end]]]
-->

<!--[[[cog fenced_block(snip_file("src/ds/args.py", beg="Usage:", end="Examples:")) ]]]-->

```text
Usage: ds [--help | --version] [--debug]
          [--dry-run]
          [--self-update]
          [--no-config]
          [--no-project]
          [--list]
          [--cwd PATH]
          [--file PATH]
          [--env-file PATH]
          [(--env NAME=VALUE)...]
          [--workspace GLOB]...
          [--pre][--post]
          [--parallel]
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
    https://docs.metaist.com/ds/getting-started/

  -l, --list
    List available tasks and exit.

  -t, --tree
    Show task dependency tree and exit.

  --output-format FORMAT
    Output format for --list and --tree (default: text).
    FORMAT is one of: text, json.

  --completion SHELL
    Output shell completion script and exit.
    SHELL is one of: bash, zsh, fish.

  --no-config
    Do not search for or load a configuration file. Supersedes `--file`.

  --no-project
    Do not search for project dependencies, e.g., `.venv`, `node_modules`

  --self-update
    Update `ds` (only for the Cosmopolitan build).

  -w GLOB, --workspace GLOB
    Patterns which indicate in which workspaces to run tasks.

    GLOB filters the list of workspaces defined in `--file`.
    The special pattern '*' matches all of the workspaces.

    Read more about configuring workspaces:
    https://docs.metaist.com/ds/workspaces/

  --pre, --post
    EXPERIMENTAL: Run tasks with pre- and post- names.

  --parallel
    EXPERIMENTAL: Run top-level tasks in parallel.

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
    https://docs.metaist.com/ds/tasks/#error-suppression

```

<!--[[[end]]]-->
