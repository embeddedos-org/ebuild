# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for serial port detection.
"""
import sys
import pytest

tk = pytest.importorskip("tkinter")


class TestSerialPortDetection:
    def test_detect_returns_list(self):
        from gui.apps.serial_term import detect_serial_ports
        ports = detect_serial_ports()
        assert isinstance(ports, list)

    def test_detect_returns_strings(self):
        from gui.apps.serial_term import detect_serial_ports
        ports = detect_serial_ports()
        for port in ports:
            assert isinstance(port, str)

    def test_baud_rates_defined(self):
        from gui.apps.serial_term import BAUD_RATES
        assert isinstance(BAUD_RATES, list)
        assert "9600" in BAUD_RATES
        assert "115200" in BAUD_RATES

    def test_windows_port_format(self):
        if sys.platform != "win32":
            pytest.skip("Windows-only test")
        from gui.apps.serial_term import detect_serial_ports
        ports = detect_serial_ports()
        for port in ports:
            assert port.startswith("COM")
