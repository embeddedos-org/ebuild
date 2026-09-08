# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""`ebuild test` must not report success for a project with no tests.

ctest exits 0 when it finds nothing to run. A CMakeLists.txt with
`enable_testing()` and no `add_test()` still produces a CTestTestfile.cmake, so
`_resolve_test_runner()` finds ctest, ctest prints "No tests were found!!!",
exits 0, and trusting that exit status reports a green suite for a project
containing no tests at all.

Measured on master before this change, against a project with a configured
build tree and zero registered tests:

    $ ctest --test-dir _build
    No tests were found!!!
    ctest exit=0

    $ ebuild test
    [ok] All tests passed.
    exit=0

That is worse than having no test command, because it actively reassures.
"""

import sys

import yaml
from click.testing import CliRunner

from ebuild.cli.commands import _parse_test_counts, _ran_no_tests, cli


class TestEmptyRunDetection:
    def test_ctest_no_tests_marker(self):
        assert _ran_no_tests("ctest", "No tests were found!!!") is True

    def test_meson_no_tests_marker(self):
        assert _ran_no_tests("meson test", "No tests defined.") is True

    def test_cargo_zero_tests_marker(self):
        assert _ran_no_tests("cargo test", "running 0 tests") is True

    def test_zero_totals_are_caught_without_a_marker(self):
        # A runner that prints a well-formed summary adding up to nothing is
        # the same situation by a different route.
        assert _ran_no_tests("ctest",
                             "100% tests passed, 0 tests failed out of 0") is True

    def test_a_real_run_is_not_flagged(self):
        assert _ran_no_tests("ctest",
                             "100% tests passed, 0 tests failed out of 17") is False

    def test_a_failing_run_is_not_flagged(self):
        # Failures are already handled by the exit status; this must not
        # reclassify them as "nothing ran".
        assert _ran_no_tests("ctest",
                             "50% tests passed, 3 tests failed out of 6") is False

    def test_make_has_no_marker_and_is_not_flagged(self):
        assert _ran_no_tests("make test", "anything at all") is False


class TestCountParsing:
    """Counts come from the runner's own summary, never from the exit status."""

    def test_ctest_summary(self):
        assert _parse_test_counts(
            "ctest", "100% tests passed, 0 tests failed out of 17") == (17, 0)

    def test_ctest_summary_with_failures(self):
        assert _parse_test_counts(
            "ctest", "50% tests passed, 3 tests failed out of 6") == (3, 3)

    def test_cargo_summary(self):
        assert _parse_test_counts(
            "cargo test", "test result: ok. 12 passed; 0 failed; 0 ignored") == (12, 0)

    def test_meson_summary(self):
        out = "Ok:                 12\nExpected Fail:      0\nFail:               2\n"
        assert _parse_test_counts("meson test", out) == (12, 2)

    def test_make_has_no_standard_summary(self):
        # Rather than invent a format for make, the counts stay unknown and the
        # exit status carries the verdict. A made-up number would be worse than
        # none.
        assert _parse_test_counts("make test", "anything at all") is None

    def test_unrecognised_output_yields_no_counts(self):
        assert _parse_test_counts("ctest", "something else entirely") is None


