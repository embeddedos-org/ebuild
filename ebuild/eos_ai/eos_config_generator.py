# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""EoS Config Generator — transforms HardwareProfile into build configs.

Generates validated YAML configs for:
- eos: board definition, product profile, HAL config
- eboot: flash layout, boot policy, image header
- ebuild: build.yaml with correct backends and toolchain
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml

from ebuild.eos_ai.eos_hw_analyzer import HardwareProfile


_FLASH_BASE_MAP = {
    "nrf": "0x00000000",
    "rp2040": "0x10000000",
    "esp32": "0x00000000",
}


def _flash_base_for(profile: "HardwareProfile") -> str:
    """Return the correct flash base address for this MCU."""
    key = (profile.mcu or "").lower()
    family = (profile.mcu_family or "").lower()
    for prefix, base in _FLASH_BASE_MAP.items():
        if key.startswith(prefix) or family.startswith(prefix):
            return base
    return "0x08000000"


class EosConfigGenerator:
    """Generates build/boot/OS configs from a HardwareProfile."""

    def __init__(self, output_dir: str = "_generated"):
        self.output_dir = Path(output_dir)

    def generate_all(self, profile: HardwareProfile) -> Dict[str, Path]:
        """Generate all config files from a hardware profile."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        outputs = {}

        outputs["board"] = self.generate_board_yaml(profile)
        outputs["boot"] = self.generate_boot_yaml(profile)
        outputs["build"] = self.generate_build_yaml(profile)
        outputs["eos_config"] = self.generate_eos_config_h(profile)

        return outputs

    def generate_board_yaml(self, profile: HardwareProfile) -> Path:
        """Generate eos-compatible board definition."""
        board = {
            "board": {
                "name": profile.mcu.lower() or "custom_board",
                "mcu": profile.mcu,
                "family": profile.mcu_family,
                "arch": profile.arch,
                "core": profile.core,
                "vendor": profile.vendor,
                "clock_hz": profile.clock_hz,
                "memory": {
                    "flash": profile.flash_size,
                    "ram": profile.ram_size,
                },
                "peripherals": [
                    {"name": p.name, "type": p.peripheral_type, "bus": p.bus}
                    for p in profile.peripherals
                ],
                "features": profile.features,
            }
        }

        path = self.output_dir / "board.yaml"
        path.write_text(yaml.dump(board, default_flow_style=False, sort_keys=False))
        return path

    def generate_boot_yaml(self, profile: HardwareProfile) -> Path:
        """Generate eboot-compatible boot configuration."""
        flash = profile.flash_size or 1024 * 1024
        stage0_size = max(8 * 1024, min(16 * 1024, flash // 32))
        stage1_size = min(64 * 1024, flash // 8)
        bootctl_size = 4096
        slot_size = (flash - stage0_size - stage1_size - bootctl_size * 2) // 2

        boot = {
            "boot": {
                "board": profile.mcu.lower() or "custom",
                "arch": profile.arch,
                "flash_base": _flash_base_for(profile),
                "flash_size": flash,
                "layout": {
                    "stage0": {"offset": "0x00000000", "size": stage0_size},
                    "stage1": {"offset": hex(stage0_size), "size": stage1_size},
                    "bootctl_primary": {
                        "offset": hex(stage0_size + stage1_size),
                        "size": bootctl_size,
                    },
                    "bootctl_backup": {
                        "offset": hex(stage0_size + stage1_size + bootctl_size),
                        "size": bootctl_size,
                    },
                    "slot_a": {
                        "offset": hex(stage0_size + stage1_size + bootctl_size * 2),
                        "size": slot_size,
                    },
                    "slot_b": {
                        "offset": hex(stage0_size + stage1_size + bootctl_size * 2 + slot_size),
                        "size": slot_size,
                    },
                },
                "policy": {
                    "max_boot_attempts": 3,
                    "watchdog_timeout_ms": 5000,
                    "require_signature": True,
                    "anti_rollback": True,
                },
                "image": {
                    "header_version": 1,
                    "hash_algo": "sha256",
                    "sign_algo": "ed25519",
                },
            }
        }

        path = self.output_dir / "boot.yaml"
        path.write_text(yaml.dump(boot, default_flow_style=False, sort_keys=False))
        return path

    def generate_build_yaml(self, profile: HardwareProfile) -> Path:
        """Generate ebuild build.yaml for the project."""
        _TOOLCHAIN_PREFIX = {
            "arm": "arm-none-eabi",
            "arm64": "aarch64-linux-gnu",
            "aarch64": "aarch64-linux-gnu",
            "riscv64": "riscv64-linux-gnu",
            "x86_64": "x86_64-linux-gnu",
            "mips": "mipsel-linux-gnu",
        }
        toolchain = _TOOLCHAIN_PREFIX.get(profile.arch, "gcc")

        build = {
            "project": {
                "name": f"{profile.mcu.lower()}-firmware",
                "version": "0.1.0",
            },
            "backend": "cmake",
            "toolchain": {
                "compiler": "gcc",
                "arch": profile.arch or "arm",
                "prefix": toolchain,
            },
            "cmake": {
                "build_type": "Release",
                "defines": {
                    "EOS_PLATFORM": "rtos",
                    **{k: "ON" for k in profile.get_eos_enables()},
                },
            },
        }

        path = self.output_dir / "build.yaml"
        path.write_text(yaml.dump(build, default_flow_style=False, sort_keys=False))
        return path

    def generate_eos_config_h(self, profile: HardwareProfile) -> Path:
        """Generate an eos product profile header."""
        lines = [
            f"/* Auto-generated EoS product config for {profile.mcu} */",
            "#ifndef EOS_GENERATED_CONFIG_H",
            "#define EOS_GENERATED_CONFIG_H",
            "",
            f'#define EOS_PRODUCT_NAME    "{profile.mcu.lower()}"',
            f'#define EOS_MCU             "{profile.mcu}"',
            f'#define EOS_ARCH            "{profile.arch}"',
            f'#define EOS_CORE            "{profile.core}"',
            f'#define EOS_VENDOR          "{profile.vendor}"',
            f"#define EOS_CLOCK_HZ         {profile.clock_hz}",
            f"#define EOS_FLASH_SIZE       {profile.flash_size}",
            f"#define EOS_RAM_SIZE         {profile.ram_size}",
            "",
        ]

        enables = profile.get_eos_enables()
        for flag, val in sorted(enables.items()):
            lines.append(f"#define {flag:<28s} {1 if val else 0}")

        lines.extend(["", "#endif /* EOS_GENERATED_CONFIG_H */", ""])

        path = self.output_dir / "eos_product_config.h"
        path.write_text("\n".join(lines))
        return path
