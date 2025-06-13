"""Test the git hooks integration."""

# std
from pathlib import Path

# lib
import sys
import pytest
from ds.tasks import Tasks
from ds.parsers.ds_toml import parse_task

# pkg
from ds.env import TempEnv
from ds.git import (
    GIT_HOOK_PREFIX,
    ValidGitHookName,
    create_hook_template,
    create_list_of_hooks,
    detect_installed_hooks,
    find_git_directory,
    force_install_hooks,
    validate_installed_hooks,
)


def test_finds_git_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # setup: create nested directory structure with .git
    root = tmp_path / "project"
    nested = root / "src" / "module"
    git_dir = root / ".git"
    git_dir.mkdir(parents=True)
    nested.mkdir(parents=True)

    # change current working dir to nested module
    monkeypatch.chdir(nested)

    # do the test
    found = find_git_directory()

    assert found == git_dir


def test_returns_none_if_no_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # setup: create directory with no .git
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    monkeypatch.chdir(work_dir)

    # perform the test
    found = find_git_directory()

    assert found is None


def test_git_file_instead_of_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # setup: simulate a .git *file* (e.g., for a git worktree)
    root: Path = tmp_path / "project"
    nested: Path = root / "subdir"
    nested.mkdir(parents=True)

    git_file: Path = root / ".git"
    git_file.write_text("gitdir: ../.git/worktrees/project")

    monkeypatch.chdir(nested)

    # test
    found = find_git_directory()

    assert found is None


def test_git_create_hook_template() -> None:
    hook_name: ValidGitHookName = "pre-commit"

    script_expect = (
        f'#! /bin/bash\n\nPATH="test" {sys.argv[0]} {GIT_HOOK_PREFIX}{hook_name}'
    )

    with TempEnv(PATH="test"):
        assert create_hook_template(hook_name) == script_expect


def test_installed_hook_extractor(tmp_path: Path) -> None:
    # create some hooks
    hook_path = tmp_path / "hooks"
    hook_path.mkdir()

    # invalid hook 1
    hook1 = hook_path / "pre-commit.sample"
    hook1.write_text("#!/bin/bash\n# invalid")

    # invalid hook 2: a directory
    hook2 = hook_path / "commit-msg"
    hook2.mkdir()

    # valid hook
    hook3 = hook_path / "pre-push"
    hook3.write_text("#!/bin/bash\n# valid")

    detected = detect_installed_hooks(tmp_path)

    assert detected == ["pre-push"]


def test_create_hook_list() -> None:
    tasks: Tasks = {
        "ls": parse_task("ls -la"),
        f"{GIT_HOOK_PREFIX}pre-commit": parse_task("echo it worked"),
    }

    hook_list = create_list_of_hooks(tasks)

    assert len(hook_list) == 1
    assert hook_list[0][0] == "pre-commit"
    assert hook_list[0][1] == create_hook_template("pre-commit")


def _create_hook_dir(git_dir: Path) -> None:
    hook_path = git_dir / "hooks"
    hook_path.mkdir()

    # invalid hook 1
    hook1 = hook_path / "pre-commit.sample"
    hook1.write_text("#!/bin/bash\n# invalid")

    # invalid hook 2: a directory
    hook2 = hook_path / "commit-msg"
    hook2.mkdir()

    # invalid hook: task installed but doesn't match
    hook3 = hook_path / "pre-commit"
    hook3.write_text("#!/bin/bash\n# valid")

    hook4 = hook_path / "pre-rebase"
    hook4.write_text(create_hook_template("pre-rebase"))


def test_check_hooks_installed_notasks(tmp_path: Path) -> None:
    # create some hooks
    _create_hook_dir(tmp_path)

    # and create some tasks
    tasks: Tasks = {
        "ls": parse_task("ls -la"),
    }

    assert validate_installed_hooks(tmp_path, tasks)


def test_check_hooks_installed_wronglength(tmp_path: Path) -> None:
    # create some hooks
    _create_hook_dir(tmp_path)

    # and create some tasks
    tasks: Tasks = {
        "ls": parse_task("ls -la"),
        f"{GIT_HOOK_PREFIX}pre-commit": parse_task("echo it worked"),
    }

    assert not validate_installed_hooks(tmp_path, tasks)


def test_check_hooks_installed_wrongnames(tmp_path: Path) -> None:
    # create some hooks
    _create_hook_dir(tmp_path)

    # and create some tasks
    tasks: Tasks = {
        "ls": parse_task("ls -la"),
        f"{GIT_HOOK_PREFIX}pre-commit": parse_task("echo it worked"),
        f"{GIT_HOOK_PREFIX}post-update": parse_task("echo hello world"),
    }

    assert not validate_installed_hooks(tmp_path, tasks)


def test_check_hooks_installed_wrongbodies(tmp_path: Path) -> None:
    # create some hooks
    _create_hook_dir(tmp_path)

    # and create some tasks
    tasks: Tasks = {
        "ls": parse_task("ls -la"),
        f"{GIT_HOOK_PREFIX}pre-commit": parse_task("echo it worked"),
        f"{GIT_HOOK_PREFIX}pre-rebase": parse_task("echo hello world"),
    }

    assert not validate_installed_hooks(tmp_path, tasks)


def test_check_hooks_installed_all_ok(tmp_path: Path) -> None:
    # create some hooks
    _create_hook_dir(tmp_path)

    # overwrite the pre-commit hook to be correct
    (tmp_path / "hooks" / "pre-commit").write_text(create_hook_template("pre-commit"))

    # and create some tasks
    tasks: Tasks = {
        "ls": parse_task("ls -la"),
        f"{GIT_HOOK_PREFIX}pre-commit": parse_task("echo it worked"),
        f"{GIT_HOOK_PREFIX}pre-rebase": parse_task("echo hello world"),
    }

    assert validate_installed_hooks(tmp_path, tasks)


def test_force_install_hooks(tmp_path: Path) -> None:
    # create some hooks
    _create_hook_dir(tmp_path)

    # and create some tasks
    tasks: Tasks = {
        "ls": parse_task("ls -la"),
        f"{GIT_HOOK_PREFIX}pre-commit": parse_task("echo it worked"),
        f"{GIT_HOOK_PREFIX}pre-rebase": parse_task("echo hello world"),
    }

    # not valid to start with...
    assert not validate_installed_hooks(tmp_path, tasks)

    # ...do the installation...
    force_install_hooks(tmp_path, tasks)

    # ...and it should be valid now
    assert validate_installed_hooks(tmp_path, tasks)
