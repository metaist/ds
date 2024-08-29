# Workspace Configuration Files

This folder contains examples workspace configurations.

## Node

Members are usually in `./packages`.

- `npm`, `yarn`, `bun`: [`package.json`](./package.json)

**NOTE**: `pnpm` has its own [`pnpm-workspace.yaml`](https://pnpm.io/pnpm-workspace_yaml) format which is not currently supported.

## Python

Members are usually in `./modules`

- `ds`: [`pyproject-ds.toml`](./pyproject-ds.toml)
- `rye`: [`pyproject-rye.toml`](./pyproject-rye.toml)
- `uv`: [`pyproject-uv.toml`](./pyproject-uv.toml)

**Experimental**: `poetry` does not officially support workspaces, but there are are two plugins that do: [`pyproject-poetry1.toml`](./pyproject-poetry1.toml) or [`pyproject-poetry2.toml`](./pyproject-poetry2.toml)

## Rust

Members are usually in `./crates`.

- `cargo`: [`Cargo.json`](./Cargo.toml); the subfolder is usually called `crates`

## Other

- `ds`: [`ds.toml`](./ds.toml)
