# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Flash and deploy utilities.

Provides functions to flash firmware images to target devices
using common flash tools (openocd, pyocd, nrfjprog, esptool).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


class FlashError(Exception):
    """Raised when flash/deploy operation fails."""


FLASH_TOOLS = {
    "openocd": ["openocd", "-f", "interface/stlink.cfg"],
    "pyocd": ["pyocd", "flash"],
    "nrfjprog": ["nrfjprog", "--program"],
    "esptool": ["esptool.py", "--chip", "esp32", "write_flash"],
    "stflash": ["st-flash", "write"],
}


def flash(
    image_path: Path,
    tool: str = "openocd",
    target: str = "stm32f4",
    address: int = 0x08000000,
    extra_args: Optional[list[str]] = None,
) -> None:
    """Flash a firmware image to the target device.

    Args:
        image_path: Path to the binary image.
        tool: Flash tool to use.
        target: Target MCU/board.
        address: Flash address.
        extra_args: Additional arguments for the flash tool.
    """
    if not image_path.exists():
        raise FlashError(f"Image not found: {image_path}")

    if tool not in FLASH_TOOLS:
        raise FlashError(f"Unknown flash tool: {tool}. Available: {list(FLASH_TOOLS.keys())}")

    cmd = list(FLASH_TOOLS[tool])

    if tool == "openocd":
        cmd.extend(["-f", f"target/{target}.cfg"])
        cmd.extend(["-c", f"program {image_path} {hex(address)} verify reset exit"])
    elif tool == "pyocd":
        cmd.extend([str(image_path), "--target", target, "--base-address", hex(address)])
    elif tool == "nrfjprog":
        cmd.extend([str(image_path), "--sectorerase", "--verify"])
    elif tool == "esptool":
        cmd.extend([hex(address), str(image_path)])
    elif tool == "stflash":
        cmd.extend([str(image_path), hex(address)])

    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise FlashError(f"Flash failed: {result.stderr.decode()}")


def reset(tool: str = "openocd", target: str = "stm32f4") -> None:
    """Reset the target device."""
    if tool == "openocd":
        cmd = [
            "openocd", "-f", "interface/stlink.cfg",
            "-f", f"target/{target}.cfg",
            "-c", "init", "-c", "reset run", "-c", "exit",
        ]
    elif tool == "pyocd":
        cmd = ["pyocd", "reset", "--target", target]
    elif tool == "nrfjprog":
        cmd = ["nrfjprog", "--reset"]
    else:
        raise FlashError(f"Reset not supported for tool: {tool}")

    subprocess.run(cmd, capture_output=True)
