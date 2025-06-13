"""Experimental git hooks integration."""

# std
from pathlib import Path
from textwrap import dedent
from typing import Literal, Tuple, Union, List
import os
import sys
import stat

# pkg
from .tasks import Tasks

GIT_HOOK_PREFIX = "git-hook-"
"""Hook prefix to look for in the task listing"""

VALID_GIT_HOOKS = [
    "applypatch-msg",
    "commit-msg",
    "fsmonitor-watchman",
    "post-update",
    "pre-applypatch",
    "pre-commit",
    "pre-merge-commit",
    "pre-push",
    "pre-rebase",
    "pre-receive",
    "prepare-commit-msg",
    "push-to-checkout",
    "update",
]
"""List of all valid git hook names."""

# ValidGitHookName = Literal[*VALID_GIT_HOOKS]
ValidGitHookName = Union[
    Literal["applypatch-msg"],
    Literal["commit-msg"],
    Literal["fsmonitor-watchman"],
    Literal["post-update"],
    Literal["pre-applypatch"],
    Literal["pre-commit"],
    Literal["pre-merge-commit"],
    Literal["pre-push"],
    Literal["pre-rebase"],
    Literal["pre-receive"],
    Literal["prepare-commit-msg"],
    Literal["push-to-checkout"],
    Literal["update"],
]
"""Type listing for all valid git hook names."""
# which i'd like to be derived from the list above but it doesn't appear to be valid


def create_hook_template(task_name: str) -> str:
    """
    Create a bash script template for a specified git hook.

    Args:
        hook_name (str): The name of the git hook task for which to create the template.

    Returns:
        str: A string containing the bash script template for the specified git hook.
    """
    # this is probably our best bet
    invocation = sys.argv[0]

    script = f"""\
    #! /bin/bash

    PATH="{os.getenv("PATH")}" {invocation} {GIT_HOOK_PREFIX}{task_name}: $@
    """

    return dedent(script).strip()


def find_git_directory() -> Path | None:
    """
    Recurse up directories until we find a .git folder, otherwise bail.
    """

    cwd = Path(".").absolute()

    # little hack: iterate through this directory and all its parents
    for path in [cwd, *cwd.parents]:
        gitpath = path / Path(".git")
        if gitpath.exists() and gitpath.is_dir():
            # found a match
            return gitpath

    return None


def create_list_of_hooks(tasks: Tasks) -> List[Tuple[str, str]]:
    """
    Create a list of git hook script filenames and contents.

    Does not actually modify the filesystem, only creates a listing.

    Returns:
        List[Tuple[str, str]]: List of (filename, contents) pairs
    """

    hooks: List[Tuple[str, str]] = []

    # list of valid hook names prefixed by the specified prefix
    search_list = set([f"{GIT_HOOK_PREFIX}{n}" for n in VALID_GIT_HOOKS])

    for task in tasks:
        # skip immediately
        if task not in search_list:
            continue

        hook_name = task.replace(GIT_HOOK_PREFIX, "")

        hooks.append((hook_name, create_hook_template(hook_name)))

    return hooks


def detect_installed_hooks(git_dir: Path) -> List[str]:
    """
    Detect installed git hooks in the specified git directory.

    Args:
        git_dir (Path): The path to the .git directory.

    Returns:
        List[str]: A list of installed git hook names.
    """
    hook_dir = git_dir / "hooks"

    detected_hooks = []
    for hook in hook_dir.iterdir():
        # this is usually filled with hookname.sample files, so we'll filter for just those with valid names
        if hook.name not in VALID_GIT_HOOKS:
            continue

        # if this isn't a file, ignore it as well
        if not hook.is_file():
            continue

        detected_hooks.append(hook.name)

    return detected_hooks


def validate_installed_hooks(git_dir: Path, tasks: Tasks) -> bool:
    installed_hooks = detect_installed_hooks(git_dir)
    target_hooks = create_list_of_hooks(tasks)

    # early abort: if we haven't specified any hooks, none of this applies and we're good
    if len(target_hooks) == 0:
        return True

    # strategy: zip together detected and target hooks (sorted) and if we get a mismatch
    installed_hooks.sort()
    target_hooks.sort(key=lambda h: h[0])  # sort by filename

    if len(installed_hooks) != len(target_hooks):
        return False

    for installed_name, (target_name, target_body) in zip(
        installed_hooks, target_hooks
    ):
        if installed_name != target_name:
            return False

        installed_body = (git_dir / "hooks" / installed_name).read_text()
        if installed_body != target_body:
            return False

    return True


def force_install_hooks(git_dir: Path, tasks: Tasks) -> None:
    installed_hooks = detect_installed_hooks(git_dir)
    target_hooks = create_list_of_hooks(tasks)

    # remove old hooks
    for hook in installed_hooks:
        hook_path = git_dir / "hooks" / hook
        hook_path.unlink()

    # create new ones
    for hook, body in target_hooks:
        hook_path = git_dir / "hooks" / hook
        hook_path.write_text(body)
        # make sure to mark them executable on real systems (ie not windows)
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)
