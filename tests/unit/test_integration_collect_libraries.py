# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Libraries must be collected from the directory _cmake_build wrote them to.

_cmake_build() names each build directory after the repo's directory on disk
(``repo_dir.name``), but _collect_libraries() looked under the repo's logical
key (``eboot``, ``eos`` ...). Whenever the two differ -- the ``eBoot`` casing
_find_repos() explicitly accepts, or an ``EBUILD_EBOOT_PATH`` override pointing
at a checkout such as ``eboot-fork`` -- the build succeeded and its static
libraries were silently left out of the rootfs.
"""

import subprocess
from pathlib import Path

from ebuild.cli import integration
from ebuild.cli.integration import _cmake_build, _collect_libraries
from ebuild.cli.logger import Logger


def _fake_cmake(cmd, capture_output=True):
    """Stand in for cmake: the build step drops a static library in -B dir."""
    if "--build" in cmd:
        build_path = Path(cmd[cmd.index("--build") + 1])
        build_path.mkdir(parents=True, exist_ok=True)
        (build_path / "libfake.a").write_bytes(b"!<arch>\n")
    return subprocess.CompletedProcess(cmd, 0, b"", b"")


def test_libraries_from_renamed_repo_dir_are_collected(tmp_path, monkeypatch):
    repo_dir = tmp_path / "src" / "eboot-fork"
    repo_dir.mkdir(parents=True)
    (repo_dir / "CMakeLists.txt").write_text("project(eboot C)\n")
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    monkeypatch.setattr(integration.subprocess, "run", _fake_cmake)

    assert _cmake_build(repo_dir, build_dir, "", Logger())

    libs = _collect_libraries(build_dir, {"eboot": repo_dir})

    assert [lib.name for lib in libs] == ["libfake.a"]


def test_libraries_from_renamed_sdk_subdir_are_collected(tmp_path, monkeypatch):
    repo_dir = tmp_path / "src" / "eIPC-checkout"
    (repo_dir / "sdk" / "c").mkdir(parents=True)
    (repo_dir / "sdk" / "c" / "CMakeLists.txt").write_text("project(eipc C)\n")
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    monkeypatch.setattr(integration.subprocess, "run", _fake_cmake)

    assert _cmake_build(repo_dir, build_dir, "", Logger(), subdir="sdk/c")

    libs = _collect_libraries(build_dir, {"eipc": repo_dir})

    assert [lib.name for lib in libs] == ["libfake.a"]
