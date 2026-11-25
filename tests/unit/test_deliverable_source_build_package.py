# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""A deliverable's source tree keeps Python packages named ``build``.

``collect_source`` skips directories named ``build`` so CMake output is not
shipped as source. The same rule also dropped ``ebuild/ebuild/build/`` -- the
``ebuild.build`` package (toolchain, Ninja backend, footprint, ...) -- so the
ebuild source in every deliverable could not be imported or rebuilt.
"""

from ebuild import deliverable_packager
from ebuild.sdk_generator import get_target_info


def _collect(tmp_path):
    ws = tmp_path / "ws"
    pkg = ws / "ebuild" / "ebuild" / "build"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "toolchain.py").write_text("X = 1\n")
    cmake_out = ws / "eos" / "core" / "build"
    cmake_out.mkdir(parents=True)
    (cmake_out / "CMakeCache.txt").write_text("CMAKE_BUILD_TYPE:STRING=Debug\n")
    out = tmp_path / "out"
    deliverable_packager.collect_source(str(ws), str(out), "x86_64",
                                        get_target_info("x86_64"))
    return out


def test_python_build_package_is_collected(tmp_path):
    out = _collect(tmp_path)
    assert (out / "ebuild" / "ebuild" / "build" / "toolchain.py").is_file()


def test_cmake_build_directory_is_still_skipped(tmp_path):
    out = _collect(tmp_path)
    assert not (out / "eos" / "core" / "build").exists()
