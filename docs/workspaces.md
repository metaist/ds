# Workspaces
<!--
[[[cog from cog_helpers import * ]]]
[[[end]]]
-->

Workspaces are a way of managing multiple sub-projects from a top-level. `ds` supports `npm`, `rye`, `uv`, and `Cargo` style workspaces.

When `ds` is called with the `--workspace` option, the configuration file must have one of the [tool-specific workspace keys](https://github.com/metaist/ds/tree/main/examples/workspace).

If no configuration file was provided with the `--file` option, search continues up the directory tree.

!!! note

    `pnpm` has its own [`pnpm-workspace.yaml`](https://pnpm.io/pnpm-workspace_yaml) format which is not currently supported.

## Workspace Members

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

## Workspace Tasks

To run a task across multiple workspaces, use the `--workspace` or `-w` options one or more times with a pattern that indicates where the tasks should run.

For example, consider a workspace with directories `members/a`, `members/b`, and `members/x`. The configuration above would match the first two directories and exclude the third.

The following are all equivalent and run `test` in both `member/a` and `member/b`:

```bash
ds --workspace '*' test   # special match that means "all workspaces"
ds -w '*' test            # short option
ds -w* test               # even shorter option
ds -w '*/a' -w '*/b' test # manually select multiple workspaces
```
