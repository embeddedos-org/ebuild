# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Whole-flash images for targets whose boot ROM loads from flash.

An Arm Cortex-M sim target is handed its ELF with QEMU's ``-kernel``. A
part such as the ESP32 boots its flash instead, so the ELF has to become
the byte image that lives on the chip: esptool's ``elf2image`` produces
what the boot ROM expects, and it is placed at its offset in an erased
flash of the right size.

This lives in ``ebuild/system/`` rather than ``ebuild/cli/`` because it is
an image workflow; ``ebuild/cli/golden_path.py`` only wires it into
``ebuild sim`` (AGENTS.md).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Protocol

#: Flash sizes esptool names, and their size in bytes.
FLASH_SIZES: Dict[str, int] = {
    "1MB": 1 << 20,
    "2MB": 2 << 20,
    "4MB": 4 << 20,
    "8MB": 8 << 20,
    "16MB": 16 << 20,
}

#: Erased NOR flash reads as 0xff.
ERASED_BYTE = b"\xff"


class _Log(Protocol):
    def debug(self, message: str) -> None: ...


class FlashImageError(Exception):
    """A flash image could not be produced. Carries an actionable message."""


def _decode(raw: bytes) -> str:
    """Decode tool output for a human, never raising.

    ``subprocess.run(text=True)`` decodes with the process locale and
    raises UnicodeDecodeError on anything it cannot read -- which would
    replace an actionable "esptool failed: ..." with a traceback from the
    decoder, exactly when the tool is already failing.
    """
    return raw.decode("utf-8", "replace")


def build_flash_image(
    spec: Dict, elf: Path, esptool: str, log: _Log
) -> Path:
    """Turn *elf* into a whole-flash image for a target that boots from flash.

    *spec* is the eos ``sim.yaml``; its ``image`` section names the chip,
    the flash mode/frequency/size and the offset the application sits at.
    Returns the path to the flash image.

    The esptool options use underscores: esptool 4.x (Ubuntu's package)
    accepts only those, and 5.x still does. The flash file is written here
    rather than by ``merge_bin``, whose padding option differs between 4.x
    and 5.x; the bytes are the same.

    Raises:
        FlashImageError: if esptool fails, or the image section names a
            flash size, offset or application that cannot produce an image.
    """
    img = spec["image"]
    app_bin = elf.with_suffix(".bin")
    flash = elf.with_suffix(".flash.bin")

    # _require_tool() returns a resolved executable path. It is one
    # argument, never a command line: splitting it would make
    # "/opt/ESP Tools/bin/esptool" into two, and would eat the
    # backslashes of a Windows path.
    cmd = [
        esptool,
        "--chip", str(img["chip"]),
        "elf2image",
        "--flash_mode", str(img["flash_mode"]),
        "--flash_freq", str(img["flash_freq"]),
        "--flash_size", str(img["flash_size"]),
        "-o", str(app_bin),
        str(elf),
    ]
    log.debug(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        detail = _decode(result.stderr or result.stdout).strip()
        raise FlashImageError(f"esptool elf2image failed:\n{detail}")

    size_name = str(img["flash_size"])
    if size_name not in FLASH_SIZES:
        raise FlashImageError(
            f"image.flash_size {size_name!r} is not one of "
            f"{', '.join(FLASH_SIZES)}"
        )
    capacity = FLASH_SIZES[size_name]

    try:
        offset = int(str(img["offset"]), 0)
    except ValueError as exc:
        raise FlashImageError(
            f"image.offset {img['offset']!r} is not an integer: {exc}"
        ) from exc
    # A negative offset is not "near the end": Python would index the
    # slice from the right and the assignment would *grow* the bytearray,
    # returning a flash file larger than the chip.
    if offset < 0:
        raise FlashImageError(f"image.offset {offset:#x} is negative")

    data = app_bin.read_bytes()
    if offset + len(data) > capacity:
        raise FlashImageError(
            f"{app_bin} ({len(data)} bytes) does not fit in {size_name} of "
            f"flash at {offset:#x}"
        )

    image = bytearray(ERASED_BYTE * capacity)
    image[offset:offset + len(data)] = data
    if len(image) != capacity:  # pragma: no cover - guarded above
        raise FlashImageError(
            f"flash image is {len(image)} bytes, expected {capacity}"
        )
    flash.write_bytes(bytes(image))
    return flash
