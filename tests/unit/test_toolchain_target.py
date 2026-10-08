# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""`toolchain.target` is honored; unknown toolchain keys fail fast.

Issue #171: every project template emits `toolchain: {target: arm-none-eabi}`,
but ToolchainConfig had no `target` field, so the key was dropped silently and
`resolve_toolchain` fell back to host `gcc` -- an stm32f4 project built a host
executable and nothing reported it.

These pin the fix:
- `target:` selects the predefined toolchain (prefix, arch, drivers).
- An unknown `target:` name raises instead of becoming host gcc.
- A `target:` whose compiler is not installed raises instead of generating
  a build.ninja around a missing compiler.
- Unknown `toolchain:` keys raise ConfigError at parse time (fail-closed on
  the silent drop that hid `target:` for months).
"""

import os
import stat
import unittest
from pathlib import Path
from unittest import mock

import yaml

from ebuild.build.toolchain import ToolchainError, resolve_toolchain
from ebuild.core.config import ConfigError, ToolchainConfig, load_config


def _fake_toolchain_dir(tmp: Path, name: str = "arm-none-eabi-gcc") -> Path:
    """A temp dir containing an executable compiler shim; returns the dir."""
    bindir = tmp / "fake-toolchain-bin"
    bindir.mkdir(parents=True, exist_ok=True)
    # shutil.which() on Windows only matches PATHEXT extensions (.exe, .bat,
    # .cmd); an extensionless shebang shim is invisible to it there.
    shim_name = name + (".bat" if os.name == "nt" else "")
    exe = bindir / shim_name
    exe.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return bindir


class TargetSelectsToolchain(unittest.TestCase):
    def test_target_arm_none_eabi_cross_compiles(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            bindir = _fake_toolchain_dir(Path(td))
            with mock.patch.dict(os.environ, {"PATH": str(bindir) + os.pathsep + os.environ["PATH"]}):
                t = resolve_toolchain(ToolchainConfig(target="arm-none-eabi"))
        self.assertEqual(t.cc, "arm-none-eabi-gcc")
        self.assertEqual(t.cxx, "arm-none-eabi-g++")
        self.assertEqual(t.ar, "arm-none-eabi-ar")
        self.assertEqual(t.objcopy, "arm-none-eabi-objcopy")
        self.assertEqual(t.prefix, "arm-none-eabi-")
        self.assertEqual(t.arch, "arm")

    def test_target_host_is_host(self):
        t = resolve_toolchain(ToolchainConfig(target="host"))
        self.assertEqual((t.cc, t.arch), ("gcc", "x86_64"))

    def test_explicit_prefix_overrides_target_prefix(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            bindir = _fake_toolchain_dir(Path(td), name="my-arm-gcc")
            with mock.patch.dict(os.environ, {"PATH": str(bindir) + os.pathsep + os.environ["PATH"]}):
                t = resolve_toolchain(
                    ToolchainConfig(target="arm-none-eabi", prefix="my-arm-")
                )
        self.assertEqual(t.cc, "my-arm-gcc")

    def test_unknown_target_raises(self):
        with self.assertRaisesRegex(ToolchainError, "unknown toolchain target"):
            resolve_toolchain(ToolchainConfig(target="arm-none-eabii"))

    def test_missing_toolchain_installation_raises(self):
        # `target:` names a real toolchain, but its compiler is not on PATH.
        # Previously this generated a build.ninja around a missing compiler;
        # now it fails here with the reason.
        with mock.patch.dict(os.environ, {"PATH": "/nonexistent-dir-for-test"}):
            with self.assertRaisesRegex(ToolchainError, "not found on PATH"):
                resolve_toolchain(ToolchainConfig(target="arm-none-eabi"))

    def test_no_target_keeps_old_behavior_without_installed_check(self):
        # The `compiler:` spelling is unchanged: no installation probe, so
        # existing configs and tests that only inspect resolution keep working.
        t = resolve_toolchain(ToolchainConfig(compiler="arm-none-eabi-gcc"))
        self.assertEqual(t.cc, "arm-none-eabi-gcc")


class ToolchainKeysAreStrict(unittest.TestCase):
    def _write(self, tmp: Path, toolchain: dict) -> Path:
        p = tmp / "build.yaml"
        p.write_text(
            yaml.safe_dump(
                {
                    "project": {"name": "demo", "version": "0.1.0"},
                    "toolchain": toolchain,
                    "targets": [],
                }
            ),
            encoding="utf-8",
        )
        return p

    def test_target_is_parsed(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            cfg = load_config(self._write(Path(td), {"target": "arm-none-eabi"}))
        self.assertIsNotNone(cfg.toolchain)
        self.assertEqual(cfg.toolchain.target, "arm-none-eabi")

    def test_unknown_toolchain_key_raises(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = self._write(Path(td), {"target": "arm-none-eabi", "bogus_key": 1})
            with self.assertRaisesRegex(ConfigError, "unknown 'toolchain' key"):
                load_config(path)

    def test_non_string_target_raises(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = self._write(Path(td), {"target": 42})
            with self.assertRaisesRegex(ConfigError, "must be a string"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
