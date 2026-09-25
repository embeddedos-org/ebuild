# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""`ebuild build` must use ninja_command(), not a hardcoded python -m ninja.

ninja_command() prefers a ninja binary on PATH and falls back to the PyPI
module. ebuild test already uses it. ebuild build used to skip it, so a
system ninja install was not enough for the main command.
"""

import subprocess
import sys
import textwrap

import pytest
from click.testing import CliRunner

from ebuild.build.dispatch import ninja_command
from ebuild.cli.commands import cli


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Minimal target project so `ebuild build` takes the Ninja backend path."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.c").write_text("int main(void) { return 0; }\n")
    (tmp_path / "build.yaml").write_text(textwrap.dedent("""\
        project:
          name: demo
          version: "1.0.0"

        targets:
          - name: demo
            type: executable
            sources: ["src/main.c"]

        toolchain:
          compiler: gcc
          arch: x86_64
        """))
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestNinjaCommand:
    def test_prefers_ninja_on_path(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/ninja" if name == "ninja" else None)
        assert ninja_command() == ["/usr/bin/ninja"]

    def test_falls_back_to_the_python_module(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        assert ninja_command() == [sys.executable, "-m", "ninja"]


class TestBuildUsesNinjaCommand:
    def test_build_uses_the_path_binary_when_present(self, project, monkeypatch):
        """If this still started with sys.executable, build is on the old argv."""
        captured = {}

        def fake_run(cmd, *args, **kwargs):
            captured["cmd"] = list(cmd)
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr("ebuild.cli.commands.subprocess.run", fake_run)
        monkeypatch.setattr(
            "shutil.which",
            lambda name: "/opt/ninja" if name == "ninja" else None,
        )

        result = CliRunner().invoke(cli, ["build"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        cmd = captured["cmd"]
        assert cmd[0] == "/opt/ninja"
        assert "-f" in cmd
        assert str(project / "_build" / "build.ninja") in cmd

    def test_build_falls_back_to_the_module_when_path_is_empty(self, project, monkeypatch):
        captured = {}

        def fake_run(cmd, *args, **kwargs):
            captured["cmd"] = list(cmd)
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr("ebuild.cli.commands.subprocess.run", fake_run)
        monkeypatch.setattr("shutil.which", lambda name: None)

        result = CliRunner().invoke(cli, ["build"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        cmd = captured["cmd"]
        assert cmd[:3] == [sys.executable, "-m", "ninja"]
        assert "-f" in cmd
