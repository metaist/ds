"""Test main entry point."""

# std
from pathlib import Path
from shlex import split
import tempfile

# lib
from _pytest.capture import CaptureFixture
import pytest

# pkg
from ds import __version__
from ds import main
from ds import pushd
from ds.env import TempEnv

PATH_WK = Path("examples") / "workspace"


def test_help() -> None:
    """-h and --help show help"""
    main(split("ds -h"))
    main(split("ds --help"))


def test_version(capsys: CaptureFixture[str]) -> None:
    """--version shows the version"""
    main(split("ds --version"))

    captured = capsys.readouterr()
    assert captured.out.startswith(__version__)


def test_self_update() -> None:
    """--self-update in non-cosmo build shows error"""
    main(split("ds --self-update"))


def test_list() -> None:
    """--list shows available tasks"""
    for arg in ["", "-l", "--list"]:
        main(split(f"ds {arg}"))


def test_pre_post() -> None:
    """--pre / --post run pre/post tasks"""
    main(split("ds --pre --post -f examples/formats/pyproject-pdm.toml echo"))


def test_parallel() -> None:
    """--parallel"""
    main(split("ds --no-config --parallel 'echo hello' 'echo world'"))


def test_env_file() -> None:
    """--env-file loads an env file"""
    main(split("ds --env-file examples/formats/.env 'echo $IN_DOT_ENV'"))

    # non-existent .env
    with pytest.raises(SystemExit):
        main(split("ds --env-file .env 'echo $IN_DOT_ENV'"))


def test_echo() -> None:
    """Just run a command from the top-level."""
    main(split("ds 'echo hello'"))


def test_no_config() -> None:
    """Test disabling config."""
    main(split("ds --no-config 'echo hello'"))

    with pytest.raises(SystemExit):
        main(split("ds --no-config --list"))

    with pytest.raises(SystemExit):
        main(split("ds --no-config -w* test"))


def test_no_project() -> None:
    """Run without project."""
    main(split("ds --no-project 'echo hello'"))


def test_project_in_venv() -> None:
    """Run within an active/inactive .venv."""
    with TempEnv(VIRTUAL_ENV=str(Path(".venv").resolve())):
        main(split("ds 'echo hello'"))

    with TempEnv(VIRTUAL_ENV=None):
        main(split("ds 'echo hello'"))

    main(split("ds --cwd / 'echo hello'"))


def test_multiple_results() -> None:
    """Try finding the same result multiple times."""
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        v1 = root / ".venv"
        v1.mkdir(parents=True, exist_ok=True)
        (v1 / "pyvenv.cfg").write_text("")

        v2 = root / "nested" / ".venv"
        v2.mkdir(parents=True, exist_ok=True)
        (v2 / "pyvenv.cfg").write_text("")

        v3 = root / "node_modules" / ".bin"
        v3.mkdir(parents=True, exist_ok=True)

        with TempEnv(DS_INTERNAL__FILE=None, VIRTUAL_ENV=None):
            with pushd(root / "nested"):
                main(split("ds --debug --no-config 'echo hello'"))


def test_good_loop() -> None:
    """Run some loop-looking tasks."""
    main(split("ds -f examples/misc/loop-good.toml ls"))  # ok
    main(split("ds -f examples/misc/loop-good.toml df"))  # ok
    main(split("ds -f examples/misc/loop-good.toml ls2"))  # ok


def test_bad_loop() -> None:
    """Try to run bad loops."""
    with pytest.raises(SystemExit) as e:
        main(split("ds -f examples/misc/loop-bad.toml bad"))
    assert e.value.code == 1


def test_no_task() -> None:
    """Try to run a missing task."""
    with pytest.raises(SystemExit) as e:
        main(split("ds _does_not_exist"))
    assert e.value.code == 127  # command not found


def test_bad_cwd() -> None:
    """Try to point to a non-existent directory."""
    with pytest.raises(SystemExit) as e:
        main(split("ds --cwd /does-not-exist"))
    assert e.value.code == 1


def test_bad_config() -> None:
    """Try to load a non-existent config file."""
    with pytest.raises(SystemExit) as e:
        main(split("ds -f /does-not-exist.toml"))
    assert e.value.code == 1


def test_missing_config() -> None:
    """Fail to find a config file."""
    with pushd("/"):
        with pytest.raises(SystemExit):
            main(split("ds tests"))


def test_stay_in_file() -> None:
    """Use the same file when calling `ds` in a task."""
    main(split("ds --debug -f examples/formats/package.json inside"))
    main(split("ds -f examples/formats/package.json outside"))


def test_get_file_from_env() -> None:
    """Get config file from environment variable."""
    path = str(Path("examples") / "formats" / "package.json")
    with TempEnv(DS_INTERNAL__FILE=path):
        main(split("ds"))

    with TempEnv(DS_INTERNAL__FILE=path):
        main(split("ds --debug"))

    with TempEnv(DS_INTERNAL__FILE=None):
        main(split("ds"))


def test_run_workspace() -> None:
    """Run a workspace."""
    with TempEnv(DS_INTERNAL__FILE=None):
        with pushd(PATH_WK):
            main(split("ds --debug -w*"))


def test_run_some_workspaces() -> None:
    """Run in only one workspace."""
    with TempEnv(DS_INTERNAL__FILE=None):
        with pushd(PATH_WK):
            main(split("ds -w '*/a'"))


def test_workspace_same_name() -> None:
    """Run files with same name."""
    with TempEnv(DS_INTERNAL__FILE=None):
        with pushd(PATH_WK):
            main(split("ds --file 'package.json' -w*"))


def _create_git_dir(tmp_dir: Path) -> None:
    (tmp_dir / ".git" / "hooks").mkdir(parents=True)


def test_sync_git_hooks_no_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = (Path("examples") / "misc" / "no_defined_hooks.toml").absolute()

    # _create_git_dir(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("")

    with TempEnv(DS_INTERNAL__FILE=str(config_path)):
        main(split("ds --sync-git-hooks"))


def test_sync_git_hooks_no_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = (Path("examples") / "misc" / "no_defined_hooks.toml").absolute()

    monkeypatch.chdir(tmp_path)
    _create_git_dir(tmp_path)
    (tmp_path / ".env").write_text("")

    with TempEnv(DS_INTERNAL__FILE=str(config_path)):
        main(split("ds --sync-git-hooks"))


def test_sync_git_hooks_bad_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = (Path("examples") / "misc" / "defined_hooks.toml").absolute()

    monkeypatch.chdir(tmp_path)
    _create_git_dir(tmp_path)
    (tmp_path / ".env").write_text("")

    with TempEnv(DS_INTERNAL__FILE=str(config_path)):
        main(split("ds"))


def test_sync_git_hooks_install_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = (Path("examples") / "misc" / "defined_hooks.toml").absolute()

    monkeypatch.chdir(tmp_path)
    _create_git_dir(tmp_path)
    (tmp_path / ".env").write_text("")

    assert not (tmp_path / ".git" / "hooks" / "pre-commit").exists()

    with TempEnv(DS_INTERNAL__FILE=str(config_path)):
        main(split("ds --sync-git-hooks"))

        assert (tmp_path / ".git" / "hooks" / "pre-commit").exists()