class TestTheVerdictReachesTheDeveloper:
    """The detection above is only worth having if `ebuild test` acts on it.
    These drive the command itself, so a runner that ran nothing cannot be
    reported as a pass by a code path that never consulted `_ran_no_tests`.

    The runner is stubbed and answered by `sys.executable`, not by ctest:
    the point under test is what ebuild concludes from a runner's output, and
    the three CI platforms do not agree on which runners are installed.
    """

    def _project(self, tmp_path):
        (tmp_path / "build.yaml").write_text(yaml.safe_dump({
            "project": {"name": "node", "version": "1.0.0"},
            "workspace": {"backend": "ninja", "build_dir": "build"},
            "toolchain": {"target": "host"},
            "targets": [{"name": "node", "type": "executable",
                         "sources": ["src/main.c"]}],
        }), encoding="utf-8")
        return tmp_path

    def _run(self, tmp_path, monkeypatch, *, name, output, exit_code=0):
        """Invoke `ebuild test` against a runner that prints `output`.

        The output is passed through a file rather than inlined into `-c`.
        `ebuild test` echoes the argv it is about to run, so an inlined
        string appears in the captured output whether or not the command
        echoes what the runner printed -- which is the thing being asserted.
        """
        monkeypatch.chdir(self._project(tmp_path))
        canned = tmp_path / "runner_stdout.txt"
        canned.write_text(output, encoding="utf-8")
        argv = [sys.executable, "-c",
                "import sys; sys.stdout.write("
                "open(sys.argv[1], encoding='utf-8').read()); "
                f"sys.exit({exit_code!r})",
                str(canned)]
        monkeypatch.setattr(
            "ebuild.cli.commands._resolve_test_runner",
            lambda *_a, **_kw: (name, argv, tmp_path))
        return CliRunner().invoke(cli, ["test"])

    def test_a_run_that_found_nothing_fails_the_command(self, tmp_path, monkeypatch):
        """ctest exits 0 when it finds nothing to run. Trusting that status
        reports a green suite for a project containing no tests at all."""
        result = self._run(tmp_path, monkeypatch,
                           name="ctest", output="No tests were found!!!\n")
        assert result.exit_code == 1
        assert "without running a single test" in result.output
        assert "All tests passed" not in result.output

    def test_a_real_run_reports_the_runner_s_own_counts(self, tmp_path, monkeypatch):
        result = self._run(
            tmp_path, monkeypatch, name="ctest",
            output="100% tests passed, 0 tests failed out of 17\n")
        assert result.exit_code == 0
        assert "17 passed" in result.output

    def test_a_runner_with_no_summary_still_gets_a_verdict(self, tmp_path, monkeypatch):
        """`make test` prints no standard summary. The exit status carries the
        verdict; inventing a count would be worse than reporting none."""
        result = self._run(tmp_path, monkeypatch,
                           name="make test", output="cc -o t t.c\n./t\n")
        assert result.exit_code == 0
        assert "All tests passed." in result.output
        assert "passed," not in result.output       # no invented numbers

    def test_the_runner_s_output_is_echoed(self, tmp_path, monkeypatch):
        """It is captured so the empty-run check can read it; capturing it
        without echoing it would take away the failure detail the developer
        needs."""
        result = self._run(
            tmp_path, monkeypatch, name="ctest",
            output="1/2 Test #1: parses_a_header .... Passed\n"
                   "100% tests passed, 0 tests failed out of 2\n")
        assert "parses_a_header" in result.output

    def test_a_failing_run_exits_with_the_runner_s_status(self, tmp_path, monkeypatch):
        result = self._run(
            tmp_path, monkeypatch, name="ctest", exit_code=8,
            output="50% tests passed, 1 tests failed out of 2\n")
        assert result.exit_code == 8
        assert "Tests failed" in result.output

    def test_a_silent_runner_does_not_echo_a_blank_line(self, tmp_path, monkeypatch):
        """A runner can succeed without printing anything. Echoing an empty
        capture would put a stray blank line between the step and the
        verdict."""
        result = self._run(tmp_path, monkeypatch, name="make test", output="")
        assert result.exit_code == 0
        assert "All tests passed." in result.output
        assert "\n\n\n" not in result.output

    def test_a_runner_that_is_not_installed_says_so(self, tmp_path, monkeypatch):
        monkeypatch.chdir(self._project(tmp_path))
        monkeypatch.setattr(
            "ebuild.cli.commands._resolve_test_runner",
            lambda *_a, **_kw: ("ctest", ["definitely-not-a-real-tool"], tmp_path))
        result = CliRunner().invoke(cli, ["test"])
        assert result.exit_code == 1
        assert "not installed" in result.output

    def test_a_project_with_no_runner_at_all_is_refused(self, tmp_path, monkeypatch):
        """Not an error to have no tests -- an error to be told they passed."""
        monkeypatch.chdir(self._project(tmp_path))
        result = CliRunner().invoke(cli, ["test"])
        assert result.exit_code == 1
        assert "No test runner found" in result.output
