## ds: Run Dev Scripts

<p align="center">
  <a href="https://metaist.github.io/ds/"><img alt="ds" width="200" src="https://raw.githubusercontent.com/metaist/ds/main/dash-the-rabbit.png" /></a><br />
  <em>Dash the Sprinter</em>
</p>
<p align="center">
  <a href="https://github.com/metaist/ds/actions/workflows/ci.yaml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/metaist/ds/.github/workflows/ci.yaml?branch=main&logo=github"/></a>
  <a href="https://pypi.org/project/ds"><img alt="PyPI" src="https://img.shields.io/pypi/v/ds.svg?color=blue" /></a>
  <a href="https://pypi.org/project/ds"><img alt="Supported Python Versions" src="https://img.shields.io/pypi/pyversions/ds" /></a>
</p>

## Why?

I often need to run scripts to build my code, run my server, lint my files, etc. Every project seems to use a different tool (e.g., [`make`], [`ant`], [`npm`], [`pnpm`], [`pdm`]), yet the basic commands I use in each project are largely the same. Therefore, I decided to build a very simple task runner see also [Inspirations](#inspirations).

## Inspirations

I've used several task runners, usually as part of build tools. Below is a list of tools used or read about when building `ds`.

- 1976: [`make`] (C) - Together with its descendants, `make` is one of the most popular build & task running tools. It is fairly easy to make syntax errors and the tab-based indent drives me up the wall.

- 2000: [`ant`] (Java) - an XML-based replacement for `make`. I actually liked using `ant` quite a bit until I stopped writing Java and didn't want to have `java` as a dependency for my `python` projects.

- 2008: [`gradle`] (Groovy/Kotlin) - Written for the `jvm`, I pretty much only use this for Android development. Can't say I love it.

- 2010: [`npm`] (JavaScript) - Being able to add a simple `scripts` field to `package.json` made it very easy to run dev scripts. Supports `pre` and `post` lifecycle tasks.

- 2010: [`pdm`] (Python) - Supports 4 different types of tasks including `cmd`, `shell`, `call`, and `composite`.

- 2016: [`yarn`] (JavaScript) - An alternative to `npm` which also supports command-line arguments.

- 2016: [`pnpm`] (JavaScript) - Another alternative to `npm` which supports many more options including running tasks in parallel.

- 2016: [`just`] (Rust) - Defines tasks in a `justfile`, similar to `make`. Supports detecting cycles, running parallel, and many other options.

- 2016: [`cargo-run-script`] (Rust) - Uses `Cargo.toml` to configure scripts and supports argument substitution (`$1`, `$2`, etc.).

- 2017: [`cargo-make`] (Rust) - Very extensive port of `make` to Rust defining tasks in `Makefile.toml`.

- 2022: [`hatch`] (Python) - Defines environment-specific scripts with the ability to suppress errors, like `make`.

- 2023: [`bun`] (Zig) - An alternative to `node` and `npm`.

[`ant`]: https://en.wikipedia.org/wiki/Apache_Ant
[`bun`]: https://en.wikipedia.org/wiki/Bun_(software)
[`cargo-run-script`]: https://github.com/JoshMcguigan/cargo-run-script/
[`cargo-make`]: https://github.com/sagiegurari/cargo-make
[`gradle`]: https://en.wikipedia.org/wiki/Gradle
[`hatch`]: https://hatch.pypa.io/1.12/config/environment/overview/#scripts
[`just`]: https://github.com/casey/just
[`make`]: https://en.wikipedia.org/wiki/Make_(software)
[`npm`]: https://en.wikipedia.org/wiki/Npm
[`pdm`]: https://pdm-project.org/latest/usage/scripts/#user-scripts
[`pnpm`]: https://pnpm.io/cli/run
[`yarn`]: https://yarnpkg.com/cli/run

## License

[MIT License](https://github.com/metaist/ds/blob/main/LICENSE.md)
