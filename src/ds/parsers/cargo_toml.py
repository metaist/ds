"""`Cargo.toml` parser."""

# std
import logging

# pkg
from . import Config
from . import Membership
from . import toml
from ..args import Args
from ..searchers import get_key
from ..searchers import glob_paths
from ..symbols import GLOB_EXCLUDE
from ..symbols import KEY_MISSING
from ..tasks import Tasks
from . import ds_toml


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

    members: Membership = {}
    if "members" in data:
        members = glob_paths(
            config.path.parent,
            data["members"],
            allow_all=False,
            allow_excludes=False,
            allow_new=True,
            previous=members,
        )

    if "exclude" in data:
        members = glob_paths(
            config.path.parent,
            [f"{GLOB_EXCLUDE}{p}" for p in data["exclude"]],
            allow_all=False,
            allow_excludes=True,
            allow_new=False,
            previous=members,
        )
    return members


def parse_tasks(
    args: Args, config: Config, key: str = "workspace.metadata.scripts"
) -> Tasks:
    """Tasks are not officially defined `Cargo.toml`.

    However, we'll look at:
    - `workspace.metadata.scripts`
    - `package.metadata.scripts`
    """
    if get_key(config.data, key, KEY_MISSING) is KEY_MISSING:
        key = "package.metadata.scripts"
        if get_key(config.data, key, KEY_MISSING) is KEY_MISSING:
            raise KeyError(f"Missing '{key}' key in {config.path}")
    return ds_toml.parse_tasks(args, config, key)
