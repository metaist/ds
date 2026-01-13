# Limitations
<!--
[[[cog from cog_helpers import * ]]]
[[[end]]]
-->

`ds` **does not** strive to be an all-in-one tool for every project and is not a replacement for package management tools or `make`. Here are some things that are not supported or not yet implemented.

- [Lifecycle Events](#not-supported-lifecycle-events)
- [`call` Tasks](#not-supported-call-tasks)
- Partial Support: `Makefile` format (see [#68](https://github.com/metaist/ds/issues/68))
- In Progress: Remove Python Dependency (see [#46](https://github.com/metaist/ds/issues/46))

## Not Supported: Lifecycle Events

Some task runners (all the `node` ones, `pdm`, `composer`) support running additional pre- and post- tasks when you run a task. However, this obscures the relationship between tasks and can create surprises if you happen to have two tasks with unfortunate names (e.g., `pend` and `prepend`). `ds` does not plan to support this behavior (see [#24](https://github.com/metaist/ds/issues/24)).

As more explicit alternative is to use [composite commands](tasks.md#composite-task) to clearly describe the relationship between a task and its pre- and post- tasks.

<!--[[[cog insert_file("examples/readme/lifecycle-bad.toml")]]]-->

```toml
# Bad example: hidden assumption that `build` calls `prebuild` first.
[scripts]
prebuild = "echo 'prebuild'"
build = "echo 'build'"
```

<!--[[[end]]]-->

<!--[[[cog insert_file("examples/readme/lifecycle-good.toml")]]]-->

```toml
# Good example: clear relationship between tasks.
[scripts]
prebuild = "echo 'prebuild'"
build = ["prebuild", "echo 'build'"]
```

<!--[[[end]]]-->

## Not Supported: `call` Tasks

Some task runners support special `call` tasks which get converted into language-specific calls. For example, both `pdm` and `rye` can `call` into python packages and `composer` can `call` into a PHP module call.

These types of tasks introduces a significant difference between what you write in the configuration file and what gets executed, so in the interest of reducing magic, `ds` does not currently support this behavior (see [#32](https://github.com/metaist/ds/issues/32)).

A more explicit alternative is to write out the call you intend:

```bash
# {"call": "pkg"} becomes:
python -m pkg

# {"call": "pkg:main('test')"} becomes:
python -c "import sys; from pkg import main as _1; sys.exit(main('test'))"
```
