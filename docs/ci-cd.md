# CI/CD

Use `ds` in your CI pipelines—same commands locally and in CI.

## GitHub Actions

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install ds
        run: uv tool install ds-run  # or: pip install ds-run

      - name: Run tests
        run: ds test
```

Or use the [Cosmopolitan binary](https://github.com/metaist/ds/releases) for faster setup:

```yaml
      - name: Install ds
        run: |
          curl -L -o /usr/local/bin/ds https://github.com/metaist/ds/releases/latest/download/ds
          chmod +x /usr/local/bin/ds
```

## GitLab CI

```yaml
test:
  image: python:3.12
  script:
    - uv tool install ds-run  # or: pip install ds-run
    - ds test
```

## Other CI Systems

The pattern is the same for any CI system:

1. Install: `uv tool install ds-run` (or `pip install ds-run`)
2. Run: `ds <task>`

This works with CircleCI, Travis CI, Azure Pipelines, Jenkins, and others.
