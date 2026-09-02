# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Flash and RAM footprint of a built artifact.

The MLP developer walk ends with a build that says how much of the board it
just used:

    Flash: 384 KB
    RAM:    72 KB
    Ready to flash.

A developer who has to run `arm-none-eabi-size` themselves and remember which
columns to add is not being told; they are being left to find out.

The accounting matches `scripts/measure_footprint.py` in the eos repo, so the
two tools cannot disagree about what a number means:

    text   code + read-only data      -> flash
    data   initialised writable data  -> flash AND RAM
    bss    zero-initialised data      -> RAM only

    flash = text + data
    ram   = data + bss

`data` is charged to both because it is stored in flash and copied to RAM at
startup. Reading `size`'s "dec" column instead understates RAM.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

#: Capacity of the reference part for each board family, in bytes.
#:
#: These are the parts `ebuild new --board` scaffolds against. A family spans
#: several densities -- an STM32F407 has 1 MB of flash and an STM32F401 has
#: 256 KB -- so a project that cares states its own numbers under `memory:` in
#: its board YAML, which takes precedence over anything here.
#:
#: Boards that boot from removable or external storage, and Linux-class parts
#: with no fixed budget, are absent on purpose: a made-up ceiling is worse
#: than no ceiling, because a percentage reads as authoritative.
_REFERENCE_CAPACITY: Dict[str, Tuple[int, int]] = {
    # board       flash            ram
    "nrf52":     (512 * 1024,      64 * 1024),    # nRF52832
    "nrf52840":  (1024 * 1024,    256 * 1024),    # nRF52840
    "stm32f4":   (1024 * 1024,    192 * 1024),    # STM32F407
    "stm32h7":   (2048 * 1024,   1024 * 1024),    # STM32H743
    "rp2040":    (2048 * 1024,    264 * 1024),    # RP2040 + 2 MB QSPI
    "esp32":     (4096 * 1024,    520 * 1024),    # ESP32-WROOM-32, 4 MB module
    "tms570":    (3072 * 1024,    256 * 1024),    # TMS570LS3137
}

_SIZE_LINE = re.compile(
    r"^\s*(?P<text>\d+)\s+(?P<data>\d+)\s+(?P<bss>\d+)\s+\d+\s+[0-9a-fA-F]+\s"
)

#: Apple's size(1) prints "__TEXT __DATA __OBJC others" instead of the
#: Berkeley "text data bss" columns. _SIZE_LINE matches that row too and
#: read __OBJC -- always 0 -- as bss, so every footprint measured on macOS
#: silently reported RAM without any zero-initialised data in it.
_MACHO_COLUMNS = re.compile(r"^\s*__TEXT\s+__DATA\s+__OBJC\s+others\b")
_MACHO_SEGMENT = re.compile(r"^Segment\s+(?P<name>\S+?):\s+(?P<size>\d+)")
_MACHO_SECTION = re.compile(
    r"^\s+Section\s+(?P<name>\S+?):\s+(?P<size>\d+)(?P<zero>\s*\(zerofill\))?"
)


class FootprintError(RuntimeError):
    """Raised when a footprint cannot be measured."""


@dataclass(frozen=True)
class Footprint:
    """Section sizes of one artifact, in bytes."""

    text: int
    data: int
    bss: int

    @property
    def flash(self) -> int:
        """Bytes occupied in flash: code, read-only data, and the stored
        image of initialised writable data."""
        return self.text + self.data

    @property
    def ram(self) -> int:
        """Bytes occupied in RAM once started: initialised data copied out of
        flash, plus the zero-initialised region."""
        return self.data + self.bss


def find_size_tool(toolchain_prefix: Optional[str] = None) -> Optional[str]:
    """Locate the `size` binary for a toolchain.

    A cross build must be measured with its own `size`; the host one reads an
    ARM ELF's headers but is not guaranteed to across every binutils version,
    and silently reporting host numbers for a firmware image is worse than
    reporting none. Returns None when nothing suitable is installed.
    """
    if toolchain_prefix and toolchain_prefix != "host":
        cross = shutil.which(f"{toolchain_prefix}-size")
        if cross:
            return cross
        # No fallback to the host tool: the numbers would be for a different
        # target and nothing in the output would say so.
        return None
    return shutil.which("size")


