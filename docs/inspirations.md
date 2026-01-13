# Inspirations

I've used several task runners, usually as part of build tools. Below is a list of tools used or read about when building `ds`.

- **1976: [make](https://en.wikipedia.org/wiki/Make_(software))** (C) - Together with its descendants, `make` is one of the most popular build & task running tools. It is fairly easy to make syntax errors and the tab-based indent drives me up the wall.

- **2000: [ant](https://en.wikipedia.org/wiki/Apache_Ant)** (Java) - an XML-based replacement for `make`. I actually liked using `ant` quite a bit until I stopped writing Java and didn't want to have `java` as a dependency for my `python` projects.

- **2008: [gradle](https://en.wikipedia.org/wiki/Gradle)** (Groovy/Kotlin) - Written for the `jvm`, I pretty much only use this for Android development. Can't say I love it.

- **2010: [npm](https://en.wikipedia.org/wiki/Npm)** (JavaScript) - Being able to add a simple `scripts` field to `package.json` made it very easy to run dev scripts. Supports `pre` and `post` lifecycle tasks.

- **2010: [pdm](https://pdm-project.org)** (Python) - Supports 4 different types of tasks including `cmd`, `shell`, `call`, and `composite`.

- **2012: [composer](https://getcomposer.org)** (PHP) - Uses `composer.json`, similar to `package.json`. Supports pre- and post- task lifecycle for special tasks, command-line arguments, composite tasks, and other options.

- **2016: [yarn](https://yarnpkg.com)** (JavaScript) - An alternative to `npm` which also supports command-line arguments.

- **2016: [pnpm](https://pnpm.io)** (JavaScript) - Another alternative to `npm` which supports many more options including running tasks in parallel.

- **2016: [just](https://github.com/casey/just)** (Rust) - Defines tasks in a `justfile`, similar to `make`. Supports detecting cycles, running parallel, and many other options.

- **2016: [cargo-run-script](https://github.com/JoshMcguigan/cargo-run-script/)** (Rust) - Uses `Cargo.toml` to configure scripts and supports argument substitution (`$1`, `$2`, etc.).

- **2017: [cargo-make](https://github.com/sagiegurari/cargo-make)** (Rust) - Very extensive port of `make` to Rust defining tasks in `Makefile.toml`.

- **2022: [hatch](https://hatch.pypa.io/1.12/config/environment/overview/#scripts)** (Python) - Defines environment-specific scripts with the ability to suppress errors, like `make`.

- **2023: [bun](https://en.wikipedia.org/wiki/Bun_(software))** (Zig) - An alternative to `node` and `npm`.

- **2023: [rye](https://rye.astral.sh)** (Rust) - Up-and-coming replacement for managing python projects.
