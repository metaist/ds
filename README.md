# ds: run dev scripts

<!--
[[[cog from cog_helpers import * ]]]
[[[end]]]
-->

<!-- <p align="center">
  <a href="https://metaist.github.io/ds/"><img alt="ds" width="200" src="https://raw.githubusercontent.com/metaist/ds/main/dash-the-rabbit.png" /></a><br />
  <em>Dash the Sprinter</em>
</p> -->
<p align="center">
  <a href="https://github.com/metaist/ds/actions/workflows/ci.yaml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/metaist/ds/.github/workflows/ci.yaml?branch=main&logo=github"/></a>
  <a href="https://pypi.org/project/ds-run"><img alt="PyPI" src="https://img.shields.io/pypi/v/ds-run.svg?color=blue" /></a>
  <a href="https://pypi.org/project/ds-run"><img alt="Supported Python Versions" src="https://img.shields.io/pypi/pyversions/ds-run" /></a>
</p>

A very simple task runner to run dev scripts (e.g., lint, build, test, start server) that works across multiple projects and is language-agnostic (see [Inspirations](#inspirations)).

## Benefits

♻️ **Works with existing projects**<br />
[Almost](#limitations) a drop-in replacement for:

- **Node** (`package.json`): [`npm run`][npm run], [`yarn run`][yarn run], [`pnpm run`][pnpm run], [`bun run`][bun run]
- **Python** (`pyproject.toml`): [`pdm run`][pdm run], [`rye run`][rye run]
- **PHP** (`composer.json`): [`composer run-script`][composer run-script]
- **Rust** (`Cargo.toml`): [`cargo run-script`][cargo run-script]

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
- In Progress: [Shell Completions][#44] (see [#44])
- In Progress: [Task-Specific Env Vars][#51] (see [#51])
- In Progress: [Remove Python Dependency][#46] (see [#46])

## Install

`ds` is typically installed at the system-level to make it available across all your projects.

```bash
python -m pip install ds-run

# or, if you use uv:
uv pip install --system ds-run
```

## Example

Create a `ds.toml` file in the top-level of your project or you can also put this configuration in an existing [project configuration file](#where-should-i-put-my-config) to reduce file-cruft.

<!--[[[cog insert_file("examples/readme/example.toml")]]]-->

```toml
# Example: Basic `ds` configuration.

[scripts]
clean = "rm -rf build/"
build = "mkdir $@" # pass arguments
all = ["clean", "build -p build"] # a composite task
```

<!--[[[end]]]-->

Now you can list the tasks with `ds --list` or just `ds`:

```
# Found 3 tasks in ds.toml

clean:
    rm -rf build/

build:
    mkdir $@

all:
    ['clean', 'build -p build']
```

Run the tasks.

```bash
ds clean
# => rm -rf build/

ds build: some-folder
# => mkdir some-folder

ds all
# => rm -rf build/
# => mkdir -p build
```

Read more:

- [Configuration File](#configuration-file)
- [Argument Interpolation](#argument-interpolation)
- [Error Suppression](#error-suppression)

## Where should I put my config?

To avoid making lots of top-level files, `ds` tries to use common project configuration files.

- **Node**: `package.json` under `scripts`
- **Python**: `pyproject.toml` under `[tool.ds.scripts]`
- **PHP**: `composer.json` under `scripts`
- **Rust**: `Cargo.toml` under `[package.metadata.scripts]` or `[workspace.metadata.scripts]`
- **Other**: `ds.toml` under `[scripts]`

Read more:

- [Example configuration files](https://github.com/metaist/ds/tree/main/examples/formats)
- [Configuration File](#configuration-file)
- [Workspaces](#workspaces)

## Usage

<!--[[[cog fenced_block(snip_file("src/ds/args.py", beg="Usage:", end="Examples:")) ]]]-->

```text
Usage: ds [--help | --version] [--debug]
          [--file PATH]
          [--cwd PATH]
          [--workspace GLOB]...
          [--list | (<task>[: <options>... --])...]

Options:
  -h, --help
    Show this message and exit.

  --version
    Show program version and exit.

  --debug
    Show debug messages.

  -f PATH, --file PATH
    File with task and workspace definitions (default: search in parents).

    Read more about the configuration file:
    https://github.com/metaist/ds#configuration-file

  --cwd PATH
    Set the starting working directory (default: --file parent).
    PATH is resolved relative to the current working directory.

  -w GLOB, --workspace GLOB
    Patterns which indicate in which workspaces to run tasks.

    GLOB filters the list of workspaces defined in `--file`.
    The special pattern '*' matches all of the workspaces.

    Read more about configuring workspaces:
    https://github.com/metaist/ds#workspaces

  -l, --list
    List available tasks and exit.

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

## Configuration File

`ds` supports `.json` and `.toml` configuration files (see [examples](https://github.com/metaist/ds/tree/main/examples/formats)).

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

<!--[[[end]]]-->

If you provide one or more `--workspace` options, the file must contain a [workspace key](#workspaces). Otherwise, then the file must contain a [task key](#task-keys).

If the appropriate key cannot be found, searching continues up the directory tree. The first file that has the appropriate key is used.

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

<!--[[[end]]]-->

## Task Names

- Task names are strings, that are usually short and all lowercase.
- They can have a colon (`:`) in them, like `py:build`, or other punctuation, like `py.build`.
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

## Workspaces

Workspaces are a way of managing multiple sub-projects from a top-level. `ds` supports `npm`, `rye`, and `Cargo` style workspaces (see [examples](https://github.com/metaist/ds/tree/main/examples/workspace)).

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

Patterns are applied in order so subsequent patterns can include or exclude sub-directories as needed. For compatibility with `Cargo`, [we also support the `excludes` key](https://github.com/metaist/ds/tree/main/examples/workspace/Cargo.toml) which is applied _after_ all the members.

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
ds -w '*/a' -w '*/b' test # enumerate each workspace
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
