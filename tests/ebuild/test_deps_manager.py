# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for DepsManager."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from ebuild.deps import DEFAULT_CONFIG
from ebuild.deps.manager import DepsManager, SIBLING_DIR_NAMES


@pytest.fixture
def isolated_deps(tmp_path, monkeypatch):
    """Keep tests away from the real ~/.ebuild directory."""
    home = tmp_path / "ebuild-home"
    repos = home / "repos"
    config = home / "config.yaml"

    monkeypatch.setattr(
        "ebuild.deps.manager.ensure_ebuild_home",
        lambda: home,
    )
    monkeypatch.setattr(
        "ebuild.deps.manager.EBUILD_CONFIG_PATH",
        config,
    )
    monkeypatch.setenv("EBUILD_REPOS_DIR", str(repos))
    monkeypatch.delenv("EBUILD_EOS_PATH", raising=False)
    monkeypatch.delenv("EBUILD_EBOOT_PATH", raising=False)

    home.mkdir()
    repos.mkdir()

    return tmp_path


def _case_sensitive_is_dir(self: Path) -> bool:
    """Treat directory names as case-sensitive, as Linux does."""
    try:
        names = {child.name for child in self.parent.iterdir()}
    except OSError:
        return False

    return self.name in names


def test_eboot_aliases_include_github_casing():
    """eBoot should be recognized as an eboot sibling."""
    assert SIBLING_DIR_NAMES["eboot"] == ("eboot", "eBoot")


def test_sibling_eboot_resolves_camel_case(
    isolated_deps,
    monkeypatch,
):
    """Resolve an eBoot sibling directory."""
    workspace = isolated_deps / "ws"
    project = workspace / "ebuild"
    camel = workspace / "eBoot"

    project.mkdir(parents=True)
    camel.mkdir()

    monkeypatch.setattr(
        Path,
        "is_dir",
        _case_sensitive_is_dir,
    )

    resolved = DepsManager().get_repo_path(
        "eboot",
        project_dir=project,
    )

    assert resolved is not None
    assert resolved.name == "eBoot"


def test_sibling_eboot_still_resolves_lowercase(
    isolated_deps,
    monkeypatch,
):
    """Resolve the lowercase eboot sibling directory."""
    workspace = isolated_deps / "ws"
    project = workspace / "ebuild"
    lower = workspace / "eboot"

    project.mkdir(parents=True)
    lower.mkdir()

    monkeypatch.setattr(
        Path,
        "is_dir",
        _case_sensitive_is_dir,
    )

    resolved = DepsManager().get_repo_path(
        "eboot",
        project_dir=project,
    )

    assert resolved is not None
    assert resolved.name == "eboot"


def test_sibling_eboot_missing_returns_none(
    isolated_deps,
    monkeypatch,
):
    """Return None when no eboot sibling exists."""
    workspace = isolated_deps / "ws"
    project = workspace / "ebuild"

    project.mkdir(parents=True)

    monkeypatch.setattr(
        Path,
        "is_dir",
        _case_sensitive_is_dir,
    )

    resolved = DepsManager().get_repo_path(
        "eboot",
        project_dir=project,
    )

    assert resolved is None


def test_setters_do_not_mutate_module_defaults(
    isolated_deps,
):
    """Config changes must not mutate DEFAULT_CONFIG."""
    manager = DepsManager()

    manager.set_branch("eos", "dev")
    manager.set_url(
        "eboot",
        "https://example.invalid/eboot.git",
    )

    assert DEFAULT_CONFIG["repos"]["eos"]["branch"] == "master"
    assert DEFAULT_CONFIG["repos"]["eboot"]["url"].endswith(
        "/eBoot.git"
    )


def test_setup_uses_remote_default_branch_when_unconfigured(
    isolated_deps,
    monkeypatch,
):
    """Do not pass --branch when no branch is configured."""
    manager = DepsManager()

    manager._config["repos"]["eos"] = {
        "url": "https://example.invalid/eos.git",
    }

    clone_result = Mock()
    clone_result.returncode = 0
    clone_result.stderr = ""

    mock_run = Mock(return_value=clone_result)

    monkeypatch.setattr(
        "ebuild.deps.manager.subprocess.run",
        mock_run,
    )

    destination = manager.setup(
        "eos",
        shallow=False,
    )

    assert destination == manager.cache_dir / "eos"
    mock_run.assert_called_once()

    clone_command = mock_run.call_args.args[0]

    assert clone_command[:2] == ["git", "clone"]
    assert "https://example.invalid/eos.git" in clone_command
    assert "--branch" not in clone_command
    assert "master" not in clone_command
