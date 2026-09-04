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

from ebuild.firmware.flash import FlashError, flash


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


def test_missing_image_is_rejected_before_invoking_the_tool(tmp_path, record_run):
    with pytest.raises(FlashError, match="Image not found"):
        flash(tmp_path / "missing.bin", tool="openocd")

    assert record_run == []


def test_unknown_tool_is_rejected(tmp_path, record_run):
    image_path = _image(tmp_path, "firmware.bin")

    with pytest.raises(FlashError, match="Unknown flash tool"):
        flash(image_path, tool="jtagulator")

    assert record_run == []
