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

## Rust

- `cargo`: [`Cargo.toml`](./Cargo.toml)

## Other

For all other languages and tools, use [`ds.toml`](./ds.toml).

**Experimental**: We also support an extremely small subset of the [`Makefile`](./Makefile) format (see [#68]).

[#68]: https://github.com/metaist/ds/issues/68
