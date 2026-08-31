# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Unit tests for ebuild.build.ninja_backend.NinjaBackend."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ebuild.build.ninja_backend import NinjaBackend
from ebuild.core.config import ProjectConfig, TargetConfig


def _toolchain():
    return SimpleNamespace(cc="cc", cxx="c++", ar="ar")


class TestNinjaBackendSharedLibrary(unittest.TestCase):
    """A shared_library target must link with the platform's shared-object
    flag and get the same -L/-l wiring as executables. Previously it used the
    link_shared rule but emitted no ldflags and no libs line at all, so any
    -L/-l from `uses` and any target ldflags were silently dropped."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def _generate(self, name: str, target: TargetConfig, package_paths=None) -> str:
        build_dir = Path(self._tmpdir.name) / name
        config = ProjectConfig(name="proj", version="1.0", targets=[target], source_dir=build_dir)
        backend = NinjaBackend(config, build_dir, _toolchain(), package_paths=package_paths)
        backend.generate()
        return (build_dir / "build.ninja").read_text(encoding="utf-8")

    def test_shared_library_gets_shared_flag(self):
        target = TargetConfig(name="mylib", target_type="shared_library", sources=["lib.c"])
        ninja = self._generate("shared", target)

        shared_flag = "-dynamiclib" if sys.platform == "darwin" else "-shared"
        self.assertIn(shared_flag, ninja)
        # It must go through a compiler-driver rule, not the `ar` archiver.
        # link_shared is that rule, and it carries the shared-object flag, so
        # the flag is never repeated in the edge's ldflags.
        lib_line = next(line for line in ninja.splitlines() if "libmylib" in line and line.startswith("build"))
        self.assertIn(": link_shared ", lib_line)
        self.assertNotIn(": ar_rule", lib_line)

    def test_shared_library_gets_lib_dirs_and_libs(self):
        target = TargetConfig(
            name="mylib", target_type="shared_library", sources=["lib.c"], uses=["zlib"]
        )
        lib_dir = Path(self._tmpdir.name) / "zlib-lib"
        package_paths = {
            "zlib": SimpleNamespace(include_dirs=[], lib_dirs=[lib_dir], libraries=["z"])
        }
        ninja = self._generate("shared_libs", target, package_paths=package_paths)

        self.assertIn(f"-L{lib_dir}", ninja)
        self.assertIn("libs = -lz", ninja)

    def test_static_library_unaffected(self):
        target = TargetConfig(name="mylib", target_type="static_library", sources=["lib.c"])
        ninja = self._generate("static", target)

        self.assertIn(": ar_rule", ninja)

        # The link_shared *rule* is always declared in the preamble, so the
        # bare string "-shared" appears in every generated file. What must be
        # absent is any build *edge* that uses it.
        edges = [line for line in ninja.splitlines() if line.startswith("build ")]
        self.assertTrue(edges, "no build edges were generated")
        for edge in edges:
            self.assertNotIn(": link_shared ", edge)
            self.assertNotIn(": link ", edge)


if __name__ == "__main__":
    unittest.main()
