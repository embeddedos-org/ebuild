import subprocess
from pathlib import Path
from unittest.mock import patch

from ebuild.deps.manager import DepsManager


def test_git_clone_without_branch_does_not_pass_branch(tmp_path):
    dest = tmp_path / "repo"

    with patch("ebuild.deps.manager.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        DepsManager._git_clone(
            "https://github.com/example/repo.git",
            dest,
            None,
            True,
        )

        command = mock_run.call_args[0][0]

        assert "--branch" not in command
        assert "master" not in command


def test_git_clone_with_branch_passes_branch(tmp_path):
    dest = tmp_path / "repo"

    with patch("ebuild.deps.manager.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        DepsManager._git_clone(
            "https://github.com/example/repo.git",
            dest,
            "develop",
            True,
        )

        command = mock_run.call_args[0][0]

        assert "--branch" in command
        assert "develop" in command
