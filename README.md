# ds: run dev scripts

<p align="center">
  <a href="https://metaist.github.io/ds/"><img alt="ds" width="200" src="https://raw.githubusercontent.com/metaist/ds/main/dash-the-rabbit.png" /></a><br />
  <em>Dash the Sprinter</em>
</p>
<p align="center">
  <a href="https://github.com/metaist/ds/actions/workflows/ci.yaml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/metaist/ds/.github/workflows/ci.yaml?branch=main&logo=github"/></a>
  <a href="https://pypi.org/project/ds"><img alt="PyPI" src="https://img.shields.io/pypi/v/ds.svg?color=blue" /></a>
  <a href="https://pypi.org/project/ds"><img alt="Supported Python Versions" src="https://img.shields.io/pypi/pyversions/ds" /></a>
</p>

<!--
[[[cog from cog_helpers import * ]]]
[[[end]]]
-->

## Why?

I often need to run scripts to build my code, run my server, lint my files, etc. Every project seems to use a different tool (e.g., [`make`], [`ant`], [`npm`], [`pnpm`], [`pdm`]), yet the basic commands I use in each project are largely the same. So I [was inspired](#inspirations) to build a very simple task runner.

- **Minimal magic**: Designed to use a familiar syntax and a few clear rules where possible. Not trying to recreate [`make`].
- **Low surprise**: checks for cycles and raises helpful error messages when things are wrong.
- **Works with existing files**: including `package.json`, `pyproject.toml`, and `Cargo.toml` files.
- **Run multiple tasks**: `[npm|yarn|pnpm|bun|pdm] run` can only run one task at a time.
- **Minimal dependencies**: working on removing all of these (see [#31])
  - python (3.8+)
  - `tomli` (for python < 3.11)
  - `graphlib_backport` (for python < 3.9)

## Install

```bash
python -m pip install dev-scripts

# or, if you use uv:
uv pip install dev-scripts
```

## Example

Create a `ds.toml` file in the top-level of your project or you can also put this configuration in [`package.json`, `pyproject.toml`, or `Cargo.toml`](#where-should-i-put-my-config) to reduce cruft.

<!--[[[cog insert_file("examples/readme-example.toml")]]]-->

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
['-clean', 'build -p build']
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

## Usage

<!--[[[cog
text = Path("src/ds/__init__.py").read_text()
beg = text.find("Usage:")
end = text.find("Examples:", beg)

cog.outl(f"\n```\n{text[beg:end].strip()}\n```\n")
]]]-->

```
Usage: ds [--help | --version] [--debug]
          [--cwd PATH] [--file PATH]
          [--list | (<task>[: <options>... --])...]

Options:
  -h, --help
    Show this message and exit.

  --version
    Show program version and exit.

  --debug
    Show debug messages.

  --cwd PATH
    Set the working directory (default: task file parent).

  -f PATH, --file PATH
    File with task definitions (default: search in parents).

  -l, --list
    List available tasks and exit.

  <task>[: <options>... --]
    One or more tasks to run with task-specific arguments.
    Use a colon (`:`) to indicate start of arguments and
    double-dash (`--`) to indicate the end.

    If the first <option> starts with a hyphen (`-`), you may omit the
    colon (`:`). If there are no more tasks after the last option, you
    may omit the double-dash (`--`).
```

<!--[[[end]]]-->

## Configuration File

If you don't provide a config file using the `--file` flag, `ds` will search the current directory and all of its parents for files with these names in the following order:

<!--[[[cog
text = snip_file("src/ds/__init__.py", skip_beg=True, beg="SEARCH_FILES = [", end="]")
text = replace_many(text, {
  '    "': "- `",   # make into a list
  '",': "`",        # convert quotes to backticks
}).strip()

cog.outl(f"\n{text}\n")
]]] -->

- `ds.toml`
- `.ds.toml`
- `package.json`
- `pyproject.toml`
- `Cargo.toml`

<!--[[[end]]]-->

The first file found will be used.

`ds` currently supports `json` and `toml` files. It searches for the following keys in the following order:

<!--[[[cog
text = snip_file("src/ds/__init__.py", skip_beg=True, beg="SEARCH_KEYS = [", end="]")[1:]
text = replace_many(text, {
  '    "': "- `",     # make into a list
  '",': "`",          # backticks for key name
  "  # ": " for `",   # comment into "for" with first backtick
  ", ": "`, `",       # start backtick for middle items
  "\n": "`\n",        # last backtick
}).strip()
cog.outl(f"\n{text}\n")
]]]-->

- `scripts` for `ds.toml`, `.ds.toml`, `package.json`
- `tool.ds.scripts` for `pyproject.toml`
- `tool.pdm.scripts` for `pyproject.toml`
- `package.metadata.scripts` for `Cargo.toml`

<!--[[[end]]]-->

The first key that is found is used and should be a mapping of [task names](#task-names) to [commands](#commands).

## Where should I put my config?

To avoid making lots of top-level files, `ds` tries to use common project configuration files.

- **Node**: `package.json` under `scripts` (see [Lifecycle Events Not Supported](#lifecycle-events-not-supported))
- **Python**: `pyproject.toml` under `[tool.ds.scripts]`
- **Rust**: `Cargo.toml` under `[package.metadata.scripts]`
- **Other**: `ds.toml` under `[scripts]`

## Task Names

- Task names are strings, that are usually short and all lowercase.
- They can have a colon (`:`) in them, like `py:build`, or other punctuation, like `py.build`.
- If the name starts with a hash (`#`) it is ignored. This comes from `package.json` in which its comment to add "comments" as JSON keys.
- Don't start a task name with a hyphen (`-`); it usually indicates [Error Suppression](#error-suppression).
- Don't end a task name with a colon (`:`); we use this to indicate [Command-line Arguments](#command-line-arguments)

## Commands

`ds` ultimately converts all commands into strings to be executed with `subprocess.run`.

### Basic Command

<!--[[[cog insert_file("examples/readme-basic.toml")]]]-->

```toml
# Example: Basic commands become strings.

[scripts]
ls = "ls -lah"
no_error = "-exit 1" # See "Error Suppression"

# We also support `pdm`-style commands.
# The following all produce the same command as `ls` above.
ls2 = { cmd = "ls -lah" }
ls3 = { cmd = ["ls", "-lah"] }
ls4 = { shell = "ls -lah" }
```

<!--[[[end]]]-->

A basic command is just a string of what should be executed in a shell.

- Supports most [`pdm`-style commands][`pdm`] (except `call`, see [#32])
- Supports [argument interpolation](#argument-interpolation)
- Supports [error suppression](#error-suppression)

### Composite Command

<!--[[[cog insert_file("examples/readme-composite.toml")]]]-->

```toml
# Example: Composite commands call other tasks or shell commands.

[scripts]
build = "touch build/$1"
clean = "rm -rf build"
all = ["clean", "-mkdir build", "build foo", "build bar", "echo 'Done'"]

# We also support pdm-style composite commands.
# The following is equivalent to `all`.
all2 = { composite = [
  "clean",
  "-mkdir build",
  "build foo",
  "build bar",
  "echo 'Done'",
] }
```

<!--[[[end]]]-->

A composite command consists of a series of steps where each step is the name of another task or a shell command.

- Supports [argument interpolation](#argument-interpolation)
- Supports [error suppression](#error-suppression)

## Argument Interpolation

Commands can include parameters like `$1` and `$2` to indicate that the command accepts arguments.
You can also use `$@` for the "remaining" arguments (i.e. those you haven't yet interpolated yet).

Arguments from a [composite command](#composite-command) precede those [from the command-line](#command-line-arguments).

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

If you're not passing arguments, you can put tasks names next to each other:

```bash
ds clean test
```

## Error Suppression

If a [command](#commands) starts with a hyphen (`-`), the leading hyphen is removed before the command is executed and the command will always produce an error code of `0` (i.e. it will always be considered to have completed successfully).

This is particularly useful in [composite commands](#composite-command) where you want subsequent steps to continue even if a particular step fails. For example:

<!--[[[cog insert_file("examples/readme-error-suppression.toml")]]]-->

```toml
# Example: Error suppression lets a command continue even if it fails.

[scripts]
cspell = "cspell --gitignore '**/*.{py,txt,md,markdown}'"
format = "ruff format ."
die = "-exit 1" # returns error code of 0
lint = ["-cspell", "format"] # run format even if cspell finds some misspelled words
```

<!--[[[end]]]-->

Error suppression is currently only available in configuration files and not on the command-line API (see [#22]).

## Lifecycle Events Not Supported

Some task runners support running additional pre- and post- tasks. However, this is currently not supported (see [#24]). Part of the reason is that it obscures the relationship between tasks and creates surprise if you have to have two tasks with unfortunate names.

As more explicit alternative is to use [composite commands](#composite-command) to clearly describe the relationship between a task and its pre- and post- tasks.

## Inspirations

I've used several task runners, usually as part of build tools. Below is a list of tools used or read about when building `ds`.

- 1976: [`make`] (C) - Together with its descendants, `make` is one of the most popular build & task running tools. It is fairly easy to make syntax errors and the tab-based indent drives me up the wall.

- 2000: [`ant`] (Java) - an XML-based replacement for `make`. I actually liked using `ant` quite a bit until I stopped writing Java and didn't want to have `java` as a dependency for my `python` projects.

- 2008: [`gradle`] (Groovy/Kotlin) - Written for the `jvm`, I pretty much only use this for Android development. Can't say I love it.

- 2010: [`npm`] (JavaScript) - Being able to add a simple `scripts` field to `package.json` made it very easy to run dev scripts. Supports `pre` and `post` lifecycle tasks.

- 2010: [`pdm`] (Python) - Supports 4 different types of tasks including `cmd`, `shell`, `call`, and `composite`.

- 2016: [`yarn`] (JavaScript) - An alternative to `npm` which also supports command-line arguments.

- 2016: [`pnpm`] (JavaScript) - Another alternative to `npm` which supports many more options including running tasks in parallel.

- 2016: [`just`] (Rust) - Defines tasks in a `justfile`, similar to `make`. Supports detecting cycles, running parallel, and many other options.

- 2016: [`cargo-run-script`] (Rust) - Uses `Cargo.toml` to configure scripts and supports argument substitution (`$1`, `$2`, etc.).

- 2017: [`cargo-make`] (Rust) - Very extensive port of `make` to Rust defining tasks in `Makefile.toml`.

- 2022: [`hatch`] (Python) - Defines environment-specific scripts with the ability to suppress errors, like `make`.

- 2023: [`bun`] (Zig) - An alternative to `node` and `npm`.

## License

[MIT License](https://github.com/metaist/ds/blob/main/LICENSE.md)

[#22]: https://github.com/metaist/ds/issues/22
[#24]: https://github.com/metaist/ds/issues/24
[#31]: https://github.com/metaist/ds/issues/31
[#32]: https://github.com/metaist/ds/issues/32
[`ant`]: https://en.wikipedia.org/wiki/Apache_Ant
[`bun`]: https://en.wikipedia.org/wiki/Bun_(software)
[`cargo-make`]: https://github.com/sagiegurari/cargo-make
[`cargo-run-script`]: https://github.com/JoshMcguigan/cargo-run-script/
[`gradle`]: https://en.wikipedia.org/wiki/Gradle
[`hatch`]: https://hatch.pypa.io/1.12/config/environment/overview/#scripts
[`just`]: https://github.com/casey/just
[`make`]: https://en.wikipedia.org/wiki/Make_(software)
[`npm`]: https://en.wikipedia.org/wiki/Npm
[`pdm`]: https://pdm-project.org/latest/usage/scripts/#user-scripts
[`pnpm`]: https://pnpm.io/cli/run
[`yarn`]: https://yarnpkg.com/cli/run
