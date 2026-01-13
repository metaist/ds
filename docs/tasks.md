# Tasks
<!--
[[[cog from cog_helpers import * ]]]
[[[end]]]
-->

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

- Supports most `pdm`-style and `rye`-style commands (including [`call`](limitations.md#call-tasks) for Python)
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

- Supports `pdm`-style `composite` and `rye`-style `chain`
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

This is particularly useful in [composite commands](#composite-task) where you want subsequent steps to continue even if a particular step fails. For example:

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

You can also set environment variables on the command-line, but they apply to _all_ of the tasks:

```bash
ds -e FLASK_PORT=8080 run
ds --env-file .env run
```

## Working Directory

You can set a working directory for a task using `cwd` (or `working_dir`):

```toml
[scripts]
# run server from a subdirectory
server = { cmd = "python -m http.server", cwd = "dist" }
```

The path is relative to the configuration file location.

## Task Help

You can add a description to tasks using the `help` property. This is shown when running `ds --list`:

```toml
[scripts]
test.help = "Run unit tests with coverage"
test.cmd = "pytest --cov src test"

build.help = "Build the project"
build.composite = ["clean", "compile"]
```

## Shared Options

The special task name `_` (underscore) defines options that are applied to all other tasks:

```toml
[scripts]
# These options apply to all tasks
_ = { env = { DEBUG = "1" }, cwd = "src" }

# This task inherits env and cwd from _
test = "pytest"

# This task also inherits from _, but overrides cwd
build = { cmd = "make", cwd = "build" }
```

This is useful for setting common environment variables or working directories across all tasks.

## Parallel Execution

!!! warning "Experimental Feature"

    Parallel execution is experimental. Use `--parallel` on the command line.

Run top-level tasks in parallel:

```bash
ds --parallel lint test build
```

You can also enable parallel execution for a task's dependencies:

```toml
[scripts]
# Run lint-py and lint-js in parallel
lint = { composite = ["lint-py", "lint-js"], parallel = true }
lint-py = "ruff check ."
lint-js = "eslint src/"
```

Note: Parallel execution only applies to direct dependencies. Nested dependencies still run sequentially.

## Pre/Post Hooks

!!! warning "Experimental Feature"

    Pre/post hooks are experimental. Use `--pre` and/or `--post` on the command line.

When enabled, `ds` will automatically look for and run tasks with `pre` or `post` prefixes:

```bash
ds --pre --post build
# Looks for: prebuild, pre_build, or pre-build (runs first)
# Then runs: build
# Then looks for: postbuild, post_build, or post-build (runs last)
```

```toml
[scripts]
prebuild = "echo 'preparing...'"
build = "make"
postbuild = "echo 'done!'"
```

See [Limitations](limitations.md#lifecycle-events) for why this is not enabled by default.

## Task Configuration Reference

All available task properties:

| Property | Type | Description |
|----------|------|-------------|
| `cmd` | string or list | Shell command to execute |
| `shell` | string | Alias for `cmd` |
| `composite` | list | List of tasks/commands to run in sequence |
| `chain` | list | Alias for `composite` (rye-style) |
| `help` | string | Description shown in `--list` |
| `cwd` | string | Working directory (relative to config file) |
| `working_dir` | string | Alias for `cwd` |
| `env` | object | Environment variables for this task |
| `env_file` | string | Path to `.env` file to load |
| `env-file` | string | Alias for `env_file` (pdm-style) |
| `keep_going` | boolean | Continue on error (same as `+` prefix) |
| `parallel` | boolean | Run dependencies in parallel |

### Environment File Format

The `env_file` option loads variables from a file:

```bash
# .env file format
DATABASE_URL=postgres://localhost/mydb
SECRET_KEY=abc123

# 'export' prefix is also supported
export API_KEY=xyz789

# Variable expansion works
BASE_DIR=/app
LOG_DIR=${BASE_DIR}/logs

# Comments and blank lines are ignored
# This is a comment
```
