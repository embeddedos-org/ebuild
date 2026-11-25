# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""resolve_manifest must pick the most specific eos toolchain for an arch.

ARCH_TO_TOOLCHAIN is matched with str.startswith(), and the scan took the
first hit in dict order. "mips" is listed before "mips64", "sparc" before
"sparc64", "avr" before "avr32" and "xtensa" before "xtensa-hifi", so a
64-bit MIPS or SPARC target got the 32-bit toolchain (mips-linux-gnu.yaml,
sparc-elf.yaml) and the longer entries were never reachable.
"""
import pytest

from ebuild.eos_ai.eos_hw_analyzer import HardwareProfile
from ebuild.eos_ai.eos_project_generator import EosProjectGenerator


@pytest.mark.parametrize(
    "arch, expected",
    [
        ("mips64", "mips64-linux-gnu.yaml"),
        ("sparc64", "sparc64-linux-gnu.yaml"),
        ("avr32", "avr32-gcc.yaml"),
        ("xtensa-hifi", "xt-clang.yaml"),
        # Unchanged mappings for the shorter prefixes.
        ("mips", "mips-linux-gnu.yaml"),
        ("sparc", "sparc-elf.yaml"),
        ("arm", "arm-none-eabi.yaml"),
        ("arm64", "aarch64-linux-gnu.yaml"),
        ("xtensa", "xtensa-esp32-elf.yaml"),
    ],
)
def test_toolchain_uses_longest_matching_arch_prefix(arch, expected):
    manifest = EosProjectGenerator().resolve_manifest(HardwareProfile(arch=arch))
    assert manifest.eos_toolchain == expected


def test_cortex_r_core_still_selects_r5_toolchain():
    profile = HardwareProfile(arch="arm", core="cortex-r5")
    manifest = EosProjectGenerator().resolve_manifest(profile)
    assert manifest.eos_toolchain == "arm-none-eabi-r5.yaml"
