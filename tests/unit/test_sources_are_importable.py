# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 EoS Contributors
"""Every shipped Python file must parse, and the CLI must import.

Python does not parse a module until something imports it, so a syntax error
can sit on master indefinitely — reachable only when a developer runs the
command that touches it. That is what happened to ``ebuild/build/dispatch.py``,
which carried two consecutive ``else:`` blocks and made ``ebuild build`` fail
with a SyntaxError for every user, on the first build of a new project.

Unit tests that mock the build layer would not have caught it. These tests
compile the files instead of trusting that some other test imported them.
"""

from __future__ import annotations

import ast
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "ebuild"


def _python_sources() -> list[Path]:
    return sorted(
        p for p in PACKAGE_ROOT.rglob("*.py")
        if "__pycache__" not in p.parts
    )


def test_package_root_exists() -> None:
    assert PACKAGE_ROOT.is_dir(), f"{PACKAGE_ROOT} not found"
    assert _python_sources(), "no Python sources discovered — the glob is wrong"


@pytest.mark.parametrize(
    "source", _python_sources(), ids=lambda p: str(p.relative_to(PACKAGE_ROOT))
)
def test_source_parses(source: Path) -> None:
    """Parse every file. A SyntaxError here is a broken command for a user."""
    text = source.read_text(encoding="utf-8")
    try:
        ast.parse(text, filename=str(source))
    except SyntaxError as exc:
        rel = source.relative_to(REPO_ROOT)
        pytest.fail(f"{rel}:{exc.lineno}: {exc.msg}")


def test_cli_module_imports() -> None:
    """The CLI must import cleanly, including its lazy command modules.

    Skipped where the runtime dependencies are absent — this test is about the
    source being valid, not about the environment being provisioned.

    Importing ebuild.cli.commands alone is not enough: several commands import
    their implementation inside the function body, which is exactly where the
    dispatch.py breakage hid.
    """
    pytest.importorskip("click", reason="ebuild CLI runtime dependency not installed")

    for module in (
        "ebuild.cli.commands",
        "ebuild.build.dispatch",
        "ebuild.deps.manager",
    ):
        importlib.import_module(module)


def test_cli_help_runs() -> None:
    """`python -m ebuild --help` must exit 0.

    The end-to-end check: if this fails, the tool does not start at all.
    """
    pytest.importorskip("click", reason="ebuild CLI runtime dependency not installed")

    result = subprocess.run(
        [sys.executable, "-m", "ebuild", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"`python -m ebuild --help` exited {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "Usage:" in result.stdout


@pytest.mark.parametrize("command", ["setup", "new", "configure", "build", "flash"])
def test_mvp_commands_expose_help(command: str) -> None:
    """Each command named in the MVP developer walk must at least start.

    `--help` forces click to construct the command and import whatever it
    declares at module scope, so a broken command surfaces here rather than in
    front of a new developer.
    """
    pytest.importorskip("click", reason="ebuild CLI runtime dependency not installed")

    result = subprocess.run(
        [sys.executable, "-m", "ebuild", command, "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"`ebuild {command} --help` exited {result.returncode}\n{result.stderr}"
    )


def test_default_repo_branch_exists_upstream() -> None:
    """The cached-repo default branch must actually exist on the remote.

    `ebuild setup` is the first command a new developer runs. It cloned
    branch "main" while both repositories default to "master", so setup failed
    for everyone, every time. A hardcoded branch name is a fact about a remote,
    and facts about remotes go stale.
    """
    from ebuild.deps import DEFAULT_CONFIG

    for name, cfg in DEFAULT_CONFIG["repos"].items():
        url, branch = cfg["url"], cfg["branch"]
        result = subprocess.run(
            ["git", "ls-remote", "--heads", url, branch],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            pytest.skip(f"cannot reach {url}: {result.stderr.strip()}")
        assert result.stdout.strip(), (
            f"default branch '{branch}' for repo '{name}' does not exist at {url}. "
            "ebuild setup will fail for every new developer."
        )
