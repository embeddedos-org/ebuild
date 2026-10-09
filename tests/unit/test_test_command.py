# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for `ebuild test` (golden-path test-runner step, #83).

Auto-detection order: ctest (CTestTestfile.cmake in the build dir) first,
then pytest config markers, then a tests/ or test/ directory. With nothing
detected the command exits 2 fail-closed rather than pretending to test.
"""

import subprocess
import sys

import pytest
from click.testing import CliRunner

from ebuild.cli.commands import _detect_test_runner, cli


def invoke(*args):
    return CliRunner().invoke(cli, ["test", *args])


class TestTestRegistered:
    def test_test_is_a_command(self):
        assert "test" in cli.commands


class TestDetection:
    def test_nothing_detected_returns_none(self, tmp_path):
        assert _detect_test_runner("auto", tmp_path / "build", tmp_path) is None

    def test_ctest_beats_pytest(self, tmp_path):
        build = tmp_path / "build"
        build.mkdir()
        (build / "CTestTestfile.cmake").write_text("# ctest\n")
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        assert _detect_test_runner("auto", build, tmp_path) == "ctest"

    def test_pytest_marker_detected(self, tmp_path):
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        assert _detect_test_runner("auto", tmp_path / "build", tmp_path) == "pytest"

    def test_tests_dir_detected(self, tmp_path):
        (tmp_path / "tests").mkdir()
        assert _detect_test_runner("auto", tmp_path / "build", tmp_path) == "pytest"

    def test_explicit_runner_skips_detection(self, tmp_path):
        assert _detect_test_runner("pytest", tmp_path / "build", tmp_path) == "pytest"
        assert _detect_test_runner("ctest", tmp_path / "build", tmp_path) == "ctest"


class FakeCompleted:
    def __init__(self, returncode):
        self.returncode = returncode


@pytest.fixture
def run_spy(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return FakeCompleted(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


class TestTestCommand:
    def test_no_runner_is_fail_closed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = invoke()
        assert result.exit_code == 2
        assert "No test runner detected" in result.output

    def test_pytest_detected_and_invoked(self, tmp_path, monkeypatch, run_spy):
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        monkeypatch.chdir(tmp_path)
        result = invoke()
        assert result.exit_code == 0
        assert run_spy[0][0:3] == [sys.executable, "-m", "pytest"]

    def test_runner_args_passed_through(self, tmp_path, monkeypatch, run_spy):
        (tmp_path / "tests").mkdir()
        monkeypatch.chdir(tmp_path)
        result = invoke("--", "-k", "network", "-x")
        assert result.exit_code == 0
        assert run_spy[0][-3:] == ["-k", "network", "-x"]

    def test_ctest_detected(self, tmp_path, monkeypatch, run_spy):
        build = tmp_path / "build"
        build.mkdir()
        (build / "CTestTestfile.cmake").write_text("# ctest\n")
        monkeypatch.chdir(tmp_path)
        result = invoke()
        assert result.exit_code == 0
        assert run_spy[0][0:3] == ["ctest", "--test-dir", "build"]

    def test_explicit_runner_ctest(self, tmp_path, monkeypatch, run_spy):
        monkeypatch.chdir(tmp_path)
        result = invoke("--runner", "ctest")
        assert result.exit_code == 0
        assert run_spy[0][0] == "ctest"

    def test_failing_runner_propagates_exit_code(self, tmp_path, monkeypatch):
        (tmp_path / "tests").mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            subprocess, "run", lambda cmd, **kw: FakeCompleted(3)
        )
        result = invoke()
        assert result.exit_code == 3
        assert "Tests failed" in result.output
