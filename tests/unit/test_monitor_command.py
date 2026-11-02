# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for `ebuild monitor` (golden-path serial console, #83).

The issue requires monitor to be testable in CI without hardware: with no
serial device present it must fail cleanly and immediately (exit 1, an
actionable error) rather than hanging. These tests pin that contract.
"""

import glob
import sys

import pytest
from click.testing import CliRunner

from ebuild.cli.commands import cli


def invoke(*args):
    return CliRunner().invoke(cli, ["monitor", *args])


@pytest.fixture
def no_serial_devices(monkeypatch):
    monkeypatch.setattr(glob, "glob", lambda pattern: [])


@pytest.fixture
def no_pyserial(monkeypatch):
    # `import serial` inside the command must raise ImportError even when
    # pyserial happens to be installed on the test machine.
    monkeypatch.setitem(sys.modules, "serial", None)


class TestMonitorRegistered:
    def test_monitor_is_a_command(self):
        assert "monitor" in cli.commands


class TestMonitorWithoutHardware:
    def test_no_device_fails_cleanly(self, no_serial_devices):
        result = invoke()
        assert result.exit_code == 1
        assert "No serial device found" in result.output
        assert "--port" in result.output

    def test_multiple_devices_refuses_to_guess(self, monkeypatch):
        monkeypatch.setattr(
            glob, "glob", lambda pattern: ["/dev/ttyUSB0", "/dev/ttyUSB1"]
        )
        result = invoke()
        assert result.exit_code == 1
        assert "More than one serial device" in result.output
        assert "/dev/ttyUSB0" in result.output

    def test_missing_pyserial_is_actionable(
        self, no_serial_devices, no_pyserial, monkeypatch
    ):
        # Explicit port skips detection; without pyserial the command must
        # say how to fix it instead of crashing.
        monkeypatch.setattr(glob, "glob", lambda pattern: ["/dev/ttyUSB0"])
        result = invoke("--port", "/dev/ttyUSB0")
        assert result.exit_code == 1
        assert "pyserial is not installed" in result.output
