# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Regression tests for how ImageBuilder reports a failed image tool.

`qemu-img` and `mksquashfs` failures were reported with
`result.stderr.decode()`, a strict UTF-8 decode. A tool whose stderr is not
valid UTF-8 -- mksquashfs names the rootfs file it could not read, and Linux
file names are arbitrary bytes -- turned the failure into a
UnicodeDecodeError, so `ebuild system` printed a codec error instead of the
tool's own message and never raised ImageError at all.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from ebuild.system import image as image_mod
from ebuild.system.image import ImageBuilder, ImageError

# Latin-1 "é" (0xE9) is not valid UTF-8 on its own.
_NON_UTF8_STDERR = b"FATAL ERROR: cannot read /rootfs/caf\xe9.txt\n"


def _fail_tool(monkeypatch: pytest.MonkeyPatch, tool: str) -> None:
    """Pretend every tool is installed and *tool* fails with non-UTF-8 stderr."""
    monkeypatch.setattr(image_mod, "_has_command", lambda name: True)

    def fake_run(cmd, *args, **kwargs):
        if cmd[0] == tool:
            return SimpleNamespace(returncode=1, stdout=b"", stderr=_NON_UTF8_STDERR)
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)


def _rootfs(tmp_path: Path) -> Path:
    rootfs = tmp_path / "rootfs"
    rootfs.mkdir()
    return rootfs


def test_qemu_img_failure_with_non_utf8_stderr_raises_image_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fail_tool(monkeypatch, "qemu-img")
    builder = ImageBuilder(tmp_path / "_build")

    with pytest.raises(ImageError, match=r"qemu-img failed: .*cannot read /rootfs/caf"):
        builder.create(_rootfs(tmp_path), image_format="qcow2", image_size_mb=4)


def test_mksquashfs_failure_with_non_utf8_stderr_raises_image_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The Windows refusal comes before the tool runs; bypass it so the
    # failure path is exercised on every host.
    monkeypatch.setattr(image_mod, "IS_WINDOWS", False)
    _fail_tool(monkeypatch, "mksquashfs")
    builder = ImageBuilder(tmp_path / "_build")

    with pytest.raises(ImageError, match=r"mksquashfs failed: .*cannot read /rootfs/caf"):
        builder.create(_rootfs(tmp_path), image_format="squashfs")
