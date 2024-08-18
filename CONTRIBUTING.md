# Contributing

## Local Development

```bash
# get the code
git clone git@github.com:metaist/ds.git
cd ds

# create a virtual environment
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip

# install dependencies and dev tools
pip install -e ".[dev]"
```

As you work on the code, you should periodically run:

```bash
ds dev # check lint, type-checks, and run tests
```

This repo generally tries to maintain type-correctness (via `mypy` and `pyright`) and complete unit test coverage.

## Making a Release

Checkout `prod`:

```bash
git checkout prod
git merge --no-ff --no-edit main
```

Update top-most `__init__.py`:

```python
__version__ = "X.0.1"
```

Update `CHANGELOG.md`:

Sections order is: `Fixed`, `Changed`, `Added`, `Deprecated`, `Removed`, `Security`.

```markdown
---

[X.0.1]: https://github.com/metaist/ds/compare/X.0.0...X.0.1

## [X.0.1] - XXXX-XX-XXT00:00:00Z

**Fixed**

**Changed**

**Added**

**Deprecated**

**Removed**

**Security**
```

###

```bash
export VER="X.0.1"

# final checks
ds all

# check build
ds build

# commit and push tags
ds release: $VER
```

[Create the release on GitHub](https://github.com/metaist/ds/releases/new). The `pypi.yaml` workflow will attempt to publish it to PyPI.
