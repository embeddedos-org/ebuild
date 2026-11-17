# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Only executables land in a deliverable's ``eosuite/bin``.

The packager chose binaries with ``os.access(path, os.X_OK)``. On Windows that
is True for every existing file, so object files, CMake caches and logs from
the eApps build tree were all shipped as "binaries" in ``eosuite/bin``.
"""

import os
import sys
import zipfile

import pytest

from ebuild import deliverable_packager


def _bin_entries(zpath):
    with zipfile.ZipFile(zpath) as zf:
        return sorted(os.path.basename(n) for n in zf.namelist()
                      if "/eosuite/bin/" in n)


def _package(tmp_path):
    build = tmp_path / "build"
    suite = build / "eosuite"
    (suite / "CMakeFiles").mkdir(parents=True)
    (suite / "CMakeCache.txt").write_text("CMAKE_BUILD_TYPE:STRING=Debug\n")
    (suite / "CMakeFiles" / "main.c.o").write_bytes(b"\x7fELF")
    (suite / "ebot.exe").write_bytes(b"MZ")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    return deliverable_packager.package_deliverable(
        "x86_64", "1.0.0", str(build), str(tmp_path / "dist"), str(workspace))


def test_build_tree_files_are_not_shipped_as_binaries(tmp_path, monkeypatch):
    # Reproduce Windows semantics on every host: X_OK is True for any file.
    monkeypatch.setattr(os, "access", lambda path, mode: True)
    assert _bin_entries(_package(tmp_path)) == ["ebot.exe"]


@pytest.mark.skipif(sys.platform == "win32",
                    reason="POSIX execute bit cannot be set on Windows")
def test_a_file_with_the_execute_bit_is_shipped(tmp_path):
    tool = tmp_path / "build" / "eosuite" / "eos_shell"
    tool.parent.mkdir(parents=True)
    tool.write_bytes(b"\x7fELF")
    os.chmod(tool, 0o755)
    assert "eos_shell" in _bin_entries(_package(tmp_path))
