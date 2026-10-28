# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

import sys
import types

from click.testing import CliRunner
import pytest

import ebuild.cli.commands as commands
from ebuild.cli.commands import _serial_ports, monitor


class RecordingLogger:
    def __init__(self):
        self.errors = []
        self.infos = []

    def header(self, msg):
        pass

    def step(self, msg):
        pass

    def info(self, msg):
        self.infos.append(msg)

    def success(self, msg):
        pass

    def error(self, msg):
        self.errors.append(msg)

    def warning(self, msg):
        pass

    def debug(self, msg):
        pass


def _port(device, vid):
    return types.SimpleNamespace(device=device, vid=vid)


def _install_fake_pyserial(monkeypatch, comports, serial_cls=None):
    """Put a fake `serial` package in sys.modules; pyserial is optional."""
    list_ports = types.ModuleType("serial.tools.list_ports")
    list_ports.comports = lambda: comports
    tools = types.ModuleType("serial.tools")
    tools.list_ports = list_ports
    serial = types.ModuleType("serial")
    serial.tools = tools
    if serial_cls is not None:
        serial.Serial = serial_cls
    monkeypatch.setitem(sys.modules, "serial", serial)
    monkeypatch.setitem(sys.modules, "serial.tools", tools)
    monkeypatch.setitem(sys.modules, "serial.tools.list_ports", list_ports)


def _remove_pyserial(monkeypatch):
    # A None entry in sys.modules makes the import raise ImportError.
    for name in ("serial", "serial.tools", "serial.tools.list_ports"):
        monkeypatch.setitem(sys.modules, name, None)


@pytest.fixture
def no_posix_ports(monkeypatch):
    monkeypatch.setattr(commands.glob, "glob", lambda pattern: [])


def test_com_ports_keep_only_usb_devices(monkeypatch, no_posix_ports):
    _install_fake_pyserial(monkeypatch, [
        _port("COM1", None),   # built-in port
        _port("COM4", None),   # Bluetooth serial port
        _port("COM3", 0x10C4),
    ])
    assert _serial_ports() == ["COM3"]


def test_com_ports_sort_numerically(monkeypatch, no_posix_ports):
    _install_fake_pyserial(monkeypatch, [
        _port("COM10", 0x0403),
        _port("COM2", 0x0403),
        _port("COM3", 0x0403),
    ])
    assert _serial_ports() == ["COM2", "COM3", "COM10"]


def test_non_com_devices_from_pyserial_are_ignored(monkeypatch):
    # On Linux pyserial reports /dev/ttyUSB0 too; the glob already found it.
    monkeypatch.setattr(
        commands.glob, "glob",
        lambda pattern: ["/dev/ttyUSB0"] if pattern == "/dev/ttyUSB*" else [],
    )
    _install_fake_pyserial(monkeypatch, [_port("/dev/ttyUSB0", 0x10C4)])
    assert _serial_ports() == ["/dev/ttyUSB0"]


def test_posix_ports_found_without_pyserial(monkeypatch):
    monkeypatch.setattr(
        commands.glob, "glob",
        lambda pattern: ["/dev/ttyACM0"] if pattern == "/dev/ttyACM*" else [],
    )
    _remove_pyserial(monkeypatch)
    assert _serial_ports() == ["/dev/ttyACM0"]


def test_monitor_reports_missing_pyserial_before_detection(
        monkeypatch, no_posix_ports):
    _remove_pyserial(monkeypatch)
    log = RecordingLogger()
    result = CliRunner().invoke(monitor, [], obj=log)
    assert result.exit_code == 1
    assert len(log.errors) == 1
    assert "pyserial is not installed" in log.errors[0]


def test_monitor_auto_detects_single_usb_com_port(
        monkeypatch, no_posix_ports):
    opened = []

    class FakeSerial:
        def __init__(self, port, baud, timeout):
            opened.append(port)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, size):
            raise KeyboardInterrupt

    _install_fake_pyserial(
        monkeypatch,
        [_port("COM1", None), _port("COM5", 0x2341)],
        serial_cls=FakeSerial,
    )
    log = RecordingLogger()
    result = CliRunner().invoke(monitor, [], obj=log)
    assert result.exit_code == 0, log.errors
    assert opened == ["COM5"]
    assert "Auto-detected COM5" in log.infos


def test_monitor_refuses_to_guess_between_usb_com_ports(
        monkeypatch, no_posix_ports):
    _install_fake_pyserial(
        monkeypatch, [_port("COM3", 0x10C4), _port("COM7", 0x0403)])
    log = RecordingLogger()
    result = CliRunner().invoke(monitor, [], obj=log)
    assert result.exit_code == 1
    assert "More than one serial device" in log.errors[0]
