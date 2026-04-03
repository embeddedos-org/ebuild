# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for ETimer — stopwatch time formatting.
"""
import pytest

tk = pytest.importorskip("tkinter")


class TestTimerFormatting:
    """Test the static _fmt method (no GUI needed)."""

    def test_zero(self):
        from gui.apps.etimer import ETimer
        assert ETimer._fmt(0) == "00:00:00.000"

    def test_one_second(self):
        from gui.apps.etimer import ETimer
        assert ETimer._fmt(1.0) == "00:00:01.000"

    def test_one_minute(self):
        from gui.apps.etimer import ETimer
        assert ETimer._fmt(60.0) == "00:01:00.000"

    def test_one_hour(self):
        from gui.apps.etimer import ETimer
        assert ETimer._fmt(3600.0) == "01:00:00.000"

    def test_milliseconds(self):
        from gui.apps.etimer import ETimer
        result = ETimer._fmt(1.5)
        assert result == "00:00:01.500"

    def test_complex_time(self):
        from gui.apps.etimer import ETimer
        result = ETimer._fmt(3661.123)
        assert result == "01:01:01.123"

    def test_large_time(self):
        from gui.apps.etimer import ETimer
        result = ETimer._fmt(36000)  # 10 hours
        assert result == "10:00:00.000"
