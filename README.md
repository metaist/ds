# ds: run dev scripts

<!--
[[[cog from cog_helpers import * ]]]
[[[end]]]
-->
<p align="center">
  <a href="https://github.com/metaist/ds/actions/workflows/ci.yaml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/metaist/ds/.github/workflows/ci.yaml?branch=main&logo=github"/></a>
  <a href="https://pypi.org/project/ds-run"><img alt="PyPI" src="https://img.shields.io/pypi/v/ds-run.svg?color=blue" /></a>
  <a href="https://pypi.org/project/ds-run"><img alt="Supported Python Versions" src="https://img.shields.io/pypi/pyversions/ds-run" /></a>
</p>

Dev scripts are the short names we give to common tasks and long commands in a software project. `ds` finds and runs dev scripts in your project's configuration file (e.g., `Cargo.toml`, `package.json`, `pyproject.toml`, etc.):

```bash
pip install ds-run  # or: uv tool install ds-run
ds --list           # list the tasks
ds clean lint test  # run multiple tasks
ds format:*         # run tasks that match a glob
ds test -vv         # pass arguments to tasks
ds -e PORT=8080 run # set environment variables
ds +cspell test     # suppress errors
ds -w* build        # supports monorepo/workspaces
```

Read more:

- [Installing `ds`](#install)
- [Example configuration files][example-tasks]
- [When should I make a dev script?](#when-should-i-make-a-dev-script)
- [Where should I put my config?](#where-should-i-put-my-config)
- [How does `ds` find my config?](#how-does-ds-find-my-config)
- [Where do tasks run?](#where-do-tasks-run)

## Example

Suppose you want to use `pytest` with `coverage` to run unit tests, doctests, and to generate a branch-level coverage report:

```bash
coverage run --branch --source=src -m \
  pytest \
    --doctest-modules \
    --doctest-ignore-import-errors \
    src test;
coverage report -m
```

Instead of typing that, we just add a script to our `pyproject.toml` file:

```toml
[tool.ds.scripts]
test = """
  coverage run --branch --source=src -m \
    pytest \
      --doctest-modules \
      --doctest-ignore-import-errors \
      src test;
  coverage report -m
"""
```

And now you can run it with a quick shorthand:

```bash
ds test
```

## Benefits

♻️ **Works with existing projects**<br />
[Almost](#limitations) a drop-in replacement for:

- **Node** (`package.json`): [`npm run`][npm run], [`yarn run`][yarn run], [`pnpm run`][pnpm run], [`bun run`][bun run]
- **Python** (`pyproject.toml`): [`pdm run`][pdm run], [`rye run`][rye run]
- **PHP** (`composer.json`): [`composer run-script`][composer run-script]
- **Rust** (`Cargo.toml`): [`cargo run-script`][cargo run-script]

**Experimental**: We also support an extremely small subset of the [`Makefile`](./Makefile) format (see [#68]).

See: [Inspirations](#inspirations)

🗂️ **Add monorepo/workspace support anywhere**<br />
Easily [manage monorepos and sub-projects](#workspaces), even if they use different tooling.

🏃 **Run multiple tasks with custom arguments for each task**<br />
Provide [command-line arguments](#command-line-arguments) for multiple tasks as well as simple [argument interpolation](#argument-interpolation).

🪄 **Minimal magic**<br/>
Tries to use familiar syntax and a few clear rules. Checks for basic cycles and raises helpful error messages if things go wrong.

🚀 **Minimal dependencies**<br />
Currently working on removing all of these (see [#46]):

- python (3.8+)
- `tomli` (for python < 3.11)
- `graphlib_backport` (for python < 3.9)

## Limitations

`ds` **does not** strive to be an all-in-one tool for every project and is not a replacement for package management tools or `make`. Here are some things that are not supported or not yet implemented.

- Not Supported: [Lifecycle Events](#not-supported-lifecycle-events)
- Not Supported: [`call` Tasks](#not-supported-call-tasks)
- Partial Support: [`Makefile` format][#68] (see [#68])
- In Progress: [Shell Completions][#44] (see [#44])
- In Progress: [Remove Python Dependency][#46] (see [#46])

## Install

`ds` is typically installed at the system-level to make it available across all your projects.

```bash
python -m pip install ds-run

# or, if you use uv:
uv tool install ds-run
```

If you just want to try `ds`:

```bash
uvx --from ds-run ds --version
# or
pipx run ds-run --version
```

## Usage

<!--[[[cog fenced_block(snip_file("src/ds/args.py", beg="Usage:", end="Examples:")) ]]]-->

```text
Usage: ds [--help | --version] [--debug]
          [--dry-run]
          [--list]
          [--cwd PATH]
          [--file PATH]
          [--env-file PATH]
          [(--env NAME=VALUE)...]
          [--workspace GLOB]...
          [<task>[: <options>... --]...]

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

  -w GLOB, --workspace GLOB
    Patterns which indicate in which workspaces to run tasks.

    GLOB filters the list of workspaces defined in `--file`.
    The special pattern '*' matches all of the workspaces.

    Read more about configuring workspaces:
    https://github.com/metaist/ds#workspaces

  <task>[: <options>... --]
    One or more tasks to run with task-specific arguments.

    Use a colon (`:`) to indicate start of arguments and
    double-dash (`--`) to indicate the end.

    If the first <option> starts with a hyphen (`-`), you may omit the
    colon (`:`). If there are no more tasks after the last option, you
    may omit the double-dash (`--`).

    Tasks are executed in order across any relevant workspaces. If any
    task returns a non-zero code, task execution stops unless the
    <task> was prefixed with a (`+`) in which case execution continues.

    Read more about error suppression:
    https://github.com/metaist/ds#error-suppression

```

<!--[[[end]]]-->

## When should I make a dev script?

Typically, you should make a dev script for important steps in your development process. For example, most projects will need a way to run linters and unit tests (see the [`test` example above](#example)). Some projects also need a way to start up a server, fetch configuration files, or clean up generated files.

Dev scripts act as another form of documentation that helps developers understand how to build and work on your project.

## Where should I put my config?

`ds` supports `.json` and `.toml` configuration files (see [examples][example-tasks]) which typically go in the top-level of your project. To avoid making lots of top-level files, `ds` can use common project configuration files.

- **Node**: `package.json` under `scripts`
- **PHP**: `composer.json` under `scripts`
- **Python**: `pyproject.toml` under `[tool.ds.scripts]` (`[tool.pdm.scripts]` and `[tool.rye.scripts]` also supported)
- **Rust**: `Cargo.toml` under `[package.metadata.scripts]` or `[workspace.metadata.scripts]`
- **Other**: `ds.toml` under `[scripts]`

**Experimental**: We support an extremely small subset of the [`Makefile`](./Makefile) format (see [#68]).

Read more:

- [Example configuration files][example-tasks]
- [Workspaces](#workspaces)

## How does `ds` find my config?

If you don't provide a config file using the `--file` option, `ds` will search the current directory and all of its parents for files with these names in the following order:

<!--[[[cog
from ds.configs import SEARCH_FILES
cog.outl()
for key in SEARCH_FILES:
    cog.outl(f"- `{key}`")
cog.outl()
]]] -->

- `ds.toml`
- `.ds.toml`
- `Cargo.toml`
- `composer.json`
- `package.json`
- `pyproject.toml`
- `Makefile`
- `makefile`

<!--[[[end]]]-->

If you provide one or more `--workspace` options, the file must contain a [workspace key](#workspaces). Otherwise, then the file must contain a [task key](#task-keys).

If the appropriate key cannot be found, searching continues up the directory tree. The first file that has the appropriate key is used.

One exception to the search process is when using the `--workspace` option: If a workspace member contains a file with the same name as the configuration file, that file is used _within_ the workspace (e.g., a workspace defined in `Cargo.toml` will try to find a `Cargo.toml` in each workspace). Otherwise, the usual search process is used.

## Where do tasks run?

Typically, tasks run in the same directory as the configuration file.

If you provide a `--cwd` option (but not a `--workspace` option), tasks will run in the directory provided by the `--cwd` option.

If you provide one or more `--workspace` options, `--cwd` is ignored and tasks are run in each of the selected workspace members.

**NOTE**: In configuration files, you can use the `cwd` or `working_dir` option to specify a working directory for a _specific_ task and that option will be respected even when using `--workspace` or `--cwd` from the command line.

## Task Keys

`ds` searches configuration files for the following keys, in the following order, to find task definitions. The first key that's found is used and should contain a mapping from [task names](#task-names) to [basic tasks](#basic-task) or [composite tasks](#composite-task).

<!--[[[cog
from ds.configs import SEARCH_KEYS_TASKS
cog.outl()
for key in SEARCH_KEYS_TASKS:
    cog.outl(f"- `{key}`")
cog.outl()
]]]-->

- `scripts`
- `tool.ds.scripts`
- `tool.pdm.scripts`
- `tool.rye.scripts`
- `package.metadata.scripts`
- `workspace.metadata.scripts`
- `Makefile`

<!--[[[end]]]-->

## Task Names

- Task names are strings, that are usually short, lowercase, ASCII letters.
- They can have a colon (`:`) in them, like `py:build`.
- All leading and trailing whitespace in a task name is trimmed.
- If the name is empty or starts with a hash (`#`) it is ignored. This allows formats like `package.json` to "comment out" tasks.
- Don't start a name with a plus (`+`) because that indicates [error suppression](#error-suppression).
- Don't start a name with a hyphen (`-`) because that can make the task look like a [command-line argument](#command-line-arguments).
- Don't end a task name with a colon (`:`) because we use that to pass [command-line arguments](#command-line-arguments)

## Basic Task

A basic task is just a string of what should be executed in a shell using `subprocess.run`.

- Supports most [`pdm`-style][pdm] and [`rye`-style][rye] commands ([except `call`](#not-supported-call-tasks))
- Supports [argument interpolation](#argument-interpolation)
- Supports [error suppression](#error-suppression)

<!--[[[cog insert_file("examples/readme/basic.toml")]]]-->

```toml
# Example: Basic tasks become strings.

[scripts]
ls = "ls -lah"
no_error = "+exit 1" # See "Error Suppression"

# We also support `pdm`-style and `rye`-style commands.
# The following are all equivalent to `ls` above.
ls2 = { cmd = "ls -lah" }
ls3 = { cmd = ["ls", "-lah"] }
ls4 = { shell = "ls -lah" }
```

<!--[[[end]]]-->

## Composite Task

A composite task consists of a series of steps where each step is the name of another task or a shell command.

- Supports [`pdm`-style][pdm] `composite` and [`rye`-style][rye] `chain`
- Supports [argument interpolation](#argument-interpolation)
- Supports [error suppression](#error-suppression)

<!--[[[cog insert_file("examples/readme/composite.toml")]]]-->

```toml
# Example: Composite tasks call other tasks or shell commands.

[scripts]
build = "touch build/$1"
clean = "rm -rf build"

# We also support `pdm`-style and `rye`-style composite commands.
# The following are all equivalent.
all = ["clean", "+mkdir build", "build foo", "build bar", "echo 'Done'"]

pdm-style = { composite = [
  "clean",
  "+mkdir build", # See: Error Suppression
  "build foo",
  "build bar",
  "echo 'Done'", # Composite tasks can call shell commands.
] }

rye-style = { chain = [
  "clean",
  "+mkdir build", # See: Error Suppression
  "build foo",
  "build bar",
  "echo 'Done'", # Composite tasks can call shell commands.
] }
```

<!--[[[end]]]-->

## Argument Interpolation

Tasks can include parameters like `$1` and `$2` to indicate that the task accepts arguments.

You can also use `$@` for the "remaining" arguments (i.e. those you haven't yet interpolated yet).

You can also specify a default value for any argument using a `bash`-like syntax: `${1:-default value}`.

Arguments from a [composite task](#composite-task) precede those [from the command-line](#command-line-arguments).

<!--[[[cog insert_file("examples/readme/argument-interpolation.toml")]]]-->

```toml
# Example: Argument interpolation lets you pass arguments to tasks.

[scripts]
# pass arguments, but supply defaults
test = "pytest ${@:-src test}"

# interpolate the first argument (required)
# and then interpolate the remaining arguments, if any
lint = "ruff check $1 ${@:-}"

# we also support the pdm-style {args} placeholder
test2 = "pytest {args:src test}"
lint2 = "ruff check {args}"

# pass an argument and re-use it
release = """\
  git commit -am "release: $1";\
  git tag $1;\
  git push;\
  git push --tags;\
  git checkout main;\
  git merge --no-ff --no-edit prod;\
  git push
"""
```

<!--[[[end]]]-->

### Command-line Arguments

When calling `ds` you can specify additional arguments to pass to commands.

```bash
ds build: foo -- build: bar
```

This would run the `build` task first with the argument `foo` and next with the argument `bar`.

A few things to note:

- the colon (`:`) after the task name indicates the start of arguments
- the double dash (`--`) indicates the end of arguments

If the first argument to the task starts with a hyphen, the colon can be omitted.
If there are no more arguments, you can omit the double dash.

```bash
ds test -v
```

If you're not passing arguments, you can put tasks names next to each other:

```bash
ds clean test
```

## Error Suppression

If a task starts with a plus sign (`+`), the plus sign is removed before the command is executed and the command will always produce an return code of `0` (i.e. it will always be considered to have completed successfully).

This is particularly useful in [composite commands](#composite-command) where you want subsequent steps to continue even if a particular step fails. For example:

<!--[[[cog insert_file("examples/readme/error-suppression.toml")]]]-->

```toml
# Example: Error suppression lets subsequent tasks continue after failure.

[scripts]
cspell = "cspell --gitignore '**/*.{py,txt,md,markdown}'"
format = "ruff format ."
die = "+exit 1" # returns error code of 0
die_hard = "exit 2" # returns an error code of 2 unless suppressed elsewhere
lint = ["+cspell", "format"] # format runs even if cspell finds misspellings
```

<!--[[[end]]]-->

Error suppression works both in configuration files and on the command-line:

```bash
ds die_hard format
# => error after `die_hard`

ds +die_hard format
# => no error
```

## Environment Variables

You can set environment variables on a per-task basis:

<!--[[[cog insert_file("examples/readme/environment-variables.toml")]]]-->

```toml
# Example: Environment variables can be set on tasks.

[scripts]
# set an environment variable
run = { cmd = "python -m src.server", env = { FLASK_PORT = "8080" } }

# use a file relative to the configuration file
run2 = { cmd = "python -m src.server", env-file = ".env" }

# composite tasks override environment variables
run3 = { composite = ["run"], env = { FLASK_PORT = "8081" } }
```

<!--[[[end]]]-->

You can also set environment variables on the command-line, but the apply to _all_ of the tasks:

```bash
ds -e FLASK_PORT=8080 run
ds --env-file .env run
```

## Workspaces

Workspaces are a way of managing multiple sub-projects from a top-level. `ds` supports `npm`, `rye`, `uv`, and `Cargo` style workspaces (see [examples](https://github.com/metaist/ds/tree/main/examples/workspace)).

When `ds` is called with the `--workspace` option, the configuration file must have one of the following keys:

<!--[[[cog
from ds.configs import SEARCH_KEYS_WORKSPACE
cog.outl()
for key in SEARCH_KEYS_WORKSPACE:
    cog.outl(f"- `{key}`")
cog.outl()
]]]-->

- `workspace.members`
- `tool.ds.workspace.members`
- `tool.rye.workspace.members`
- `tool.uv.workspace.members`
- `workspaces`

<!--[[[end]]]-->

If no configuration file was provided with the `--file` option, search continues up the directory tree.

**NOTE**: `pnpm` has its own [`pnpm-workspace.yaml`](https://pnpm.io/pnpm-workspace_yaml) format which is not currently supported.

### Workspace Members

The value corresponding to the workspace key should be a list of patterns that indicate which directories (relative to the configuration file) should be included as members. The following `glob`-like patterns are supported:

- `?`: matches a single character (e.g., `ca?` matches `car`, `cab`, and `cat`)
- `[]`: matches specific characters (e.g., `ca[rb]` matches `car` and `cab`)
- `*`: matches multiple characters, but not `/` (e.g., `members/*` matches all the files in `members`, but not further down the tree)
- `**`: matches multiple characters, including `/` (e.g., `members/**` matches all files in `members` and all sub-directories and all of their contents)

If you prefix any pattern with an exclamation point (`!`) then the rest of the pattern describes which files should _not_ be matched.

Patterns are applied in order so subsequent patterns can include or exclude sub-directories as needed. [We also support the `excludes` key](https://github.com/metaist/ds/tree/main/examples/workspace/Cargo.toml) (for `uv` and `Cargo`) which is applied _after_ all the members.

<!--[[[cog insert_file("examples/workspace/ds.toml")]]]-->

```toml
# Example: workspace includes everything in `members` except `members/x`.

[workspace]
members = ["members/*", "!members/x"]
```

<!--[[[end]]]-->

### Workspace Tasks

To run a task across multiple workspaces, use the `--workspace` or `-w` options one or more times with a pattern that indicates where the tasks should run.

For example, consider a workspace with directories `members/a`, `members/b`, and `members/x`. The configuration above would match the first two directories and exclude the third.

The following are all equivalent and run `test` in both `member/a` and `member/b`:

```bash
ds --workspace '*' test   # special match that means "all workspaces"
ds -w '*' test            # short option
ds -w* test               # even shorter option
ds -w '*/a' -w '*/b' test # manually select multiple workspaces
```

## Not Supported: Lifecycle Events

Some task runners (all the `node` ones, `pdm`, `composer`) support running additional pre- and post- tasks when you run a task. However, this obscures the relationship between tasks and can create surprises if you happen to have two tasks with unfortunate names (e.g., `pend` and `prepend`). `ds` does not plan to support this behavior (see [#24]).

As more explicit alternative is to use [composite commands](#composite-command) to clearly describe the relationship between a task and its pre- and post- tasks.

<!--[[[cog insert_file("examples/readme/lifecycle-bad.toml")]]]-->

```toml
# Bad example: hidden assumption that `build` calls `prebuild` first.
[scripts]
prebuild = "echo 'prebuild'"
build = "echo 'build'"
```

<!--[[[end]]]-->

<!--[[[cog insert_file("examples/readme/lifecycle-good.toml")]]]-->

```toml
# Good example: clear relationship between tasks.
[scripts]
prebuild = "echo 'prebuild'"
build = ["prebuild", "echo 'build'"]
```

<!--[[[end]]]-->

## Not Supported: `call` Tasks

Some task runners support special `call` tasks which get converted into language-specific calls. For example, both `pdm` and `rye` can `call` into python packages and `composer` can `call` into a PHP module call.

These types of tasks introduces a significant difference between what you write in the configuration file and what gets executed, so in the interest of reducing magic, `ds` does not currently support this behavior (see [#32]).

A more explicit alternative is to write out the call you intend:

```bash
# {"call": "pkg"} becomes:
python -m pkg

# {"call": "pkg:main('test')"} becomes:
python -c "import sys; from pkg import main as _1; sys.exit(main('test'))"
```

## Inspirations

I've used several task runners, usually as part of build tools. Below is a list of tools used or read about when building `ds`.

- 1976: [`make`][make] (C) - Together with its descendants, `make` is one of the most popular build & task running tools. It is fairly easy to make syntax errors and the tab-based indent drives me up the wall.

- 2000: [`ant`][ant] (Java) - an XML-based replacement for `make`. I actually liked using `ant` quite a bit until I stopped writing Java and didn't want to have `java` as a dependency for my `python` projects.

- 2008: [`gradle`][gradle] (Groovy/Kotlin) - Written for the `jvm`, I pretty much only use this for Android development. Can't say I love it.

- 2010: [`npm`][npm] (JavaScript) - Being able to add a simple `scripts` field to `package.json` made it very easy to run dev scripts. Supports `pre` and `post` lifecycle tasks.

- 2010: [`pdm`][pdm] (Python) - Supports 4 different types of tasks including `cmd`, `shell`, `call`, and `composite`.

- 2012: [`composer`][composer] (PHP) - Uses `composer.json`, similar to `package.json`. Supports pre- and post- task lifecycle for special tasks, command-line arguments, composite tasks, and other options.

- 2016: [`yarn`][yarn] (JavaScript) - An alternative to `npm` which also supports command-line arguments.

- 2016: [`pnpm`][pnpm] (JavaScript) - Another alternative to `npm` which supports many more options including running tasks in parallel.

- 2016: [`just`][just] (Rust) - Defines tasks in a `justfile`, similar to `make`. Supports detecting cycles, running parallel, and many other options.

- 2016: [`cargo-run-script`][cargo-run-script] (Rust) - Uses `Cargo.toml` to configure scripts and supports argument substitution (`$1`, `$2`, etc.).

- 2017: [`cargo-make`][cargo-make] (Rust) - Very extensive port of `make` to Rust defining tasks in `Makefile.toml`.

- 2022: [`hatch`][hatch] (Python) - Defines environment-specific scripts with the ability to suppress errors, like `make`.

- 2023: [`bun`][bun] (Zig) - An alternative to `node` and `npm`.

- 2023: [`rye`][rye] (Rust) - Up-and-coming replacement for managing python projects.

## License

[MIT License](https://github.com/metaist/ds/blob/main/LICENSE.md)

[#24]: https://github.com/metaist/ds/issues/24
[#32]: https://github.com/metaist/ds/issues/32
[#44]: https://github.com/metaist/ds/issues/44
[#46]: https://github.com/metaist/ds/issues/46
[#51]: https://github.com/metaist/ds/issues/51
[#54]: https://github.com/metaist/ds/issues/54
[#68]: https://github.com/metaist/ds/issues/68
[ant]: https://en.wikipedia.org/wiki/Apache_Ant
[bun run]: https://bun.sh/docs/cli/run
[bun]: https://en.wikipedia.org/wiki/Bun_(software)
[cargo run-script]: https://github.com/JoshMcguigan/cargo-run-script/
[cargo-make]: https://github.com/sagiegurari/cargo-make
[cargo-run-script]: https://github.com/JoshMcguigan/cargo-run-script/
[composer run-script]: https://getcomposer.org/doc/articles/scripts.md#running-scripts-manually
[composer]: https://getcomposer.org
[gradle]: https://en.wikipedia.org/wiki/Gradle
[hatch]: https://hatch.pypa.io/1.12/config/environment/overview/#scripts
[just]: https://github.com/casey/just
[make]: https://en.wikipedia.org/wiki/Make_(software)
[npm run]: https://docs.npmjs.com/cli/v10/commands/npm-run-script
[npm]: https://en.wikipedia.org/wiki/Npm
[pdm run]: https://pdm-project.org/latest/usage/scripts/#user-scripts
[pdm]: https://pdm-project.org
[pnpm run]: https://pnpm.io/cli/run
[pnpm]: https://pnpm.io
[rye run]: https://rye.astral.sh/guide/commands/run/
[rye]: https://rye.astral.sh
[yarn run]: https://yarnpkg.com/cli/run
[yarn]: https://yarnpkg.com
[example-tasks]: https://github.com/metaist/ds/tree/main/examples/formats
