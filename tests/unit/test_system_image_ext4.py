# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Regression tests for ImageBuilder's ext4 output.

`_create_ext4` writes a zero-filled file and then runs mkfs.ext4 over it.
The mkfs.ext4 exit status was never read, so when it failed (an old
e2fsprogs without `-d`, a rootfs it cannot read, an image too small for
the tree) `ebuild system --format ext4` still printed "Image created" and
left an unformatted file of zeros behind as the image.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from ebuild.system import image as image_mod
from ebuild.system.image import ImageBuilder, ImageError

pytestmark = pytest.mark.skipif(
    image_mod.IS_WINDOWS, reason="ext4 images are refused on Windows"
)


def _fake_tools(
    monkeypatch: pytest.MonkeyPatch, mkfs_returncode: int, calls: list
) -> None:
    """Pretend mkfs.ext4 is installed and exits with *mkfs_returncode*."""
    monkeypatch.setattr(image_mod, "_has_command", lambda name: True)

    def fake_empty_image(self, output: Path, size_mb: int) -> None:
        output.write_bytes(b"\0" * 4096)

    monkeypatch.setattr(ImageBuilder, "_create_empty_image", fake_empty_image)

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        if cmd[0] == "mkfs.ext4":
            return SimpleNamespace(
                returncode=mkfs_returncode,
                stdout=b"",
                stderr=b"mkfs.ext4: invalid option -- 'd'\n",
            )
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)


def _rootfs(tmp_path: Path) -> Path:
    rootfs = tmp_path / "rootfs"
    (rootfs / "etc").mkdir(parents=True)
    (rootfs / "etc" / "hostname").write_text("eos\n", encoding="utf-8")
    return rootfs


def test_failed_mkfs_ext4_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list = []
    _fake_tools(monkeypatch, mkfs_returncode=1, calls=calls)
    builder = ImageBuilder(tmp_path / "_build")

    with pytest.raises(ImageError, match="mkfs.ext4 failed.*invalid option"):
        builder.create(_rootfs(tmp_path), image_format="ext4", image_size_mb=4)

    assert [c[0] for c in calls] == ["mkfs.ext4"]
    # The zero-filled file is not an image; it must not be left behind
    # where the next step would pick it up as one.
    assert not (tmp_path / "_build" / "images" / "eos-rootfs.ext4").exists()


def test_successful_mkfs_ext4_returns_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list = []
    _fake_tools(monkeypatch, mkfs_returncode=0, calls=calls)
    builder = ImageBuilder(tmp_path / "_build")
    rootfs = _rootfs(tmp_path)

    out = builder.create(rootfs, image_format="ext4", image_size_mb=4,
                         label="sysroot")

    assert out == tmp_path / "_build" / "images" / "sysroot.ext4"
    assert out.is_file()
    assert calls == [["mkfs.ext4", "-L", "sysroot", "-d", str(rootfs), str(out)]]
