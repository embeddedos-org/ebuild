# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""`ebuild doctor` — environment diagnosis.

The MLP list asks for "one-command environment diagnosis". Without it, the
same class of problem surfaces three different ways: a missing cross toolchain
as a compiler-not-found partway through a build, a missing repo cache as
`eos/hal.h: No such file`, a missing `size` as a silently absent footprint.
None of those names the fix.

The behaviour that matters most is the exit code. A doctor that exits 1 on a
host-only machine — which legitimately has no cross toolchain — stops being
consulted.
"""

import json

from click.testing import CliRunner

from ebuild.cli.commands import cli
from ebuild.system import doctor as doc
from ebuild.system.doctor import (
    MISSING,
    OK,
    WARN,
    Check,
    exit_code,
    format_report,
    host_checks,
    toolchain_checks,
)


class TestExitCode:
    def test_a_clean_environment_passes(self):
        assert exit_code([Check("a", OK), Check("b", OK)]) == 0

    def test_a_missing_cross_toolchain_does_not_fail(self):
        """A host-only machine is not broken. If this returns 1, CI on every
        such machine goes red and the command gets ignored."""
        assert exit_code([Check("a", OK), Check("arm-none-eabi", WARN)]) == 0

    def test_something_that_stops_a_build_fails(self):
        assert exit_code([Check("ninja", MISSING)]) == 1

    def test_no_checks_is_not_a_failure(self):
        assert exit_code([]) == 0


class TestReport:
    def test_every_check_gets_a_line(self):
        checks = [Check("alpha", OK, "1.0"), Check("beta", MISSING, "gone", "fix it")]
        body = format_report(checks)
        assert "alpha" in body and "beta" in body

    def test_a_missing_check_names_its_fix(self):
        """Reporting that something is absent without saying what to do is
        the part that makes a diagnostic useless."""
        body = format_report([Check("ninja", MISSING, "not on PATH",
                                    "install ninja-build")])
        assert "install ninja-build" in body

    def test_a_clean_run_says_so_plainly(self):
        body = format_report([Check("ninja", OK, "1.11")])
        assert "No problems" in body

    def test_warnings_are_listed_apart_from_problems(self):
        """A warning is a capability the developer may not want, not a fault."""
        body = format_report([
            Check("ninja", OK, "1.11"),
            Check("arm-none-eabi", WARN, "not installed",
                  "install it to target stm32f4"),
        ])
        assert "No problems" in body
        assert "Optional, for other targets" in body
        assert "stm32f4" in body

    def test_names_are_column_aligned(self):
        body = format_report([Check("a", OK, "x"), Check("looooong", OK, "y")])
        first, second = body.splitlines()[:2]
        assert first.index("x") == second.index("y")


class TestChecks:
    def test_host_checks_cover_the_build_path(self):
        names = {c.name for c in host_checks()}
        assert {"python", "ninja", "host compiler", "git"} <= names

    def test_python_is_always_ok(self):
        """It is running the check."""
        python = next(c for c in host_checks() if c.name == "python")
        assert python.status == OK

    def test_a_missing_required_tool_is_a_problem(self, monkeypatch):
        monkeypatch.setattr(doc.shutil, "which", lambda _n: None)
        assert any(c.status == MISSING for c in host_checks())

    def test_size_absent_is_optional_not_a_problem(self, monkeypatch):
        """Without binutils the build still works; it just reports no
        footprint."""
        monkeypatch.setattr(doc.shutil, "which",
                            lambda n: None if n == "size" else f"/usr/bin/{n}")
        size = next(c for c in host_checks() if c.name == "size")
        assert size.status == WARN

    def test_every_cross_toolchain_names_the_boards_it_unlocks(self, monkeypatch):
        monkeypatch.setattr(doc.shutil, "which", lambda _n: None)
        for check in toolchain_checks():
            assert check.status == WARN
            assert check.fix, f"{check.name} says nothing about what it is for"

    def test_a_present_toolchain_is_ok(self, monkeypatch):
        monkeypatch.setattr(doc.shutil, "which",
                            lambda n: "/opt/bin/" + n)
        monkeypatch.setattr(doc, "_version_of", lambda *a, **k: "13.2")
        assert all(c.status == OK for c in toolchain_checks())


class TestCommand:
    def test_doctor_runs_and_reports(self):
        result = CliRunner().invoke(cli, ["doctor"])
        assert result.exit_code in (0, 1)
        assert "python" in result.output

    def test_json_output_is_machine_readable(self):
        """CI wants the checks, not the formatting."""
        result = CliRunner().invoke(cli, ["doctor", "--json"])
        payload = json.loads(result.output)
        assert isinstance(payload, list)
        assert {"name", "status", "detail", "fix"} <= set(payload[0])

    def test_json_and_text_agree_on_the_exit_code(self):
        a = CliRunner().invoke(cli, ["doctor"])
        b = CliRunner().invoke(cli, ["doctor", "--json"])
        assert a.exit_code == b.exit_code

    def test_doctor_is_registered(self):
        assert "doctor" in cli.commands
