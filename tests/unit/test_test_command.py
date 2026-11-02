# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for `ebuild test` (golden-path test-runner step, #83).

One command, no duplicates: native ebuild ``test`` targets first, then the
project's own runner -- auto-detected from the layout (ctest, pytest, cargo
test, meson test, make test) or chosen explicitly with --runner. A missing
build.yaml is not an error: detection falls back to the project layout so
`ebuild test` works in any project directory. Args after `--` pass through
to the runner.
"""

import subprocess
import sys

import pytest
from click.testing import CliRunner

from ebuild.cli.commands import _resolve_test_runner, _runner_argv, cli


def invoke(*args):
    return CliRunner().invoke(cli, ["test", *args])


class TestTestRegistered:
    def test_test_is_a_command(self):
        assert "test" in cli.commands

    def test_test_registered_once(self):
        assert list(cli.commands).count("test") == 1


class TestDetection:
    def test_nothing_detected_returns_none(self, tmp_path):
        assert _resolve_test_runner(tmp_path, tmp_path / "build", None) is None

    def test_ctest_beats_pytest(self, tmp_path):
        build = tmp_path / "build"
        build.mkdir()
        (build / "CTestTestfile.cmake").write_text("# ctest\n")
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        name, _, _ = _resolve_test_runner(tmp_path, build, None)
        assert name == "ctest"

    def test_pytest_marker_detected(self, tmp_path):
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        name, argv, cwd = _resolve_test_runner(tmp_path, tmp_path / "build", None)
        assert name == "pytest"
        assert argv[:3] == [sys.executable, "-m", "pytest"]
        assert cwd == tmp_path

    def test_tests_dir_detected(self, tmp_path):
        (tmp_path / "tests").mkdir()
        name, _, _ = _resolve_test_runner(tmp_path, tmp_path / "build", None)
        assert name == "pytest"

    def test_cargo_detected(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]\n")
        name, argv, _ = _resolve_test_runner(tmp_path, tmp_path / "build", None)
        assert name == "cargo test"
        assert argv[:2] == ["cargo", "test"]

    def test_make_test_target_detected(self, tmp_path):
        (tmp_path / "Makefile").write_text("test:\n\ttrue\n")
        name, _, _ = _resolve_test_runner(tmp_path, tmp_path / "build", None)
        assert name == "make test"

    def test_filter_reaches_pytest(self, tmp_path):
        (tmp_path / "tests").mkdir()
        _, argv, _ = _resolve_test_runner(tmp_path, tmp_path / "build", "net")
        assert argv[-2:] == ["-k", "net"]


class TestExplicitRunner:
    @pytest.mark.parametrize(
        "runner,first",
        [
            ("pytest", sys.executable),
            ("ctest", "ctest"),
            ("cargo", "cargo"),
            ("meson", "meson"),
            ("make", "make"),
        ],
    )
    def test_runner_argv_first_token(self, tmp_path, runner, first):
        _, argv, _ = _runner_argv(runner, tmp_path, tmp_path / "build", None)
        assert argv[0] == first


class FakeCompleted:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


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
        assert result.exit_code == 1
        assert "No test runner found" in result.output

    def test_no_build_yaml_still_detects(self, tmp_path, monkeypatch, run_spy):
        # No build.yaml at all: layout detection must still kick in.
        assert not (tmp_path / "build.yaml").exists()
        (tmp_path / "tests").mkdir()
        monkeypatch.chdir(tmp_path)
        result = invoke()
        assert result.exit_code == 0
        assert run_spy[0][0:3] == [sys.executable, "-m", "pytest"]

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
        result = invoke("--build-dir", "build")
        assert result.exit_code == 0
        assert run_spy[0][:2] == ["ctest", "--output-on-failure"]

    def test_explicit_runner_ctest(self, tmp_path, monkeypatch, run_spy):
        monkeypatch.chdir(tmp_path)
        result = invoke("--runner", "ctest")
        assert result.exit_code == 0
        assert run_spy[0][0] == "ctest"

    def test_filter_option(self, tmp_path, monkeypatch, run_spy):
        (tmp_path / "tests").mkdir()
        monkeypatch.chdir(tmp_path)
        result = invoke("--filter", "net")
        assert result.exit_code == 0
        assert run_spy[0][-2:] == ["-k", "net"]

    def test_failing_runner_propagates_exit_code(self, tmp_path, monkeypatch):
        (tmp_path / "tests").mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            subprocess, "run", lambda cmd, **kw: FakeCompleted(3, stdout="x")
        )
        result = invoke()
        assert result.exit_code == 3
        assert "Tests failed" in result.output

    def test_missing_runner_binary_is_clear_error(self, tmp_path, monkeypatch):
        (tmp_path / "tests").mkdir()
        monkeypatch.chdir(tmp_path)

        def boom(cmd, **kw):
            raise FileNotFoundError("nope")

        monkeypatch.setattr(subprocess, "run", boom)
        result = invoke("--runner", "cargo")
        assert result.exit_code == 1
        assert "not installed or not on PATH" in result.output
