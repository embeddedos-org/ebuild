# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""The build.yaml generated from a hardware profile must name a real compiler.

``toolchain.prefix`` is concatenated with the driver (``{prefix}gcc``), and
every shipped example writes it with its trailing hyphen
(``prefix: arm-none-eabi-``). EosConfigGenerator wrote ``arm-none-eabi``, so
the generated project resolved its compiler to ``arm-none-eabigcc`` -- and an
unrecognised arch got the prefix ``gcc``, i.e. ``gccgcc``.
"""

import pytest

from ebuild.build.toolchain import resolve_toolchain
from ebuild.core.config import load_config
from ebuild.eos_ai.eos_config_generator import EosConfigGenerator
from ebuild.eos_ai.eos_hw_analyzer import HardwareProfile


@pytest.mark.parametrize("arch, expected_cc", [
    ("arm", "arm-none-eabi-gcc"),
    ("riscv64", "riscv64-linux-gnu-gcc"),
    ("arm64", "aarch64-linux-gnu-gcc"),
    ("xtensa", "gcc"),
])
def test_generated_build_yaml_resolves_to_a_real_compiler_name(tmp_path, arch, expected_cc):
    profile = HardwareProfile(mcu="DEMO1", arch=arch)
    build_yaml = EosConfigGenerator(str(tmp_path)).generate_build_yaml(profile)

    cfg = load_config(build_yaml)

    assert resolve_toolchain(cfg.toolchain).cc == expected_cc
