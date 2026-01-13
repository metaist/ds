# Getting Started

## Install

`ds` is typically installed at the system-level to make it available across all your projects.

```bash
uv tool install ds-run

# or, if you use pip:
pip install ds-run
```

You can also [download a Cosmopolitan binary](https://github.com/metaist/ds/releases/latest/download/ds) which runs on Windows, macOS, and Linux:

```bash
export LOCAL_BIN=$HOME/.local/bin # or anywhere on your PATH
mkdir -p $LOCAL_BIN
wget -O $LOCAL_BIN/ds -N https://github.com/metaist/ds/releases/latest/download/ds
chmod +x $LOCAL_BIN/ds
ds --version
# NOTE: it takes a few seconds the first time you run it
```

If you just want to try `ds`:

```bash
uvx ds-run --version
# or
pipx run ds-run --version
```

## When should I make a dev script?

Typically, you should make a dev script for important steps in your development process. For example, most projects will need a way to run linters and unit tests (see the [example on the home page](index.md#example)). Some projects also need a way to start up a server, fetch configuration files, or clean up generated files.

Dev scripts act as another form of documentation that helps developers understand how to build and work on your project.

## Where should I put my config?

`ds` supports `.json` and `.toml` configuration files (see [examples](https://github.com/metaist/ds/tree/main/examples/formats)) which typically go in the top-level of your project. To avoid making lots of top-level files, `ds` can use common project configuration files.

- **Node**: `package.json` under `scripts`
- **PHP**: `composer.json` under `scripts`
- **Python**: `pyproject.toml` under `[tool.ds.scripts]` (`[tool.pdm.scripts]` and `[tool.rye.scripts]` also supported)
- **Rust**: `Cargo.toml` under `[package.metadata.scripts]` or `[workspace.metadata.scripts]`
- **Other**: `ds.toml` under `[scripts]`

**Experimental**: We support an extremely small subset of the `Makefile` format (see [#68](https://github.com/metaist/ds/issues/68)).

Read more:

- [Example configuration files](https://github.com/metaist/ds/tree/main/examples/formats)
- [Workspaces](workspaces.md)

## How does `ds` find my config?

If you don't provide a config file using the `--file` option, `ds` will search the current directory and all of its parents for files with these name patterns in the following order:

<!--[[[cog
from ds.parsers import PARSERS
cog.outl()
for key in list(PARSERS):
    cog.outl(f"- `{key}`")
cog.outl()
]]] -->

- `ds.toml`
- `pyproject.toml`
- `uv.toml`
- `package.json`
- `Cargo.toml`
- `composer.json`
- `[Mm]akefile`

<!--[[[end]]]-->

If you provide one or more `--workspace` options, the file must contain a [workspace key](workspaces.md). Otherwise, the file must contain a [task key](#task-keys).

If the appropriate key cannot be found, searching continues up the directory tree. The first file that has the appropriate key is used.

One exception to the search process is when using the `--workspace` option: If a workspace member contains a file with the same name as the configuration file, that file is used _within_ the workspace (e.g., a workspace defined in `Cargo.toml` will try to find a `Cargo.toml` in each workspace). Otherwise, the usual search process is used.

## Where do tasks run?

Typically, tasks run in the same directory as the configuration file.

If you provide a `--cwd` option (but not a `--workspace` option), tasks will run in the directory provided by the `--cwd` option.

If you provide one or more `--workspace` options, `--cwd` is ignored and tasks are run in each of the selected workspace members.

!!! note

    In configuration files, you can use the `cwd` or `working_dir` option to specify a working directory for a _specific_ task and that option will be respected even when using `--workspace` or `--cwd` from the command line.

## Project Dependencies

`ds` automatically detects and activates project dependencies:

**Python Virtual Environments**

If a `.venv` directory exists (or `VIRTUAL_ENV` is set), `ds` automatically activates it before running tasks. You don't need to manually activate your virtual environment.

**Node.js node_modules**

If a `node_modules/.bin` directory exists, `ds` adds it to `PATH` so you can run locally-installed npm binaries directly:

```toml
[scripts]
# These work without npx because node_modules/.bin is in PATH
lint = "eslint src/"
format = "prettier --write ."
```

Use `--no-project` to disable this automatic detection.

## Shell Completion

`ds` supports shell completion for bash, zsh, and fish.

**Bash** (add to `~/.bashrc`):

```bash
eval "$(ds --completion bash)"
```

**Zsh** (add to `~/.zshrc`):

```zsh
eval "$(ds --completion zsh)"
```

**Fish** (add to `~/.config/fish/config.fish`):

```fish
ds --completion fish | source
```

After adding the appropriate line and restarting your shell, you can use Tab to complete task names and options.

## Task Keys

`ds` searches configuration files for [tool-specific keys](https://github.com/metaist/ds/tree/main/examples/formats) to find task definitions which should contain a mapping from [task names](tasks.md#task-names) to [basic tasks](tasks.md#basic-task) or [composite tasks](tasks.md#composite-task).
