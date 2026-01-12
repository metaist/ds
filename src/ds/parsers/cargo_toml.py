"""`Cargo.toml` parser."""

# std
import logging

# pkg
from . import ds_toml
from . import toml
from ..configs import Config
from ..configs import Membership
from ..searchers import get_key
from ..symbols import KEY_MISSING
from ..tasks import Tasks
from .utils import parse_workspace_globs


log = logging.getLogger(__name__)

loads = toml.loads
"""Standard `toml` parser."""


def parse_workspace(config: Config, key: str = "workspace") -> Membership:
    """Workspaces are in `[workspace]`.

    See: https://doc.rust-lang.org/cargo/reference/workspaces.html
    """
    data = get_key(config.data, key, KEY_MISSING)
    if data is KEY_MISSING:
        raise KeyError(f"Missing '{key}' key in {config.path}")

    return parse_workspace_globs(config, data, allow_inline_excludes=False)


def parse_tasks(config: Config, key: str = "workspace.metadata.scripts") -> Tasks:
    """Tasks are not officially defined `Cargo.toml`.

    However, we'll look at:
    - `workspace.metadata.scripts`
    - `package.metadata.scripts`
    """
    if get_key(config.data, key, KEY_MISSING) is KEY_MISSING:
        key = "package.metadata.scripts"
        if get_key(config.data, key, KEY_MISSING) is KEY_MISSING:
            raise KeyError(f"Missing '{key}' key in {config.path}")
    return ds_toml.parse_tasks(config, key)
