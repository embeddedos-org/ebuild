# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""`toolchain.compiler` selects the compiler that actually runs.

resolve_toolchain() used `compiler` only as a key into PREDEFINED_TOOLCHAINS
and then built the tool names as ``f"{prefix}gcc"``. Any value that was not one
of the five toolchain *names* -- `clang`, `cc`, or the `arm-none-eabi-gcc`
spelling -- produced `prefix = ""` and `cc = "gcc"`, with no warning: a
cross-compile configuration built a host binary and reported success.

These pin the three things that were wrong (a non-gcc compiler was ignored, a
compiler carrying its own prefix was ignored, and neither produced a warning)
without changing what the documented spelling does.
"""

import unittest

from ebuild.build.toolchain import PREDEFINED_TOOLCHAINS, resolve_toolchain
from ebuild.core.config import ToolchainConfig


class CompilerNamesTheCompiler(unittest.TestCase):
    def test_clang_is_clang_and_not_gcc(self):
        t = resolve_toolchain(ToolchainConfig(compiler="clang"))
        self.assertEqual(t.cc, "clang")
        self.assertEqual(t.cxx, "clang++")

    def test_cc_is_cc(self):
        t = resolve_toolchain(ToolchainConfig(compiler="cc"))
        self.assertEqual(t.cc, "cc")
        self.assertEqual(t.cxx, "c++")

    def test_a_compiler_carrying_its_own_prefix_cross_compiles(self):
        # docs/architecture.md spells the compiler this way. It used to fall
        # through to host gcc, so `ebuild build` emitted a host binary and
        # printed "Ready to flash".
        t = resolve_toolchain(
            ToolchainConfig(compiler="arm-none-eabi-gcc", arch="arm")
        )
        self.assertEqual(t.cc, "arm-none-eabi-gcc")
        self.assertEqual(t.cxx, "arm-none-eabi-g++")
        self.assertEqual(t.prefix, "arm-none-eabi-")
        # The binutils have to follow the compiler, or the archive step runs
        # the host ar over cross objects.
        self.assertEqual(t.ar, "arm-none-eabi-ar")
        self.assertEqual(t.objcopy, "arm-none-eabi-objcopy")

    def test_an_unknown_driver_is_used_verbatim_and_infers_no_prefix(self):
        # A custom driver must not be guessed at: it is used as given, so it
        # fails loudly at build time instead of silently becoming host gcc.
        t = resolve_toolchain(ToolchainConfig(compiler="my-special-driver"))
        self.assertEqual(t.cc, "my-special-driver")
        self.assertEqual(t.prefix, "")


class DocumentedSpellingsAreUnchanged(unittest.TestCase):
    def test_default_is_host_gcc(self):
        t = resolve_toolchain(ToolchainConfig())
        self.assertEqual((t.cc, t.cxx, t.ar, t.arch), ("gcc", "g++", "ar", "x86_64"))

    def test_none_is_host_gcc(self):
        t = resolve_toolchain(None)
        self.assertEqual((t.cc, t.prefix, t.arch), ("gcc", "", "x86_64"))

    def test_gcc_with_an_explicit_prefix(self):
        # docs/task_cortex_r5_example.md: compiler: gcc + prefix: arm-none-eabi-
        t = resolve_toolchain(
            ToolchainConfig(compiler="gcc", arch="arm", prefix="arm-none-eabi-")
        )
        self.assertEqual(t.cc, "arm-none-eabi-gcc")
        self.assertEqual(t.arch, "arm")

    def test_every_predefined_toolchain_still_resolves_to_its_prefix(self):
        for name, predef in PREDEFINED_TOOLCHAINS.items():
            with self.subTest(toolchain=name):
                t = resolve_toolchain(ToolchainConfig(compiler=name))
                self.assertEqual(t.prefix, predef["prefix"])
                self.assertEqual(t.cc, f"{predef['prefix']}gcc")
                self.assertEqual(t.arch, predef["arch"])

    def test_an_explicit_prefix_wins_over_one_derived_from_the_compiler(self):
        t = resolve_toolchain(
            ToolchainConfig(compiler="aarch64-linux-gnu-gcc", prefix="riscv64-linux-gnu-")
        )
        self.assertEqual(t.cc, "riscv64-linux-gnu-gcc")


if __name__ == "__main__":
    unittest.main()
