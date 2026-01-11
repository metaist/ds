# Configuration File Formats

This folder contains minimal examples of supported configuration file formats.

## Node

- `npm`, `pnpm`, `yarn`, `bun`: [`package.json`](./package.json)

## PHP

- `composer`: [`composer.json`](./composer.json)

## Python

- `ds`: [`pyproject.toml`](./pyproject-ds.toml)
- `pdm`: [`pyproject.toml`](./pyproject-pdm.toml)
- `rye`: [`pyproject.toml`](./pyproject-rye.toml)
- `poetry`: [`pyproject.toml`](./pyproject-poetry.toml)

## Rust

- `cargo`: [`Cargo.toml`](./Cargo.toml)

## Other

For all other languages and tools, use [`ds.toml`](./ds.toml).

**Experimental**: We also support an extremely small subset of the [`Makefile`](./Makefile) format (see [#68]).

## Cheat Sheet

Quick reference for common features across formats.

### Task Location

| Format | Key |
|--------|-----|
| `ds.toml` | `[scripts]` |
| `pyproject.toml` (ds) | `[tool.ds.scripts]` |
| `pyproject.toml` (pdm) | `[tool.pdm.scripts]` |
| `pyproject.toml` (rye) | `[tool.rye.scripts]` |
| `package.json` | `"scripts": {}` |
| `composer.json` | `"scripts": {}` |
| `Cargo.toml` | `[package.metadata.scripts]` |
| `Makefile` | targets |

### Basic Task

A simple shell command.

| Format | Syntax |
|--------|--------|
| `.toml` | `task = "cmd"` |
| `.toml` | `task = { cmd = "cmd" }` |
| `.toml` | `task = { shell = "cmd" }` |
| `.json` | `"task": "cmd"` |
| `Makefile` | `task:`<br>`⇥cmd` |

### Composite Task

Run multiple tasks or commands in sequence.

| Format | Syntax |
|--------|--------|
| `.toml` (ds) | `task = ["step1", "step2"]` |
| `.toml` (pdm) | `task = { composite = ["step1", "step2"] }` |
| `.toml` (rye) | `task = { chain = ["step1", "step2"] }` |
| `.json` | `"task": "ds step1 step2"` |
| `Makefile` | `task: step1 step2` |

### Argument Interpolation

Pass arguments to tasks.

| Syntax | Description |
|--------|-------------|
| `$1`, `$2` | Positional arguments |
| `$@` | All remaining arguments |
| `${1:-default}` | Positional with default |
| `${@:-default}` | All args with default |
| `{args}` | pdm-style all args |
| `{args:default}` | pdm-style with default |

**Example:** `task = "pytest ${@:-src test}"`

### Environment Variables

| Format | Syntax |
|--------|--------|
| `.toml` | `task = { cmd = "cmd", env = { VAR = "val" } }` |
| `.toml` | `task = { cmd = "cmd", env_file = ".env" }` |
| `.toml` (rye) | `task = { cmd = "cmd", env-file = ".env" }` |
| `.json` | `"task": "ds -e VAR=val cmd"` |
| `Makefile` | `task:`<br>`⇥VAR=val`<br>`⇥cmd` |
| CLI | `ds -e VAR=val task` or `ds --env-file .env task` |

### Error Suppression

Continue execution even if a task fails.

| Format | Syntax |
|--------|--------|
| `.toml` (ds) | `task = "+cmd"` |
| `.toml` (pdm) | `task = { cmd = "cmd", keep_going = true }` |
| `.toml` composite | `task = ["+failing_task", "next"]` |
| `.json` | `"task": "ds +failing_task"` |
| `Makefile` recipe | `-cmd` (dash prefix) |
| `Makefile` prereq | `task: +failing_task` |
| CLI | `ds +task` |

### Working Directory

Run a task in a specific directory.

| Format | Syntax |
|--------|--------|
| `.toml` (ds) | `task = { cmd = "cmd", cwd = "dir" }` |
| `.toml` (pdm) | `task = { cmd = "cmd", working_dir = "dir" }` |
| `.json` | `"task": "ds --cwd dir cmd"` |
| `Makefile` | `task:`<br>`⇥cd dir`<br>`⇥cmd` |
| CLI | `ds --cwd dir task` |

### Task Help/Description

| Format | Syntax |
|--------|--------|
| `.toml` | `task = { cmd = "cmd", help = "description" }` |
| `.json` | `"#task": "description"` (comment key) |
| `composer.json` | `"scripts-descriptions": { "task": "desc" }` |
| `Makefile` | `task: # description` |

### Disabling Tasks

| Format | Syntax |
|--------|--------|
| `.toml` | `"#task" = "cmd"` |
| `.json` | `"#task": "cmd"` |

### Workspaces

| Format | Key |
|--------|-----|
| `ds.toml` | `[workspace]` with `members = [...]` |
| `pyproject.toml` (uv) | `[tool.uv.workspace]` with `members = [...]` |
| `pyproject.toml` (rye) | `[tool.rye]` with `workspace.members = [...]` |
| `package.json` | `"workspaces": [...]` |
| `Cargo.toml` | `[workspace]` with `members = [...]` |

**CLI:** `ds -w '*' task` or `ds --workspace 'pattern' task`

[#68]: https://github.com/metaist/ds/issues/68
