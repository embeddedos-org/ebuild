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
    "esptool": ["esptool.py"],
    "stflash": ["st-flash"],
}


#: Chip names esptool accepts for --chip.
_ESPTOOL_CHIPS = (
    "esp8266", "esp32", "esp32s2", "esp32s3", "esp32c2", "esp32c3",
    "esp32c5", "esp32c6", "esp32c61", "esp32h2", "esp32p4",
)


def _esptool_chip(target: str) -> str:
    """esptool's --chip value for *target*.

    The target is lower-cased with '-' and '_' dropped, then matched against
    the chip names esptool knows: an exact match wins, otherwise the longest
    chip name the target starts with, so a board id names its chip
    (``ESP32-S3`` and ``esp32s3-devkitc`` give ``esp32s3``, ``esp32dev``
    gives ``esp32``). esptool refuses to flash a chip other than the one
    --chip names. A target that matches no chip, such as the CLI's default
    ``stm32f4``, keeps the previous ``esp32``.
    """
    name = target.lower().replace("-", "").replace("_", "")
    if name in _ESPTOOL_CHIPS:
        return name
    prefixes = [chip for chip in _ESPTOOL_CHIPS if name.startswith(chip)]
    return max(prefixes, key=len) if prefixes else "esp32"


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
        cmd.extend(extra_args or [])
        image_str = str(image_path)
        if image_str.count("{") != image_str.count("}"):
            raise FlashError(
                f"Image path has unbalanced braces, which OpenOCD's Tcl "
                f"parser cannot group: {image_path}"
            )
        # -c's value is a single argv element, but OpenOCD re-parses it as a
        # Tcl command line: an unquoted space in image_path splits it into
        # extra "program" arguments instead of one filename. Tcl brace
        # grouping keeps it one token; subprocess.run (no shell) already
        # passes braces through literally, so this needs no other escaping
        # for spaces or backslashes.
        cmd.extend(["-c", f"program {{{image_path}}} {hex(address)} verify reset exit"])
    elif tool == "pyocd":
        cmd.extend([str(image_path), "--target", target, "--base-address", hex(address)])
        cmd.extend(extra_args or [])
    elif tool == "nrfjprog":
        cmd.extend([str(image_path), "--sectorerase", "--verify"])
        cmd.extend(extra_args or [])
    elif tool == "esptool":
        cmd.extend(["--chip", _esptool_chip(target)])
        cmd.extend(extra_args or [])
        cmd.extend(["write_flash", hex(address), str(image_path)])
    elif tool == "stflash":
        cmd.extend(extra_args or [])
        cmd.extend(["write", str(image_path), hex(address)])

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise FlashError(
            f"Flash failed: {result.stderr.decode(errors='replace').strip()}"
        )


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

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise FlashError(
            f"Reset failed: {result.stderr.decode(errors='replace').strip()}"
        )
