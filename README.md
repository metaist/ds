# ds: run dev scripts

<p align="center">
  <strong>One command. Every project.</strong><br /><br />
  <a href="https://github.com/metaist/ds/actions/workflows/ci.yaml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/metaist/ds/.github/workflows/ci.yaml?branch=main&logo=github"/></a>
  <a href="https://pypi.org/project/ds-run"><img alt="PyPI" src="https://img.shields.io/pypi/v/ds-run.svg?color=blue" /></a>
  <a href="https://pypi.org/project/ds-run"><img alt="Supported Python Versions" src="https://img.shields.io/pypi/pyversions/ds-run" /></a>
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
ds test -vv         # pass arguments to tasks
```

**[Read the full documentation →](https://docs.metaist.com/ds/)**

## Quick Example

Add scripts to your `pyproject.toml`:

```toml
[tool.ds.scripts]
test = "pytest src test"
lint = ["ruff check .", "ruff format ."]
dev = ["lint", "test"]
```

Run them:

```bash
ds dev        # run lint then test
ds test -v    # pass arguments
ds +lint test # suppress lint errors, continue to test
```

## Why ds?

- **Works with existing projects** — reads `package.json`, `pyproject.toml`, `Cargo.toml`, `composer.json`, or `Makefile`
- **Zero migration** — no new config file needed
- **Multi-language** — same command for Python, Node, Rust, PHP projects
- **Single binary** — [Cosmopolitan build](https://github.com/metaist/ds/releases) runs on Windows, macOS, Linux

## Install

```bash
uv tool install ds-run
# or
pip install ds-run
```

Or download the [portable binary](https://github.com/metaist/ds/releases/latest/download/ds).

## Documentation

- [Getting Started](https://docs.metaist.com/ds/getting-started/)
- [Tasks](https://docs.metaist.com/ds/tasks/)
- [Workspaces](https://docs.metaist.com/ds/workspaces/)
- [CLI Reference](https://docs.metaist.com/ds/cli/)
- [CI/CD](https://docs.metaist.com/ds/ci-cd/)
- [Example configs](https://github.com/metaist/ds/tree/main/examples/formats)

## License

[MIT License](https://github.com/metaist/ds/blob/main/LICENSE.md)
