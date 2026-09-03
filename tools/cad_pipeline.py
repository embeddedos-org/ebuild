#!/usr/bin/env python3
"""
ebuild CAD Pipeline — eFab KiCad → ebuild artifacts
=====================================================
Reads a KiCad .kicad_pcb file containing EoS memory map annotations
(eos_mmap, eos_cpu, eos_peripheral) and generates:

  1. A GNU LD linker script  (output_dir/eos_generated.ld)
  2. A Device Tree Source    (output_dir/eos_generated.dts)
  3. An ebuild recipe YAML   (output_dir/eos_recipe.yaml)
  4. A CMake toolchain file  (output_dir/eos_toolchain.cmake)

Usage:
    python3 cad_pipeline.py <board.kicad_pcb> <output_dir>

Example:
    python3 cad_pipeline.py samples/eos_reference_board.kicad_pcb build/
"""

import re
import sys
import os
import json
from dataclasses import dataclass, field
from typing import List

# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class MemoryRegion:
    name: str
    base: int
    size: int
    flags: str   # rx, rw, rwx

@dataclass
class CpuDef:
    arch: str = "aarch64"
    core: str = "cortex-a57"
    freq_mhz: int = 1000
    endian: str = "little"
    fpu: str = "neon-fp-armv8"
    stack_size: int = 0x10000
    entry_symbol: str = "eos_kernel_entry"
    boot_symbol: str = "_start"

@dataclass
class Peripheral:
    name: str
    compatible: str
    base: int
    irq: int

@dataclass
class BoardDef:
    title: str = "EoS Board"
    revision: str = "1.0"
    company: str = "EmbeddedOS Foundation"
    cpu: CpuDef = field(default_factory=CpuDef)
    memory: List[MemoryRegion] = field(default_factory=list)
    peripherals: List[Peripheral] = field(default_factory=list)

# ── Parser ────────────────────────────────────────────────────────────────────

def _sexpr_body(content: str, head: str) -> List[str]:
    """Return the body of every ``(head ...)`` block, paren-matched.

    A non-greedy ``(eos_cpu(.*?))`` regex stops at the FIRST ``)``, which in

        (eos_cpu
          (arch "aarch64")
          (core "cortex-a57")

    is the one closing ``(arch ...)``. Every attribute after the first then
    fell out of the match and silently took its dataclass default, so a board
    declaring cortex-a72 at 1800 MHz produced artifacts describing cortex-a57
    at 1000, and every ``eos_peripheral`` came out as
    ``unknown/unknown/0x0/irq -1``. Nothing reported an error -- the region and
    peripheral *counts* were right, so the output looked plausible.

    Depth counting handles nesting; quoted strings are skipped so a parenthesis
    inside a name cannot unbalance the scan.
    """
    bodies = []
    for m in re.finditer(r"\(" + re.escape(head) + r"(?![A-Za-z0-9_])", content):
        i = m.end()
        start = i
        depth = 1
        in_str = False
        while i < len(content) and depth:
            c = content[i]
            if in_str:
                if c == "\\":
                    i += 1
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            i += 1
        if depth == 0:
            bodies.append(content[start:i - 1])
    return bodies


def parse_kicad_pcb(path: str) -> BoardDef:
    """Parse a KiCad PCB file and extract EoS-specific annotations."""
    board = BoardDef()

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Title block
    m = re.search(r'\(title\s+"([^"]+)"\)', content)
    if m:
        board.title = m.group(1)
    m = re.search(r'\(rev\s+"([^"]+)"\)', content)
    if m:
        board.revision = m.group(1)
    m = re.search(r'\(company\s+"([^"]+)"\)', content)
    if m:
        board.company = m.group(1)

    # Memory map: (eos_mmap "NAME" "0xBASE" "0xSIZE" "FLAGS")
    for m in re.finditer(
        r'\(eos_mmap\s+"([^"]+)"\s+"(0x[0-9A-Fa-f]+)"\s+"(0x[0-9A-Fa-f]+)"\s+"([^"]+)"\)',
        content
    ):
        board.memory.append(MemoryRegion(
            name=m.group(1),
            base=int(m.group(2), 16),
            size=int(m.group(3), 16),
            flags=m.group(4),
        ))

    # CPU definition
    cpu_bodies = _sexpr_body(content, "eos_cpu")
    if cpu_bodies:
        cb = cpu_bodies[0]
        def _attr(key):
            mm = re.search(rf'\({key}\s+"([^"]+)"\)', cb)
            return mm.group(1) if mm else None
        def _attr_int(key):
            mm = re.search(rf'\({key}\s+(\d+)\)', cb)
            return int(mm.group(1)) if mm else None

        board.cpu = CpuDef(
            arch=_attr("arch") or "aarch64",
            core=_attr("core") or "cortex-a57",
            freq_mhz=_attr_int("freq_mhz") or 1000,
            endian=_attr("endian") or "little",
            fpu=_attr("fpu") or "neon-fp-armv8",
            stack_size=int(_attr("stack_size") or "0x10000", 16),
            entry_symbol=_attr("entry_symbol") or "eos_kernel_entry",
            boot_symbol=_attr("boot_symbol") or "_start",
        )

    # Peripherals: (eos_peripheral (name "...") (compatible "...") (base "...") (irq N))
    for pb in _sexpr_body(content, "eos_peripheral"):
        def _p(key):
            mm = re.search(rf'\({key}\s+"([^"]+)"\)', pb)
            return mm.group(1) if mm else None
        def _pi(key):
            mm = re.search(rf'\({key}\s+(-?\d+)\)', pb)
            return int(mm.group(1)) if mm else -1

        board.peripherals.append(Peripheral(
            name=_p("name") or "unknown",
            compatible=_p("compatible") or "unknown",
            base=int(_p("base") or "0x0", 16),
            irq=_pi("irq"),
        ))

    return board

