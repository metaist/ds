"""`uv.toml` parser."""

# std
import logging

# pkg
from . import cargo_toml
from ..configs import Config
from ..configs import Membership
from . import toml
from ..tasks import Tasks


log = logging.getLogger(__name__)

loads = toml.loads
"""Standard `toml` parser."""


def parse_workspace(config: Config, key: str = "tool.uv.workspace") -> Membership:
    """Workspaces are in `tool.uv.workspace` (pyproject.toml) or `workspace` (uv.toml).

    See:
    - https://docs.astral.sh/uv/concepts/workspaces/#workspace-roots
    - https://docs.astral.sh/uv/reference/settings/#workspace
    """
    if config.path.name == "uv.toml" and key == "tool.uv.workspace":
        key = "workspace"

    # It is clear from the documentation and from the general approach
    # that `uv` has taken that they are trying to keep the structure
    # similar to `Cargo.toml`.
    return cargo_toml.parse_workspace(config, key)


def parse_tasks(config: Config) -> Tasks:
    """`uv` does not define tasks."""
    raise NotImplementedError("`uv` does not support tasks.")