def _run_size(tool: str, args: list, artifact: Path):
    """Run the size tool, turning every failure mode into FootprintError."""
    try:
        proc = subprocess.run([tool] + args, capture_output=True,
                              text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FootprintError(f"{tool} failed on {artifact}: {exc}") from exc
    if proc.returncode != 0:
        raise FootprintError(
            f"{tool} exited {proc.returncode} on {artifact}: "
            f"{(proc.stderr or proc.stdout).strip()[:200]}"
        )
    return proc


def _measure_macho(tool: str, artifact: Path) -> "Footprint":
    """Section sizes from Apple size(1), which needs -m to report them.

    Sections rather than segments: a segment is page-aligned, so __TEXT
    reads as 16 KB for 112 bytes of code. The Berkeley numbers this
    mirrors are section sizes, and the two tools must not disagree about
    what a number means.
    """
    proc = _run_size(tool, ["-m", str(artifact)], artifact)
    text = data = bss = 0
    segment = ""
    for line in proc.stdout.splitlines():
        seg = _MACHO_SEGMENT.match(line)
        if seg:
            segment = seg.group("name")
            continue
        sec = _MACHO_SECTION.match(line)
        if not sec:
            continue
        size = int(sec.group("size"))
        if sec.group("zero"):
            bss += size          # zerofill: RAM only, never stored
        elif segment == "__TEXT":
            text += size
        elif segment not in ("__PAGEZERO", "__LINKEDIT"):
            data += size
    if not (text or data or bss):
        raise FootprintError(
            f"could not read any section size from {tool} -m output "
            f"for {artifact}"
        )
    return Footprint(text=text, data=data, bss=bss)


def measure(artifact: Path, size_tool: Optional[str] = None) -> Footprint:
    """Section sizes of ``artifact``.

    Raises FootprintError rather than returning zeros, so a build cannot
    report "Flash: 0 KB" when the truth is that nothing was measured.
    """
    artifact = Path(artifact)
    if not artifact.is_file():
        raise FootprintError(f"no artifact to measure at {artifact}")

    tool = size_tool or shutil.which("size")
    if not tool:
        raise FootprintError(
            "no 'size' tool on PATH, so the footprint cannot be measured "
            "(install binutils, or the toolchain's binutils for a cross build)"
        )

    proc = _run_size(tool, [str(artifact)], artifact)

    for line in proc.stdout.splitlines():
        # Apple size(1) leads with a column header naming Mach-O segments.
        # Its data row matches _SIZE_LINE, so without this the __OBJC
        # column is silently taken for bss.
        if _MACHO_COLUMNS.match(line):
            return _measure_macho(tool, artifact)
        m = _SIZE_LINE.match(line)
        if m:
            return Footprint(text=int(m.group("text")),
                             data=int(m.group("data")),
                             bss=int(m.group("bss")))

    raise FootprintError(
        f"could not read a size line from {tool} output for {artifact}"
    )


def board_capacity(board: Optional[str],
                  board_config: Optional[dict] = None
                  ) -> Tuple[Optional[int], Optional[int]]:
   """Flash and RAM capacity for a board, or (None, None) when unknown.


   A project's own board YAML wins over the reference table: `memory.flash_size`
   and `memory.ram_size` are what the hardware descriptions in `hardware/board/`
   already use.
   """
   reference = _REFERENCE_CAPACITY.get(board.lower()) if board else None
   if board_config:
       memory = board_config.get("memory") or {}
       flash = _as_bytes(memory.get("flash_size"))
       ram = _as_bytes(memory.get("ram_size"))
       if flash or ram:
           if flash is None and reference:
               flash = reference[0]
           if ram is None and reference:
               ram = reference[1]
           return flash, ram
   if reference:
       return reference
   return None, None


def _as_bytes(value) -> Optional[int]:
    """Board YAMLs write sizes as ints or as hex strings like ``0x200000``."""
    if value is None:
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    try:
        parsed = int(str(value), 0)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def format_size(n: int) -> str:
    """Human-readable size, at the granularity a developer reasons in."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.2f} MB"


def format_report(fp: Footprint,
                  flash_capacity: Optional[int] = None,
                  ram_capacity: Optional[int] = None) -> str:
    """The build's closing footprint block.

    A percentage is shown only where the capacity is actually known. Printing
    one against a guessed ceiling would be the most misleading number in the
    whole build.
    """
    lines = []
    for label, used, cap in (("Flash", fp.flash, flash_capacity),
                             ("RAM  ", fp.ram, ram_capacity)):
        if cap:
            pct = 100.0 * used / cap
            lines.append(f"  {label}: {format_size(used):>10}"
                         f"  of {format_size(cap):>10}  ({pct:.1f}%)")
        else:
            lines.append(f"  {label}: {format_size(used):>10}")
    return "\n".join(lines)


def over_budget(fp: Footprint,
                flash_capacity: Optional[int] = None,
                ram_capacity: Optional[int] = None) -> Optional[str]:
    """A message naming the region that does not fit, or None.

    Being told at the end of a build beats being told by a linker script, and
    beats being told by a board that will not boot.
    """
    if flash_capacity and fp.flash > flash_capacity:
        return (f"flash usage {format_size(fp.flash)} exceeds the board's "
                f"{format_size(flash_capacity)}")
    if ram_capacity and fp.ram > ram_capacity:
        return (f"RAM usage {format_size(fp.ram)} exceeds the board's "
                f"{format_size(ram_capacity)}")
    return None
