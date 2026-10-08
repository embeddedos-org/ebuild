"""`ebuild setup` must say when it reused an existing clone (issue #180).

DepsManager.setup() leaves an existing clone alone on purpose, so the CLI
is the only place that can tell the user the checkout was not updated.
"""

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from ebuild.cli.commands import cli


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _make_clone(path: Path) -> str:
    path.mkdir(parents=True)
    _git(path, "init", "-q")
    (path / "README").write_text("x\n", encoding="utf-8")
    _git(path, "add", "README")
    _git(path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    return _git(path, "log", "-1", "--format=%h %cs")


class _FakeManager:
    """Stands in for DepsManager: records calls, never touches the network."""

    cache_root: Path = Path()

    def __init__(self) -> None:
        self.cache_dir = self.cache_root

    def setup(self, name, url=None, branch=None, path=None):
        if path:
            return Path(path)
        dest = self.cache_dir / name
        dest.mkdir(parents=True, exist_ok=True)  # a "fresh clone"
        return dest


@pytest.fixture
def fake_manager(tmp_path, monkeypatch):
    import ebuild.deps.manager as manager

    _FakeManager.cache_root = tmp_path / "repos"
    monkeypatch.setattr(manager, "DepsManager", _FakeManager)
    return _FakeManager.cache_root


def test_fresh_clone_has_no_stale_warning(fake_manager):
    result = CliRunner().invoke(cli, ["setup"])
    assert result.exit_code == 0, result.output
    assert "already cloned" not in result.output
    assert "Setup complete" in result.output


def test_existing_clone_names_commit_and_update_command(fake_manager):
    eos_head = _make_clone(fake_manager / "eos")
    result = CliRunner().invoke(cli, ["setup"])
    assert result.exit_code == 0, result.output
    assert f"eos was already cloned (at {eos_head}); setup does not pull." in result.output
    assert "ebuild repos update" in result.output
    # eboot was freshly "cloned" in this run, so it gets no warning.
    assert "eboot was already cloned" not in result.output


def test_existing_non_git_dir_still_warns(fake_manager):
    (fake_manager / "eboot").mkdir(parents=True)
    result = CliRunner().invoke(cli, ["setup"])
    assert result.exit_code == 0, result.output
    assert "eboot was already cloned (at an unknown commit)" in result.output


def test_linked_path_is_not_reported_as_cached(fake_manager, tmp_path):
    _make_clone(fake_manager / "eos")
    local = tmp_path / "my-eos"
    local.mkdir()
    result = CliRunner().invoke(cli, ["setup", "--eos-path", str(local)])
    assert result.exit_code == 0, result.output
    assert "eos was already cloned" not in result.output
