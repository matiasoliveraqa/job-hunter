import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.updater import (
    check_and_apply_updates,
    get_current_branch,
    get_diff_files,
    get_npm_executable,
    get_upstream_branch,
    has_local_uncommitted_changes,
    is_git_available,
    is_git_repo,
)


def test_is_git_available():
    assert is_git_available() is True


def test_is_git_repo(tmp_path):
    root = Path(__file__).resolve().parent.parent
    assert is_git_repo(root) is True
    assert is_git_repo(tmp_path) is False


def test_get_current_branch(tmp_path):
    root = Path(__file__).resolve().parent.parent
    branch = get_current_branch(root)
    assert branch is None or isinstance(branch, str)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="feature/my-branch\n")
        assert get_current_branch(tmp_path) == "feature/my-branch"

        mock_run.return_value = MagicMock(returncode=0, stdout="HEAD\n")
        with patch.dict("os.environ", {}, clear=True):
            assert get_current_branch(tmp_path) is None
        with patch.dict("os.environ", {"GITHUB_HEAD_REF": "feature/dynamic-location"}):
            assert get_current_branch(tmp_path) == "feature/dynamic-location"



def test_get_npm_executable_platform():
    with patch("sys.platform", "win32"), patch("shutil.which", return_value="C:\\npm.cmd"):
        assert get_npm_executable() == "C:\\npm.cmd"

    with patch("sys.platform", "darwin"), patch("shutil.which", return_value="/usr/local/bin/npm"):
        assert get_npm_executable() == "/usr/local/bin/npm"

    with patch("sys.platform", "linux"), patch("shutil.which", return_value="/usr/bin/npm"):
        assert get_npm_executable() == "/usr/bin/npm"


def test_check_and_apply_updates_non_git_repo(tmp_path):
    assert check_and_apply_updates(root=tmp_path) is False


def test_check_and_apply_updates_no_upstream(tmp_path):
    with patch("src.updater.is_git_available", return_value=True), \
         patch("src.updater.is_git_repo", return_value=True), \
         patch("src.updater.get_current_branch", return_value="feature/test"), \
         patch("src.updater.get_upstream_branch", return_value=None):
        assert check_and_apply_updates(root=tmp_path) is False


def test_check_and_apply_updates_uncommitted_changes(tmp_path):
    with patch("src.updater.is_git_available", return_value=True), \
         patch("src.updater.is_git_repo", return_value=True), \
         patch("src.updater.get_current_branch", return_value="main"), \
         patch("src.updater.get_upstream_branch", return_value="origin/main"), \
         patch("src.updater.has_local_uncommitted_changes", return_value=True):
        assert check_and_apply_updates(root=tmp_path) is False


def test_check_and_apply_updates_already_up_to_date(tmp_path):
    def fake_subprocess_run(cmd, **kwargs):
        if cmd == ["git", "rev-parse", "HEAD"]:
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = "abc1234\n"
            return mock
        if cmd == ["git", "pull", "--ff-only"]:
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = "Already up to date.\n"
            return mock
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = ""
        return mock

    with patch("src.updater.is_git_available", return_value=True), \
         patch("src.updater.is_git_repo", return_value=True), \
         patch("src.updater.get_current_branch", return_value="main"), \
         patch("src.updater.get_upstream_branch", return_value="origin/main"), \
         patch("src.updater.has_local_uncommitted_changes", return_value=False), \
         patch("subprocess.run", side_effect=fake_subprocess_run):
        assert check_and_apply_updates(root=tmp_path) is False


def test_check_and_apply_updates_with_diff_rebuild(tmp_path):
    call_counts = {"head": 0, "pip": 0, "npm": 0}

    def fake_subprocess_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        if cmd == ["git", "rev-parse", "HEAD"]:
            call_counts["head"] += 1
            mock.stdout = "old_commit\n" if call_counts["head"] == 1 else "new_commit\n"
            return mock
        if cmd == ["git", "pull", "--ff-only"]:
            mock.stdout = "Fast-forwarding...\n"
            return mock
        if "pip" in cmd:
            call_counts["pip"] += 1
            return mock
        if "npm" in cmd or (isinstance(cmd, list) and cmd and "npm" in cmd[0]):
            call_counts["npm"] += 1
            return mock
        mock.stdout = ""
        return mock

    web_dir = tmp_path / "web"
    web_dir.mkdir(parents=True, exist_ok=True)

    with patch("src.updater.is_git_available", return_value=True), \
         patch("src.updater.is_git_repo", return_value=True), \
         patch("src.updater.get_current_branch", return_value="main"), \
         patch("src.updater.get_upstream_branch", return_value="origin/main"), \
         patch("src.updater.has_local_uncommitted_changes", return_value=False), \
         patch("src.updater.get_diff_files", return_value=["requirements.txt", "web/src/App.vue"]), \
         patch("subprocess.run", side_effect=fake_subprocess_run):
        result = check_and_apply_updates(root=tmp_path)
        assert result is True
        assert call_counts["pip"] == 1
        assert call_counts["npm"] == 1