# ── Generators ────────────────────────────────────────────────────────────────

def gen_linker_script(board: BoardDef) -> str:
    """Generate a GNU LD linker script from the board memory map."""
    cpu = board.cpu

    # Find key regions
    def find(name_substr):
        for r in board.memory:
            if name_substr.upper() in r.name.upper():
                return r
        return None

    flash  = find("FLASH")
    ram    = find("RAM_LPDDR4") or find("RAM")
    heap   = find("HEAP")
    stack_size = cpu.stack_size

    if not flash or not ram:
        raise ValueError("Board must define at least FLASH and RAM memory regions")

    lines = [
        f"/* EoS Generated Linker Script",
        f" * Board:  {board.title} rev {board.revision}",
        f" * CPU:    {cpu.core} ({cpu.arch})",
        f" * Tool:   ebuild cad_pipeline.py",
        f" * DO NOT EDIT — regenerate from {board.title}.kicad_pcb",
        f" */",
        f"",
        f"OUTPUT_FORMAT(\"elf64-littleaarch64\")",
        f"OUTPUT_ARCH(aarch64)",
        f"ENTRY({cpu.boot_symbol})",
        f"",
        f"MEMORY {{",
    ]

    for r in board.memory:
        flag_map = {"rx": "(rx)", "rw": "(rw)", "rwx": "(rwx)"}
        flags = flag_map.get(r.flags, "(rw)")
        lines.append(
            f"    {r.name:<20} {flags:<6} : ORIGIN = {r.base:#010x}, LENGTH = {r.size:#010x}"
        )

    lines += [
        f"}}",
        f"",
        f"/* Stack size: {stack_size:#x} bytes */",
        f"_stack_size = {stack_size:#x};",
        f"",
        f"SECTIONS {{",
        f"    . = ORIGIN(RAM_LPDDR4) + 0x00080000;  /* kernel load offset */",
        f"",
        f"    .text : {{",
        f"        KEEP(*(.text.boot))",
        f"        *(.text*)",
        f"        *(.rodata*)",
        f"        . = ALIGN(8);",
        f"    }} > RAM_LPDDR4",
        f"",
        f"    .data : {{",
        f"        _data_start = .;",
        f"        *(.data*)",
        f"        . = ALIGN(8);",
        f"        _data_end = .;",
        f"    }} > RAM_LPDDR4",
        f"",
        f"    .bss (NOLOAD) : {{",
        f"        _bss_start = .;",
        f"        *(.bss*)",
        f"        *(COMMON)",
        f"        . = ALIGN(8);",
        f"        _bss_end = .;",
        f"    }} > RAM_LPDDR4",
        f"",
        f"    .stack (NOLOAD) : {{",
        f"        . = ALIGN(16);",
        f"        _stack_bottom = .;",
        f"        . += _stack_size;",
        f"        _stack_top = .;",
        f"    }} > RAM_LPDDR4",
        f"",
        f"    /DISCARD/ : {{ *(.comment) *(.note*) *(.eh_frame*) }}",
        f"}}",
    ]
    return "\n".join(lines) + "\n"


