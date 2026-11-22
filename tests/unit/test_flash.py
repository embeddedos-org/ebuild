# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Regression tests for ebuild.firmware.flash.

`flash --tool openocd` builds a single -c argv element that OpenOCD's own
Tcl interpreter re-parses as a command line. An image path containing a
space split into extra "program" arguments there, even though subprocess
received the whole path as one argv element -- OpenOCD, not the shell, was
doing the re-splitting.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from ebuild.firmware.flash import FlashError, flash, reset


@pytest.fixture
def record_run(monkeypatch):
    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def _image(tmp_path: Path, name: str) -> Path:
    image_path = tmp_path / name
    image_path.write_bytes(b"\x00")
    return image_path


def test_openocd_program_command_keeps_a_spaced_path_as_one_token(
    tmp_path, record_run
):
    image_path = _image(tmp_path, "my firmware.bin")

    flash(image_path, tool="openocd", target="stm32f4", address=0x08000000)

    assert len(record_run) == 1
    cmd = record_run[0]
    program_cmd = cmd[cmd.index("-c") + 1]
    # Tcl brace-grouping: {my firmware.bin} parses as one word regardless
    # of the space inside it.
    assert f"program {{{image_path}}} " in program_cmd
    assert program_cmd.count("{") == 1 and program_cmd.count("}") == 1


def test_openocd_program_command_is_unchanged_for_a_plain_path(
    tmp_path, record_run
):
    image_path = _image(tmp_path, "firmware.bin")

    flash(image_path, tool="openocd", target="stm32f4", address=0x08000000)

    cmd = record_run[0]
    program_cmd = cmd[cmd.index("-c") + 1]
    # Built independently of the production f-string so this pins the
    # actual expected output rather than mirroring how flash() builds it.
    expected = "program {" + str(image_path) + "} 0x8000000 verify reset exit"
    assert program_cmd == expected


def test_openocd_rejects_an_image_path_with_unbalanced_braces(tmp_path, record_run):
    image_path = _image(tmp_path, "fw}.bin")

    with pytest.raises(FlashError, match="unbalanced braces"):
        flash(image_path, tool="openocd")

    assert record_run == []


def test_flash_failure_raises_flash_error_with_tool_stderr(tmp_path, monkeypatch):
    image_path = _image(tmp_path, "firmware.bin")

    def fake_run(cmd, *args, **kwargs):
        return SimpleNamespace(returncode=1, stderr=b"no device found")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FlashError, match="Flash failed: no device found"):
        flash(image_path, tool="openocd")


# esptool on a French-locale Windows host: Python writes its piped stderr in
# the ANSI code page (cp1252), so "Accès refusé" is not valid UTF-8.
_CP1252_STDERR = "could not open port 'COM3': Accès refusé.".encode("cp1252")


def test_flash_failure_with_non_utf8_stderr_still_raises_flash_error(
    tmp_path, monkeypatch
):
    image_path = _image(tmp_path, "firmware.bin")
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, *a, **k: SimpleNamespace(returncode=2, stderr=_CP1252_STDERR),
    )

    with pytest.raises(FlashError, match="Flash failed: could not open port 'COM3'"):
        flash(image_path, tool="esptool")


def test_reset_failure_with_non_utf8_stderr_still_raises_flash_error(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, *a, **k: SimpleNamespace(returncode=2, stderr=_CP1252_STDERR),
    )

    with pytest.raises(FlashError, match="Reset failed: could not open port 'COM3'"):
        reset(tool="pyocd")


def test_missing_image_is_rejected_before_invoking_the_tool(tmp_path, record_run):
    with pytest.raises(FlashError, match="Image not found"):
        flash(tmp_path / "missing.bin", tool="openocd")

    assert record_run == []


def test_unknown_tool_is_rejected(tmp_path, record_run):
    image_path = _image(tmp_path, "firmware.bin")

    with pytest.raises(FlashError, match="Unknown flash tool"):
        flash(image_path, tool="jtagulator")

    assert record_run == []


# esptool stops with "... Wrong --chip argument?" when the chip it finds is
# not the one --chip names, so the target has to reach --chip.
@pytest.mark.parametrize(
    "target, chip",
    [
        ("esp32", "esp32"),
        ("esp32s3", "esp32s3"),
        ("esp32c3", "esp32c3"),
        ("ESP32-S3", "esp32s3"),
        ("esp32_c6", "esp32c6"),
        ("esp32c61", "esp32c61"),
        ("esp8266", "esp8266"),
        # Board ids name their chip by prefix; the longest known chip wins.
        ("esp32dev", "esp32"),
        ("esp32-devkitc", "esp32"),
        ("ESP32-S3-DevKitC-1", "esp32s3"),
        ("esp32c6-devkitm", "esp32c6"),
    ],
)
def test_esptool_chip_follows_an_espressif_target(tmp_path, record_run, target, chip):
    image_path = _image(tmp_path, "app.bin")

    flash(image_path, tool="esptool", target=target, address=0x10000)

    assert record_run == [
        ["esptool.py", "--chip", chip, "write_flash", "0x10000", str(image_path)]
    ]


def test_esptool_keeps_esp32_for_a_target_that_is_not_an_espressif_chip(
    tmp_path, record_run
):
    image_path = _image(tmp_path, "app.bin")

    flash(image_path, tool="esptool", target="stm32f4", address=0x10000,
          extra_args=["--port", "/dev/ttyUSB0"])

    assert record_run == [
        ["esptool.py", "--chip", "esp32", "--port", "/dev/ttyUSB0",
         "write_flash", "0x10000", str(image_path)]
    ]
