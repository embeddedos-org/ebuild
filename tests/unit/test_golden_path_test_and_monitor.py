# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""`ebuild test` and `ebuild monitor` — steps 6 and 8 of the golden path.

§7 names eBuild's MVP responsibility as "Setup, configure, build, test, flash,
monitor" and §7.1 spells the sequence out. Neither of these two existed; the
path stopped at step 5 of 8.

The case these tests exist for is the empty run. ctest exits 0 when it finds
nothing to execute, so the obvious implementation — trust the exit status —
reports a green test suite for a project containing no tests at all. That is a
worse outcome than having no test command, because it actively reassures.
"""

import pytest

from ebuild.build.dispatch import (
    TestOutcome,
    _found_no_tests,
    _parse_test_counts,
)


class TestCountParsing:
    """Counts come from the runner's own summary, never from exit status."""

    def test_ctest_summary(self):
        out = "100% tests passed, 0 tests failed out of 17"
        assert _parse_test_counts("cmake", out) == (17, 0)

    def test_ctest_summary_with_failures(self):
        out = "50% tests passed, 3 tests failed out of 6"
        assert _parse_test_counts("cmake", out) == (3, 3)

    def test_cargo_summary(self):
        out = "test result: ok. 12 passed; 0 failed; 0 ignored"
        assert _parse_test_counts("cargo", out) == (12, 0)

    def test_meson_summary(self):
        out = "Ok:                 12\nExpected Fail:      0\nFail:               2\n"
        assert _parse_test_counts("meson", out) == (12, 2)

    def test_make_has_no_standard_summary(self):
        # Rather than invent a format for make, the counts stay unknown and the
        # exit status carries the verdict. Reporting a made-up number would be
        # worse than reporting none.
        assert _parse_test_counts("make", "anything at all") == (None, None)

    def test_unrecognised_output_yields_no_counts(self):
        assert _parse_test_counts("cmake", "something else entirely") == (None, None)


class TestEmptyRunIsNotAPass:
    """The trap: ctest exits 0 having run nothing."""

    def test_ctest_no_tests_marker_is_detected(self):
        assert _found_no_tests("cmake", "No tests were found!!!", None, None) is True

    def test_zero_totals_are_detected_even_without_a_marker(self):
        # A runner that prints a well-formed summary adding up to nothing is
        # the same situation reached by a different route.
        assert _found_no_tests("cargo", "test result: ok.", 0, 0) is True

    def test_a_real_run_is_not_flagged(self):
        assert _found_no_tests("cmake", "100% tests passed", 17, 0) is False

    def test_outcome_is_not_ok_when_nothing_ran(self):
        o = TestOutcome(ok=False, ran=True, found_none=True, returncode=0)
        assert o.ok is False
        assert "found no tests" in o.summary()


class TestOutcomeReporting:
    def test_counts_are_withheld_when_unparsed(self):
        o = TestOutcome(ok=True, ran=True, returncode=0)
        assert o.counts_known is False
        assert "no summary" in o.summary()

    def test_counts_are_reported_when_parsed(self):
        o = TestOutcome(ok=True, ran=True, passed=17, failed=0, returncode=0)
        assert o.counts_known is True
        assert o.summary() == "17 passed, 0 failed"

    def test_a_run_that_never_started_says_why(self):
        o = TestOutcome(ok=False, ran=False, reason="ctest is not installed")
        assert o.summary() == "ctest is not installed"


class TestMonitorPortResolution:
    """monitor must fail fast and actionably with no hardware attached."""

    def test_an_explicit_port_is_honoured(self):
        # Enumeration misses some adapters. Refusing a port the developer named
        # because we failed to list it would be worse than letting open() say so.
        from ebuild.firmware.monitor import resolve_port
        assert resolve_port("/dev/ttyUSB9") == "/dev/ttyUSB9"

    def test_no_ports_gives_an_actionable_error(self, monkeypatch):
        from ebuild.firmware import monitor as mon
        monkeypatch.setattr(mon, "available_ports", lambda: [])
        with pytest.raises(mon.MonitorError) as exc:
            mon.resolve_port(None)
        assert "--port" in str(exc.value)

    def test_several_ports_are_not_guessed_between(self, monkeypatch):
        # Picking one of several at random is how a monitor session ends up
        # silently attached to the wrong board.
        from ebuild.firmware import monitor as mon
        monkeypatch.setattr(mon, "available_ports", lambda: [
            mon.PortInfo("/dev/ttyUSB0", "board A"),
            mon.PortInfo("/dev/ttyUSB1", "board B"),
        ])
        with pytest.raises(mon.MonitorError) as exc:
            mon.resolve_port(None)
        assert "/dev/ttyUSB0" in str(exc.value)
        assert "/dev/ttyUSB1" in str(exc.value)

    def test_a_single_port_is_selected(self, monkeypatch):
        from ebuild.firmware import monitor as mon
        monkeypatch.setattr(mon, "available_ports", lambda: [
            mon.PortInfo("/dev/ttyACM0", "the only board"),
        ])
        assert mon.resolve_port(None) == "/dev/ttyACM0"


class TestMonitorBaudRate:
    def test_default_when_no_config_exists(self, tmp_path):
        from ebuild.firmware.monitor import DEFAULT_BAUD, baud_from_config
        assert baud_from_config(str(tmp_path / "absent.yaml")) == DEFAULT_BAUD

    def test_board_console_baud_is_read(self, tmp_path):
        from ebuild.firmware.monitor import baud_from_config
        cfg = tmp_path / "build.yaml"
        cfg.write_text("board:\n  console:\n    baud: 9600\n", encoding="utf-8")
        assert baud_from_config(str(cfg)) == 9600

    def test_monitor_section_is_read(self, tmp_path):
        from ebuild.firmware.monitor import baud_from_config
        cfg = tmp_path / "build.yaml"
        cfg.write_text("monitor:\n  baud: 57600\n", encoding="utf-8")
        assert baud_from_config(str(cfg)) == 57600

    def test_a_malformed_config_falls_back_rather_than_raising(self, tmp_path):
        from ebuild.firmware.monitor import DEFAULT_BAUD, baud_from_config
        cfg = tmp_path / "build.yaml"
        cfg.write_text("this: [is: not: valid", encoding="utf-8")
        assert baud_from_config(str(cfg)) == DEFAULT_BAUD

    def test_a_nonsense_baud_is_ignored(self, tmp_path):
        from ebuild.firmware.monitor import DEFAULT_BAUD, baud_from_config
        cfg = tmp_path / "build.yaml"
        cfg.write_text("monitor:\n  baud: -1\n", encoding="utf-8")
        assert baud_from_config(str(cfg)) == DEFAULT_BAUD