def gen_device_tree(board: BoardDef) -> str:
    """Generate a Device Tree Source (.dts) from the board definition."""
    cpu = board.cpu

    def find(name_substr):
        for r in board.memory:
            if name_substr.upper() in r.name.upper():
                return r
        return None

    ram = find("RAM_LPDDR4") or find("RAM")

    lines = [
        f"/dts-v1/;",
        f"",
        f"/* EoS Generated Device Tree",
        f" * Board:  {board.title} rev {board.revision}",
        f" * CPU:    {cpu.core} ({cpu.arch})",
        f" * Tool:   ebuild cad_pipeline.py",
        f" * DO NOT EDIT — regenerate from {board.title}.kicad_pcb",
        f" */",
        f"",
        f"/ {{",
        f"    #address-cells = <2>;",
        f"    #size-cells = <2>;",
        f"    compatible = \"eos,{board.title.lower().replace(' ', '-')}\";",
        f"    model = \"{board.title}\";",
        f"",
        f"    chosen {{",
        f"        bootargs = \"console=ttyAMA0,115200 root=/dev/mmcblk0p2 rw\";",
        f"        stdout-path = \"serial0:115200n8\";",
        f"    }};",
        f"",
        f"    cpus {{",
        f"        #address-cells = <1>;",
        f"        #size-cells = <0>;",
        f"",
        f"        cpu@0 {{",
        f"            device_type = \"cpu\";",
        f"            compatible = \"arm,{cpu.core}\";",
        f"            reg = <0>;",
        f"            clock-frequency = <{cpu.freq_mhz * 1_000_000}>;",
        f"        }};",
        f"    }};",
        f"",
    ]

    if ram:
        lines += [
            f"    memory@{ram.base:x} {{",
            f"        device_type = \"memory\";",
            f"        reg = <0x0 {ram.base:#010x} 0x0 {ram.size:#010x}>;",
            f"    }};",
            f"",
        ]

    lines += [
        f"    soc {{",
        f"        #address-cells = <2>;",
        f"        #size-cells = <2>;",
        f"        compatible = \"simple-bus\";",
        f"        ranges;",
        f"",
    ]

    for p in board.peripherals:
        if p.irq < 0:
            irq_line = ""
        else:
            irq_line = f"\n            interrupts = <0 {p.irq} 4>;"

        lines += [
            f"        {p.name}: {p.name.split('0')[0]}@{p.base:x} {{",
            f"            compatible = \"{p.compatible}\";",
            f"            reg = <0x0 {p.base:#010x} 0x0 0x1000>;{irq_line}",
            f"            status = \"okay\";",
            f"        }};",
            f"",
        ]

    lines += [
        f"    }};",
        f"}};",
    ]
    return "\n".join(lines) + "\n"


def gen_recipe_yaml(board: BoardDef) -> str:
    """Generate an ebuild recipe YAML that drives the full build pipeline."""
    cpu = board.cpu
    lines = [
        f"# EoS ebuild Recipe — auto-generated from {board.title}.kicad_pcb",
        f"# DO NOT EDIT — regenerate with: ebuild cad_pipeline.py <board.kicad_pcb> <outdir>",
        f"",
        f"recipe:",
        f"  name: eos-{board.title.lower().replace(' ', '-')}",
        f"  version: {board.revision}",
        f"  description: \"{board.title} — EoS full-stack build\"",
        f"",
        f"target:",
        f"  arch: {cpu.arch}",
        f"  cpu: {cpu.core}",
        f"  endian: {cpu.endian}",
        f"  fpu: {cpu.fpu}",
        f"  freq_mhz: {cpu.freq_mhz}",
        f"  cross_compile: aarch64-linux-gnu-",
        f"",
        f"layers:",
        f"  - name: ebuild",
        f"    repo: ebuild",
        f"    build: cmake",
        f"",
        f"  - name: eboot",
        f"    repo: eBoot",
        f"    build: cmake",
        f"    depends: [ebuild]",
        f"    cmake_args:",
        f"      - -DBOARD=qemu_arm64",
        f"      - -DCROSS_COMPILE=aarch64-linux-gnu-",
        f"",
        f"  - name: eos-kernel",
        f"    repo: eos",
        f"    build: cmake",
        f"    depends: [eboot]",
        f"    cmake_args:",
        f"      - -DTARGET_ARCH={cpu.arch}",
        f"      - -DTARGET_CPU={cpu.core}",
        f"      - -DCROSS_COMPILE=aarch64-linux-gnu-",
        f"",
        f"  - name: middleware",
        f"    repos: [eAI, eNI, eosllm, eDB]",
        f"    build: python",
        f"    depends: [eos-kernel]",
        f"",
        f"  - name: apps",
        f"    repos: [eVera, eBrowser, eIPC, eOffice, EoStudio, EoSim, eApps]",
        f"    build: mixed",
        f"    depends: [middleware]",
        f"",
        f"image:",
        f"  linker_script: eos_generated.ld",
        f"  device_tree: eos_generated.dts",
        f"  entry: {cpu.entry_symbol}",
        f"  boot: {cpu.boot_symbol}",
        f"  format: elf64",
        f"  output: dist/eos-{board.title.lower().replace(' ', '-')}.elf",
        f"",
        f"memory_map:",
    ]
    for r in board.memory:
        lines.append(f"  {r.name}: {{ base: {r.base:#010x}, size: {r.size:#010x}, flags: {r.flags} }}")

    lines += [
        f"",
        f"peripherals:",
    ]
    for p in board.peripherals:
        lines.append(f"  {p.name}: {{ compatible: \"{p.compatible}\", base: {p.base:#010x}, irq: {p.irq} }}")

    return "\n".join(lines) + "\n"


