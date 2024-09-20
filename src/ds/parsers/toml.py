"""Wrapper around importing `tomllib`."""

# std
import sys

# no cover: start
# Coverage disabled to cover all python versions.
# TODO 2026-10-31 @ py3.10 EOL: remove conditional
if sys.version_info >= (3, 11):
    import tomllib as toml
else:
    import tomli as toml
# no cover: stop

loads = toml.loads
"""Standard `toml` parser."""
