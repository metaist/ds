# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog] and this project adheres to [Semantic Versioning].

Sections order is: `Fixed`, `Changed`, `Added`, `Deprecated`, `Removed`, `Security`.

[keep a changelog]: http://keepachangelog.com/en/1.0.0/
[semantic versioning]: http://semver.org/spec/v2.0.0.html

---

## [Unreleased]

[unreleased]: https://github.com/metaist/ds/compare/prod...main

These are changes that are on `main` that are not yet in `prod`.

---

[#24]: https://github.com/metaist/ds/issues/24
[#65]: https://github.com/metaist/ds/issues/65
[#72]: https://github.com/metaist/ds/issues/72
[#73]: https://github.com/metaist/ds/issues/73
[#74]: https://github.com/metaist/ds/issues/74
[#75]: https://github.com/metaist/ds/issues/75
[#76]: https://github.com/metaist/ds/issues/76
[#77]: https://github.com/metaist/ds/issues/77
[#78]: https://github.com/metaist/ds/issues/78
[#79]: https://github.com/metaist/ds/issues/79
[#80]: https://github.com/metaist/ds/issues/80
[#81]: https://github.com/metaist/ds/issues/81
[#82]: https://github.com/metaist/ds/issues/82
[#83]: https://github.com/metaist/ds/issues/83
[#84]: https://github.com/metaist/ds/issues/84
[#87]: https://github.com/metaist/ds/issues/87
[1.3.0]: https://github.com/metaist/ds/compare/1.2.0...1.3.0

## [1.3.0] - 2024-08-29T13:08:58Z

This release represents a shift from only supporting the overlap of all file formats to specific parsers for each supported format.

**Fixed**

- [#72]: `Makefile` links and Cosmopolitan instructions
- [#76]: logging in normal and debug modes

**Changed**

- [#65]: tried to detect current `SHELL` on Windows
- [#77]: refactored parsers, runner; each file format now has its own parser
- [#80]: config file search order
- [#81]: renamed environment variable `_DS_CURRENT_FILE` to `DS_INTERNAL__FILE`
- [#83]: moved `env_file` loading later (during run) instead of earlier (during parsing)
- [#84]: pass `env` values to `str`
- [#87]: moved project detection (`venv`, `node_modules/.bin`) earlier (right before top-level task run) instead of later (right before command run)

**Added**

- [#24]: `--pre` and `--post` options to run pre-/post- tasks
- [#73]: search for nearby `node_modules/.bin`
- [#74], [#78]: search for nearby `venv` if `VIRTUAL_ENV` is not set
- [#75]: `--no-config` and `--no-project` options to suppress searching for config files and project dependencies, respectively
- [#79]: more helpful debug messages (e.g., how to enable / disable options)
- [#82]: support for `poetry`

**Removed**

- As part [#77], `.ds.toml` is not longer a supported file format name.

---

[#14]: https://github.com/metaist/ds/issues/14
[#31]: https://github.com/metaist/ds/issues/31
[#64]: https://github.com/metaist/ds/issues/64
[#65]: https://github.com/metaist/ds/issues/65
[#66]: https://github.com/metaist/ds/issues/66
[#67]: https://github.com/metaist/ds/issues/67
[#68]: https://github.com/metaist/ds/issues/68
[#69]: https://github.com/metaist/ds/issues/69
[#70]: https://github.com/metaist/ds/issues/70
[#71]: https://github.com/metaist/ds/issues/71
[1.2.0]: https://github.com/metaist/ds/compare/1.1.0...1.2.0

## [1.2.0] - 2024-08-22T04:17:00Z

**Fixed**

- [#71]: allow `composite` (prerequisites) and `shell` (recipe) within a single task

**Changed**

- [#64]: allow shell commands directly when calling ds, e.g., `ds 'echo hello'`
- [#65]: `ds` now respects the value of the `SHELL` environment variable when running tasks
- [#70]: simplified `CI.yaml`

**Added**

- [#14]: instructions for using `uv` in `CONTRIBUTING.md`
- [#31]: Cosmopolitan Python build; Actually Portable Executable
- [#67]: `uv run` command that runs tests against all supported Python versions
- [#69]: documentation for why branch coverage is disabled
- [#66]: support for `uv` workspaces
- [#68]: support for simplified `Makefile` format

---

[#30]: https://github.com/metaist/ds/issues/30
[#46]: https://github.com/metaist/ds/issues/46
[#51]: https://github.com/metaist/ds/issues/51
[#52]: https://github.com/metaist/ds/issues/52
[#53]: https://github.com/metaist/ds/issues/53
[#55]: https://github.com/metaist/ds/issues/55
[#57]: https://github.com/metaist/ds/issues/57
[#58]: https://github.com/metaist/ds/issues/58
[#59]: https://github.com/metaist/ds/issues/59
[#60]: https://github.com/metaist/ds/issues/60
[#61]: https://github.com/metaist/ds/issues/61
[#62]: https://github.com/metaist/ds/issues/62
[1.1.0]: https://github.com/metaist/ds/compare/1.0.0...1.1.0

## [1.1.0] - 2024-08-18T04:48:22Z

**Changed**

- [#53]: `README.md` to have a quicker start section
- [#61]: improved command wrapping for `--list`

**Added**

- [#30]: `uv`, `uvx`, and `pipx` instructions to `README.md`
- [#51]: `--env` and `--env-file` command-line option together with `env` and `env-file`/`env_file` task options for passing environment variables to tasks
- [#55]: `--dry-run` command-line option to show which tasks would be run
- [#57]: support for glob-like task selector from the command line and in composite tasks
- [#58]: `help` task option to display description when using `--list`
- [#59]: support for `pdm`-style `{args}` during argument interpolation
- [#60]: `cwd` / `working_dir` task option for where tasks should run

---

[#17]: https://github.com/metaist/ds/issues/17
[#22]: https://github.com/metaist/ds/issues/22
[#28]: https://github.com/metaist/ds/issues/28
[#30]: https://github.com/metaist/ds/issues/30
[#32]: https://github.com/metaist/ds/issues/32
[#38]: https://github.com/metaist/ds/issues/38
[#41]: https://github.com/metaist/ds/issues/41
[#41]: https://github.com/metaist/ds/issues/41
[#42]: https://github.com/metaist/ds/issues/42
[#45]: https://github.com/metaist/ds/issues/45
[#47]: https://github.com/metaist/ds/issues/47
[#48]: https://github.com/metaist/ds/issues/48
[#49]: https://github.com/metaist/ds/issues/49
[#50]: https://github.com/metaist/ds/issues/50
[1.0.0]: https://github.com/metaist/ds/compare/0.1.3...1.0.0

## [1.0.0] - 2024-08-08T16:25:40Z

**Fixed**

- [#38]: `CHANGELOG` typo
- [#42]: pypi badges
- [#48]: missing docstring

**Changed**

- [#17]: config loading now looks for specific keys and tries more files if the key is not found
- [#47]: error suppression prefix string changed from hyphen (`-`) to plus (`+`).

**Added**

- [#22]: error suppression from the command-line
- [#28]: argument interpolation now accepts defaults
- [#30]: `__main__.py` to make `ds` executable as a package
- [#41]: `composer.json` support
- [#45]: support for workspaces
- [#49]: tasks that call `ds` have an implied default to use the same configuration file they were called from (via `_DS_CURRENT_CONFIG` environment variable).
- [#50]: support for `rye`

**Removed**

- [#32]: unused python `call` format string

---

[#40]: https://github.com/metaist/ds/issues/40
[0.1.3]: https://github.com/metaist/ds/compare/0.1.2...0.1.3

## [0.1.3] - 2024-07-25T06:20:18Z

**Fixed**

- [#40]: renamed PyPI package to `ds-run`

---

[#38]: https://github.com/metaist/ds/issues/38
[#39]: https://github.com/metaist/ds/issues/39
[0.1.2]: https://github.com/metaist/ds/compare/0.1.1...0.1.2

## [0.1.2] - 2024-07-25T06:06:36Z

**Fixed**

- [#38]: typo in `CHANGELOG.md`

**Changed**

- [#39]: moved `src/ds.py` into `src/ds/__init__.py` in the hope this will fix the PyPI publishing error

---

[#36]: https://github.com/metaist/ds/issues/36
[#37]: https://github.com/metaist/ds/issues/37
[0.1.1]: https://github.com/metaist/ds/compare/0.1.0...0.1.1

## [0.1.1] - 2024-07-25T05:29:41Z

**Fixed**

- [#36]: self-referential dependency

**Added**

- [#37]: release task

---

[#1]: https://github.com/metaist/ds/issues/1
[#2]: https://github.com/metaist/ds/issues/2
[#3]: https://github.com/metaist/ds/issues/2
[#4]: https://github.com/metaist/ds/issues/4
[#5]: https://github.com/metaist/ds/issues/5
[#6]: https://github.com/metaist/ds/issues/6
[#7]: https://github.com/metaist/ds/issues/7
[#8]: https://github.com/metaist/ds/issues/8
[#9]: https://github.com/metaist/ds/issues/9
[#10]: https://github.com/metaist/ds/issues/10
[#11]: https://github.com/metaist/ds/issues/11
[#12]: https://github.com/metaist/ds/issues/12
[#13]: https://github.com/metaist/ds/issues/13
[#14]: https://github.com/metaist/ds/issues/14
[#15]: https://github.com/metaist/ds/issues/15
[#16]: https://github.com/metaist/ds/issues/16
[#18]: https://github.com/metaist/ds/issues/18
[#19]: https://github.com/metaist/ds/issues/19
[#20]: https://github.com/metaist/ds/issues/20
[#21]: https://github.com/metaist/ds/issues/21
[#22]: https://github.com/metaist/ds/issues/22
[#23]: https://github.com/metaist/ds/issues/23
[#24]: https://github.com/metaist/ds/issues/24
[#25]: https://github.com/metaist/ds/issues/25
[#26]: https://github.com/metaist/ds/issues/26
[#29]: https://github.com/metaist/ds/issues/29
[#32]: https://github.com/metaist/ds/issues/32
[#33]: https://github.com/metaist/ds/issues/33
[#34]: https://github.com/metaist/ds/issues/34
[#35]: https://github.com/metaist/ds/issues/35
[0.1.0]: https://github.com/metaist/ds/commits/0.1.0

## [0.1.0] - 2024-07-25T04:42:52Z

Initial release.

**Fixed**

- [#7]: conditional import for `tomli`
- [#19]: double-quotes in f-string
- [#25]: `shell` and `cmd` [error suppression](https://github.com/metaist/ds#error-suppression)
- [#29]: running the same task twice (switch to detecting cycles)
- [#35]: py3.8 graphlib-backport missing types

**Changed**

- [#15]: generic parser to handle multiple file types
- [#16]: refactored `Task`
- [#18]: moved `ds.toml` configuration into `pyproject.toml`

**Added**

- Working with arguments:
  - [#4]: command-line task arguments
  - [#20]: `composite` task arguments
  - [#23]: parsing colon at end of task name on command-line
  - [#21]: [argument interpolation](https://github.com/metaist/ds#argument-interpolation)
  - [#33]: error if missing argument during interpolation
  - [#34]: `$@` to refer to "remaining" arguments
- New file formats:
  - [#2]: `ds.toml` support
  - [#5]: `package.json` support
  - [#8]: `pyproject.toml` support
  - [#12]: `Cargo.toml` support
- New CLI options
  - [#3]: `--list` to list tasks
  - [#10]: `--file` to specify a config file
  - [#11]: `--cwd` to specify current working directory
- Other
  - [#1]: setup repo
  - [#13]: [inspirations to README](https://github.com/metaist/ds#inspirations)

**Removed**

- [#6]: `pdm` dependency
- [#32]: `pdm`-style `call` command

**Not Implemented / Won't Fix**

- [#9]: handling duplicate task names
- [#14]: adding `uv` and `rye` instructions
- [#22]: adding command-line error suppression
- [#24]: running pre- and post- tasks
- [#26]: removing implicit task arg start; changing task arg end
