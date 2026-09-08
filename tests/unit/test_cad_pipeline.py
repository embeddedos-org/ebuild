# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for tools/cad_pipeline.py.

The pipeline had no test and no input in this repository -- the only board it
was ever pointed at lives in embeddedos-org/eFab, which does not exist, so it
had never been run. `samples/eos_reference_board.kicad_pcb` gives it one.

The bug these pin: `(eos_cpu(.*?))` and `(eos_peripheral(.*?))` are non-greedy,
so each stopped at the first `)` -- the one closing the block's *first*
attribute. Everything after it silently took a dataclass default. Counts stayed
correct, so the output looked right while describing different hardware.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "cad_pipeline.py"
SAMPLE = REPO / "samples" / "eos_reference_board.kicad_pcb"

ARTIFACTS = [
    "eos_generated.ld",
    "eos_generated.dts",
    "eos_recipe.yaml",
    "eos_toolchain.cmake",
    "board_manifest.json",
]


def _load_tool():
    spec = importlib.util.spec_from_file_location("cad_pipeline", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sample_board_exists():
    """The tool needs an input in this repo to be runnable at all."""
    assert SAMPLE.is_file(), f"missing {SAMPLE}"


def test_pipeline_generates_every_artifact(tmp_path):
    rc = subprocess.run(
        [sys.executable, str(TOOL), str(SAMPLE), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert rc.returncode == 0, rc.stderr
    for name in ARTIFACTS:
        produced = tmp_path / name
        assert produced.is_file(), f"{name} not generated"
        assert produced.stat().st_size > 0, f"{name} is empty"
        # The parser reads UTF-8; the writer must produce it. Without an
        # explicit encoding, open() uses the platform default and these came
        # out cp1252 on Windows.
        produced.read_text(encoding="utf-8")


def test_every_cpu_attribute_is_parsed_not_defaulted():
    """A non-greedy block regex kept only the first attribute of (eos_cpu ...).

    Every value below differs from CpuDef's default, so a parser that drops
    them reports the defaults and fails here.
    """
    mod = _load_tool()
    board = mod.parse_kicad_pcb(str(SAMPLE))

    assert board.cpu.arch == "aarch64"
    assert board.cpu.core == "cortex-a57"
    assert board.cpu.freq_mhz == 1000
    assert board.cpu.endian == "little"
    assert board.cpu.fpu == "neon-fp-armv8"
    assert board.cpu.stack_size == 0x10000
    assert board.cpu.entry_symbol == "eos_kernel_entry"
    assert board.cpu.boot_symbol == "_start"


def test_cpu_attributes_track_the_file_not_the_defaults(tmp_path):
    """The decisive check: a board that is not the default must not read back
    as the default. Against the unfixed parser this returns cortex-a57/1000."""
    mod = _load_tool()
    altered = (
        SAMPLE.read_text(encoding="utf-8")
        .replace('"cortex-a57"', '"cortex-a72"')
        .replace("(freq_mhz 1000)", "(freq_mhz 1800)")
        .replace('"eos_kernel_entry"', '"my_entry"')
    )
    board_file = tmp_path / "alt.kicad_pcb"
    board_file.write_text(altered, encoding="utf-8")

    board = mod.parse_kicad_pcb(str(board_file))
    assert board.cpu.core == "cortex-a72"
    assert board.cpu.freq_mhz == 1800
    assert board.cpu.entry_symbol == "my_entry"


def test_peripheral_fields_are_parsed():
    """Every peripheral used to come back unknown/unknown/0x0/irq -1."""
    mod = _load_tool()
    board = mod.parse_kicad_pcb(str(SAMPLE))

    assert len(board.peripherals) == 2
    by_name = {p.name: p for p in board.peripherals}

    assert set(by_name) == {"uart0", "rtc0"}
    assert by_name["uart0"].compatible == "arm,pl011"
    assert by_name["uart0"].base == 0x09000000
    assert by_name["uart0"].irq == 33
    assert by_name["rtc0"].compatible == "arm,pl031"
    assert by_name["rtc0"].base == 0x09010000
    assert by_name["rtc0"].irq == 34

    for p in board.peripherals:
        assert p.name != "unknown"
        assert p.base != 0
        assert p.irq >= 0


def test_memory_map_is_complete():
    """The regions the eos simulation workflow asserts on."""
    mod = _load_tool()
    board = mod.parse_kicad_pcb(str(SAMPLE))
    names = {r.name for r in board.memory}
    required = {"FLASH_NOR", "RAM_LPDDR4", "UART0_PL011", "HEAP_REGION", "OTA_SCRATCH"}
    assert required <= names, f"missing {required - names}"
    for r in board.memory:
        assert r.size > 0
        assert r.flags in ("rx", "rw", "rwx")


def test_generated_artifacts_carry_the_board_values(tmp_path):
    """The parsed values must reach the output, not just the manifest."""
    subprocess.run(
        [sys.executable, str(TOOL), str(SAMPLE), str(tmp_path)],
        capture_output=True, text=True, check=True,
    )
    manifest = json.loads((tmp_path / "board_manifest.json").read_text())
    assert manifest["cpu"]["core"] == "cortex-a57"

    toolchain = (tmp_path / "eos_toolchain.cmake").read_text(encoding="utf-8")
    assert "cortex-a57" in toolchain

    dts = (tmp_path / "eos_generated.dts").read_text(encoding="utf-8")
    assert "arm,pl011" in dts, "peripheral compatible string missing from the DTS"
