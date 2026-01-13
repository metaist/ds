# Limitations
<!--
[[[cog from cog_helpers import * ]]]
[[[end]]]
-->

`ds` **does not** strive to be an all-in-one tool for every project and is not a replacement for package management tools or `make`. Here are some things that are not supported or not yet implemented.

- [Lifecycle Events](#lifecycle-events) (experimental support via `--pre`/`--post`)
- [`call` Tasks](#call-tasks) (supported for Python only)
- Partial Support: `Makefile` format (see [#68](https://github.com/metaist/ds/issues/68))
- In Progress: Remove Python Dependency (see [#46](https://github.com/metaist/ds/issues/46))

## Lifecycle Events

Some task runners (all the `node` ones, `pdm`, `composer`) support running additional pre- and post- tasks when you run a task. However, this obscures the relationship between tasks and can create surprises if you happen to have two tasks with unfortunate names (e.g., `pend` and `prepend`). By default, `ds` does not automatically run pre/post tasks (see [#24](https://github.com/metaist/ds/issues/24)).

!!! warning "Experimental Feature"

    You can enable lifecycle events using the `--pre` and/or `--post` flags:

    ```bash
    ds --pre --post build
    # Looks for: prebuild, pre_build, or pre-build (runs first)
    # Then runs: build
    # Then looks for: postbuild, post_build, or post-build (runs last)
    ```

    See [Pre/Post Hooks](tasks.md#prepost-hooks) for more details.

A more explicit alternative is to use [composite commands](tasks.md#composite-task) to clearly describe the relationship between a task and its pre- and post- tasks.

<!--[[[cog insert_file("examples/readme/lifecycle-bad.toml")]]]-->

```toml
# Implicit: hidden assumption that `build` calls `prebuild` first.
[scripts]
prebuild = "echo 'prebuild'"
build = "echo 'build'"
```

<!--[[[end]]]-->

<!--[[[cog insert_file("examples/readme/lifecycle-good.toml")]]]-->

```toml
# Explicit: clear relationship between tasks.
[scripts]
prebuild = "echo 'prebuild'"
build = ["prebuild", "echo 'build'"]
```

<!--[[[end]]]-->

## `call` Tasks

Some task runners support special `call` tasks which get converted into language-specific calls. For example, both `pdm` and `rye` can `call` into python packages and `composer` can `call` into a PHP module call.

**Python `call` tasks are supported** in `pyproject.toml` (for pdm, rye, poetry, and ds-style configurations):

```toml
[tool.ds.scripts]
# Call a module (becomes: python -m http.server)
serve = { call = "http.server" }

# Call a function (becomes: python -c "import sys; import myapp as _1; sys.exit(_1.main())")
run = { call = "myapp:main" }

# Call with arguments
greet = { call = "myapp:greet('Hello')" }
```

!!! note "Python Only"

    `call` tasks are only supported in `pyproject.toml`. PHP `call` tasks from `composer.json` are not supported (see [#32](https://github.com/metaist/ds/issues/32)).

If you prefer explicitness, you can write out the call directly:

```bash
# {"call": "pkg"} becomes:
python -m pkg

# {"call": "pkg:main('test')"} becomes:
python -c "import sys; import pkg as _1; sys.exit(_1.main('test'))"
```
