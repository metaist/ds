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
