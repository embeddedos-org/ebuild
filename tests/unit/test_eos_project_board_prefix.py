# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""The eos board definition must come from the most specific MCU prefix.

EOS_BOARD_MAP is matched with str.startswith(), and _resolve_eos_board took
the first hit in dict order. "esp32" is listed before "esp32s3"/"esp32c3",
"imx8" before "imx8x", "mips" before "mips64" and "pic32" before "pic32m",
so an ESP32-S3 project was given boards/esp32.yaml (the original Xtensa LX6
ESP32) and the specific entries were never reachable. The eboot board lookup
(board_dir_for_mcu) already uses the longest prefix.
"""
import pytest

from ebuild.eos_ai.eos_hw_analyzer import HardwareProfile
from ebuild.eos_ai.eos_project_generator import EosProjectGenerator


@pytest.mark.parametrize(
    "mcu, expected",
    [
        ("esp32s3", "generic-esp32s3.yaml"),
        ("ESP32C3", "generic-esp32c3.yaml"),
        ("imx8x", "generic-cortex-a35.yaml"),
        ("mips64r6", "generic-mips64.yaml"),
        ("pic32mz", "generic-pic32.yaml"),
        # Unchanged mappings for the shorter prefixes.
        ("esp32", "esp32.yaml"),
        ("imx8mq", "imx8m.yaml"),
        ("stm32f407", "stm32f4.yaml"),
        ("nrf52840", "nrf52840.yaml"),
    ],
)
def test_eos_board_uses_longest_matching_mcu_prefix(mcu, expected):
    manifest = EosProjectGenerator().resolve_manifest(HardwareProfile(mcu=mcu))
    assert manifest.eos_files == [f"boards/{expected}"]


def test_unknown_mcu_has_no_eos_board():
    manifest = EosProjectGenerator().resolve_manifest(HardwareProfile(mcu="zz9000"))
    assert manifest.eos_files == []
