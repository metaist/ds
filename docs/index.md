# ds: run dev scripts
<!--
[[[cog from cog_helpers import * ]]]
[[[end]]]
-->

<p align="center">
  <strong>One command. Every project.</strong>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-pyproject.toml-3776AB?logo=python&logoColor=white" />
  <img alt="Node.js" src="https://img.shields.io/badge/Node.js-package.json-339933?logo=node.js&logoColor=white" />
  <img alt="Rust" src="https://img.shields.io/badge/Rust-Cargo.toml-000000?logo=rust&logoColor=white" />
  <img alt="PHP" src="https://img.shields.io/badge/PHP-composer.json-777BB4?logo=php&logoColor=white" />
  <img alt="Make" src="https://img.shields.io/badge/Make-Makefile-A42E2B?logo=gnu&logoColor=white" />
</p>

Stop memorizing different task runners for each language. `ds` runs dev scripts from your project's existing configuration file—whether it's `package.json`, `pyproject.toml`, `Cargo.toml`, or `composer.json`:

```bash
uv tool install ds-run  # or: pip install ds-run
ds --list           # list the tasks
ds clean lint test  # run multiple tasks
ds format:*         # run tasks that match a glob
ds test -vv         # pass arguments to tasks
ds -e PORT=8080 run # set environment variables
ds +cspell test     # suppress errors
ds -w* build        # supports monorepo/workspaces
```

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

**Works with existing projects**

[Almost](limitations.md) a drop-in replacement for:

- **Node** (`package.json`): `npm run`, `yarn run`, `pnpm run`, `bun run`
- **Python** (`pyproject.toml`): `pdm run`, `rye run`
- **PHP** (`composer.json`): `composer run-script`
- **Rust** (`Cargo.toml`): `cargo run-script`

**Experimental**: We also support an extremely small subset of the `Makefile` format (see [#68](https://github.com/metaist/ds/issues/68)).

**Add monorepo/workspace support anywhere**

Easily [manage monorepos and sub-projects](workspaces.md), even if they use different tooling.

**Run multiple tasks with custom arguments for each task**

Provide [command-line arguments](tasks.md#command-line-arguments) for multiple tasks as well as simple [argument interpolation](tasks.md#argument-interpolation).

**Minimal magic**

Tries to use familiar syntax and a few clear rules. Checks for basic cycles and raises helpful error messages if things go wrong.

**Minimal dependencies**

Currently working on removing all dependencies (see [#46](https://github.com/metaist/ds/issues/46)):

- python (3.10+)
- `tomli` (for python < 3.11)

## Comparison

How does `ds` compare to other task runners?

| Feature | ds | make | just | Task | npm scripts |
|---------|:--:|:----:|:----:|:----:|:-----------:|
| Uses existing config | **Yes** | No | No | No | package.json only |
| Multi-language support | **Yes** | No | No | No | No |
| Zero migration | **Yes** | No | No | No | Node only |
| Single binary | **Yes** | Yes | Yes | Yes | No |
| Cross-platform | Yes | Partial | Yes | Yes | Yes |
| Parallel execution | Yes | Yes | No | Yes | No* |
| Composite tasks | Yes | Yes | Yes | Yes | Partial |
| Environment variables | Yes | Yes | Yes | Yes | Partial |
| Workspaces/monorepo | Yes | No | No | Yes | Yes |

**Key differentiator**: `ds` reads your _existing_ `package.json`, `pyproject.toml`, `Cargo.toml`, or `composer.json`—no new config file needed.

\* Requires additional packages like `npm-run-all`

## Security

`ds` executes commands through your system shell with `shell=True`. This is by design—it allows shell features like pipes, redirects, and variable expansion to work naturally.

!!! warning "Shell Injection Risk"

    Arguments passed to tasks are interpolated directly into shell commands without escaping. If arguments come from untrusted sources (user input, environment variables, CI pipelines), they could contain shell metacharacters that alter command behavior.

    ```bash
    # Example of potentially dangerous input
    ds echo '; rm -rf /'  # The semicolon starts a new command!
    ```

`ds` will warn when arguments contain shell metacharacters (``; & | ` $ \ " ' < > ( ) { } * ? # !``), but does not block execution.

**Recommendations:**

- Only run `ds` with trusted task definitions and arguments
- Be cautious when passing external input as task arguments
- Review task definitions in shared/public repositories before running
