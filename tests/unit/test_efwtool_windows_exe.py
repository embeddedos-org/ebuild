# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""A cached efwtool build is found when the binary carries ``.exe``.

On Windows, CMake (MSVC or MinGW) links the eFirmware tool as
``efwtool.exe``. ``_first_efwtool`` searched only for the bare name, so
``find_efwtool`` returned None and ``ebuild package`` reported that efwtool
could not be built even though the build had produced it.
"""

import os

from ebuild.build import firmware_image
from ebuild.build.firmware_image import find_efwtool


def _exe(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"MZ")
    os.chmod(path, 0o755)
    return path


def test_a_cached_efwtool_exe_is_found(tmp_path, monkeypatch):
    monkeypatch.setattr(firmware_image.shutil, "which", lambda name: None)
    root = tmp_path / "efirmware"
    root.mkdir()
    (root / "CMakeLists.txt").write_text("project(efw)\n")
    # Multi-config generators (Visual Studio) add a per-config directory.
    tool = _exe(root / "_ebuild" / "tools" / "Debug" / "efwtool.exe")

    assert find_efwtool(tmp_path) == tool


def test_a_bare_efwtool_is_still_found(tmp_path, monkeypatch):
    monkeypatch.setattr(firmware_image.shutil, "which", lambda name: None)
    root = tmp_path / "efirmware"
    root.mkdir()
    (root / "CMakeLists.txt").write_text("project(efw)\n")
    tool = _exe(root / "_ebuild" / "tools" / "efwtool")

    assert find_efwtool(tmp_path) == tool
