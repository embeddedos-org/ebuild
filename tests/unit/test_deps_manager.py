import subprocess
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


def test_default_config_branches_are_master():
    # Regression test for #81: DEFAULT_CONFIG once named "main" for eos and
    # eBoot, a branch neither repo has, so `ebuild setup` failed on every
    # first run. Every defaulted branch must be "master".
    from ebuild.deps import DEFAULT_CONFIG

    assert set(DEFAULT_CONFIG["repos"]) >= {"eos", "eboot"}
    for name, cfg in DEFAULT_CONFIG["repos"].items():
        assert cfg["branch"] == "master", f"{name}: {cfg['branch']!r}"