def gen_cmake_toolchain(board: BoardDef) -> str:
    """Generate a CMake toolchain file for cross-compilation."""
    cpu = board.cpu
    march = "armv8-a"
    if "cortex-a72" in cpu.core:
        march = "armv8-a+crc"
    elif "cortex-m4" in cpu.core:
        march = "armv7e-m+fp"

    return f"""# EoS Generated CMake Toolchain
# Board:  {board.title} rev {board.revision}
# CPU:    {cpu.core} ({cpu.arch})
# Tool:   ebuild cad_pipeline.py
# DO NOT EDIT — regenerate from {board.title}.kicad_pcb

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR {cpu.arch})

set(CROSS_COMPILE "aarch64-linux-gnu-")
set(CMAKE_C_COMPILER   ${{CROSS_COMPILE}}gcc)
set(CMAKE_CXX_COMPILER ${{CROSS_COMPILE}}g++)
set(CMAKE_ASM_COMPILER ${{CROSS_COMPILE}}as)
set(CMAKE_AR           ${{CROSS_COMPILE}}ar)
set(CMAKE_OBJCOPY      ${{CROSS_COMPILE}}objcopy)
set(CMAKE_OBJDUMP      ${{CROSS_COMPILE}}objdump)
set(CMAKE_SIZE         ${{CROSS_COMPILE}}size)

set(CPU_FLAGS "-march={march} -mcpu={cpu.core} -mabi=lp64")
set(CMAKE_C_FLAGS_INIT   "${{CPU_FLAGS}} -ffreestanding -fno-pic -nostdlib")
set(CMAKE_ASM_FLAGS_INIT "${{CPU_FLAGS}}")
set(CMAKE_EXE_LINKER_FLAGS_INIT "-T ${{CMAKE_CURRENT_SOURCE_DIR}}/eos_generated.ld -nostdlib -static")

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# EoS memory map (from {board.title}.kicad_pcb)
"""  + "\n".join(
        f"set(EOS_{r.name}_BASE  {r.base:#010x})"
        for r in board.memory
    ) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <board.kicad_pcb> <output_dir>")
        sys.exit(1)

    pcb_path   = sys.argv[1]
    output_dir = sys.argv[2]
    os.makedirs(output_dir, exist_ok=True)

    print(f"[ebuild cad_pipeline] Parsing: {pcb_path}")
    board = parse_kicad_pcb(pcb_path)

    print(f"[ebuild cad_pipeline] Board:   {board.title} rev {board.revision}")
    print(f"[ebuild cad_pipeline] CPU:     {board.cpu.core} ({board.cpu.arch})")
    print(f"[ebuild cad_pipeline] Memory regions: {len(board.memory)}")
    print(f"[ebuild cad_pipeline] Peripherals:    {len(board.peripherals)}")

    # Generate artifacts
    artifacts = {
        "eos_generated.ld":        gen_linker_script(board),
        "eos_generated.dts":       gen_device_tree(board),
        "eos_recipe.yaml":         gen_recipe_yaml(board),
        "eos_toolchain.cmake":     gen_cmake_toolchain(board),
    }

    for filename, content in artifacts.items():
        out_path = os.path.join(output_dir, filename)
        # encoding="utf-8" to match the read side. The generated banners carry
        # em dashes and box-drawing characters, and open() without an encoding
        # uses the platform default -- cp1252 on Windows -- so the artifacts
        # came out mangled there while the parser had always read UTF-8.
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[ebuild cad_pipeline] Generated: {out_path}")

    # Write a JSON manifest for CI consumption
    manifest = {
        "board": board.title,
        "revision": board.revision,
        "cpu": {
            "arch": board.cpu.arch,
            "core": board.cpu.core,
            "freq_mhz": board.cpu.freq_mhz,
        },
        "memory_regions": [
            {"name": r.name, "base": hex(r.base), "size": hex(r.size), "flags": r.flags}
            for r in board.memory
        ],
        "peripherals": [
            {"name": p.name, "compatible": p.compatible, "base": hex(p.base), "irq": p.irq}
            for p in board.peripherals
        ],
        "generated_artifacts": list(artifacts.keys()),
    }
    manifest_path = os.path.join(output_dir, "board_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[ebuild cad_pipeline] Manifest: {manifest_path}")
    print(f"[ebuild cad_pipeline] Done. {len(artifacts)+1} files written to {output_dir}/")


if __name__ == "__main__":
    main()
