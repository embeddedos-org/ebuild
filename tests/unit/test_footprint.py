# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Flash and RAM footprint reporting.

The MLP developer walk ends with a build that says how much of the board it
used. Nothing produced those numbers, so a developer had to run `size` by hand
and know which columns to add.

The accounting has to match `scripts/measure_footprint.py` in the eos repo, or
the two tools disagree about what "flash" means:

    flash = text + data
    ram   = data + bss
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from ebuild.build.footprint import (
    Footprint,
    FootprintError,
    _measure_macho,
    _run_size,
    board_capacity,
    find_size_tool,
    format_report,
    format_size,
    measure,
    over_budget,
)


class TestAccounting:
    """`data` is charged to both regions: it is stored in flash and copied to
    RAM at startup. Reading `size`'s "dec" column instead understates RAM."""

    def test_flash_is_text_plus_data(self):
        assert Footprint(text=1000, data=200, bss=500).flash == 1200

    def test_ram_is_data_plus_bss(self):
        assert Footprint(text=1000, data=200, bss=500).ram == 700

    def test_data_is_counted_in_both(self):
        fp = Footprint(text=0, data=64, bss=0)
        assert fp.flash == 64
        assert fp.ram == 64

    def test_a_pure_bss_buffer_costs_ram_but_not_flash(self):
        """A zero-initialised array is not stored in the image."""
        fp = Footprint(text=100, data=0, bss=8192)
        assert fp.flash == 100
        assert fp.ram == 8192


class TestMeasure:
    def test_measures_a_real_binary(self, tmp_path):
        if shutil.which("gcc") is None:
            pytest.skip("needs a working gcc to compile the test binary")

        src = tmp_path / "m.c"
        src.write_text("static char buf[4096];\nint main(void){return buf[0];}\n")
        # gcc on Windows appends .exe when -o names no extension, so the
        # path measured here has to carry it or there is nothing to measure.
        exe = tmp_path / ("m.exe" if os.name == "nt" else "m")
        subprocess.run(["gcc", str(src), "-o", str(exe)], check=True)

        fp = measure(exe)
        assert fp.text > 0
        # The 4 KB buffer is zero-initialised, so it lands in bss and shows up
        # in RAM without inflating flash.
        assert fp.bss >= 4096
        assert fp.ram >= 4096

    def test_a_missing_artifact_raises_rather_than_reporting_zero(self, tmp_path):
        """Reporting "Flash: 0 KB" when nothing was measured is worse than
        saying nothing."""
        with pytest.raises(FootprintError, match="no artifact"):
            measure(tmp_path / "nope")

    def test_a_missing_size_tool_raises(self, tmp_path, monkeypatch):
        exe = tmp_path / "x"
        exe.write_bytes(b"\x7fELF")
        monkeypatch.setattr("ebuild.build.footprint.shutil.which", lambda _n: None)
        with pytest.raises(FootprintError, match="no 'size' tool"):
            measure(exe)

    def test_a_file_that_is_not_an_object_raises(self, tmp_path):
        junk = tmp_path / "notelf.txt"
        junk.write_text("this is not an object file")
        with pytest.raises(FootprintError):
            measure(junk)


class TestSizeToolSelection:
    def test_host_build_uses_the_host_tool(self):
        assert find_size_tool("host") == find_size_tool(None)

    def test_cross_build_wants_the_toolchain_tool(self, monkeypatch):
        seen = {}

        def fake_which(name):
            seen["name"] = name
            return "/opt/arm/bin/arm-none-eabi-size"

        monkeypatch.setattr("ebuild.build.footprint.shutil.which", fake_which)
        assert find_size_tool("arm-none-eabi").endswith("arm-none-eabi-size")
        assert seen["name"] == "arm-none-eabi-size"

    def test_cross_build_does_not_fall_back_to_the_host_tool(self, monkeypatch):
        """Host `size` on an ARM ELF would report numbers for a different
        target, and nothing in the output would say so."""
        monkeypatch.setattr(
            "ebuild.build.footprint.shutil.which",
            lambda name: None if name.startswith("arm-") else "/usr/bin/size",
        )
        assert find_size_tool("arm-none-eabi") is None


class TestBoardCapacity:
    def test_a_known_family_has_a_reference_part(self):
        flash, ram = board_capacity("stm32f4")
        assert flash == 1024 * 1024
        assert ram == 192 * 1024

    def test_lookup_is_case_insensitive(self):
        assert board_capacity("STM32F4") == board_capacity("stm32f4")

    def test_a_linux_class_board_has_no_fixed_budget(self):
        """A made-up ceiling is worse than none: a percentage reads as
        authoritative."""
        assert board_capacity("rpi4") == (None, None)

    def test_an_unknown_board_is_unknown(self):
        assert board_capacity("some-new-board") == (None, None)

    def test_project_board_yaml_overrides_the_reference_table(self):
        """An STM32F401 has 256 KB of flash where the F407 has 1 MB; a project
        that says so should be measured against its own part."""
        cfg = {"memory": {"flash_size": "0x40000", "ram_size": 65536}}
        assert board_capacity("stm32f4", cfg) == (262144, 65536)

    def test_hex_and_int_sizes_both_parse(self):
        assert board_capacity(None, {"memory": {"flash_size": "0x100"}})[0] == 256
        assert board_capacity(None, {"memory": {"flash_size": 256}})[0] == 256

    def test_a_zero_or_unparseable_size_is_not_a_capacity(self):
        """`flash: 0 (boots from SD card)` appears in the shipped board
        descriptions; zero is not a ceiling."""
        assert board_capacity(None, {"memory": {"flash_size": 0}}) == (None, None)
        assert board_capacity(None, {"memory": {"flash_size": "lots"}}) == (None, None)

    def test_a_board_config_without_memory_falls_back(self):
        assert board_capacity("stm32f4", {"board_name": "x"})[0] == 1024 * 1024


class TestReport:
    def test_percentages_appear_only_with_a_known_capacity(self):
        fp = Footprint(text=1000, data=100, bss=200)
        assert "%" in format_report(fp, 4096, 4096)
        assert "%" not in format_report(fp)

    def test_report_names_both_regions(self):
        body = format_report(Footprint(text=1, data=1, bss=1))
        assert "Flash" in body and "RAM" in body

    def test_a_known_flash_and_unknown_ram_shows_one_percentage(self):
        body = format_report(Footprint(text=1000, data=0, bss=99), 4096, None)
        flash_line, ram_line = body.splitlines()
        assert "%" in flash_line
        assert "%" not in ram_line


class TestBudget:
    def test_within_budget_is_silent(self):
        assert over_budget(Footprint(1000, 100, 200), 1 << 20, 1 << 20) is None

    def test_flash_overflow_is_named(self):
        msg = over_budget(Footprint(2 << 20, 0, 0), 1 << 20, 1 << 20)
        assert msg and "flash" in msg

    def test_ram_overflow_is_named(self):
        msg = over_budget(Footprint(0, 0, 2 << 20), 1 << 20, 1 << 20)
        assert msg and "RAM" in msg

    def test_no_capacity_means_no_verdict(self):
        """Without a real ceiling there is nothing to be over."""
        assert over_budget(Footprint(1 << 30, 0, 1 << 30)) is None

    def test_exactly_full_is_not_over(self):
        assert over_budget(Footprint(1024, 0, 0), 1024, 4096) is None


class TestFormatSize:
    @pytest.mark.parametrize("n,expected", [
        (0, "0 B"),
        (512, "512 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1024 * 1024, "1.00 MB"),
    ])
    def test_units(self, n, expected):
        assert format_size(n) == expected


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["size"], returncode=returncode, stdout=stdout, stderr=stderr)


class TestSizeToolFailures:
    """`_run_size` is the single place every `size` invocation goes through, so
    a failure mode it does not convert into FootprintError escapes as a bare
    OSError and takes down a build that otherwise succeeded."""

    def test_a_tool_that_cannot_be_executed_becomes_a_footprint_error(
            self, tmp_path, monkeypatch):
        def boom(*_a, **_kw):
            raise OSError("Exec format error")

        monkeypatch.setattr(subprocess, "run", boom)
        with pytest.raises(FootprintError, match="Exec format error"):
            _run_size("size", [], tmp_path / "app")

    def test_a_tool_that_hangs_becomes_a_footprint_error(
            self, tmp_path, monkeypatch):
        """The 60 s timeout exists so a wedged `size` cannot hang the build;
        the expiry has to arrive as a FootprintError like every other
        failure, or the timeout just changes which exception escapes."""
        def hang(*_a, **_kw):
            raise subprocess.TimeoutExpired(cmd="size", timeout=60)

        monkeypatch.setattr(subprocess, "run", hang)
        with pytest.raises(FootprintError, match="failed on"):
            _run_size("size", [], tmp_path / "app")

    def test_a_nonzero_exit_reports_the_tool_s_own_message(
            self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            subprocess, "run",
            lambda *_a, **_kw: _completed(1, stderr="not an object file"))
        with pytest.raises(FootprintError, match="not an object file"):
            _run_size("size", [], tmp_path / "app")


#: Real `size -m` output, from a host binary with 4 bytes of initialised data
#: and a 4 KB zero-initialised buffer. Reproduced verbatim rather than
#: measured, because the parsing has to be exercised on the Linux and Windows
#: legs too -- where no Mach-O binary can be produced and every line of this
#: parser would otherwise go unrun.
_MACHO_SIZE_M = """\
Segment __PAGEZERO: 4294967296 (zero fill)
Segment __TEXT: 16384
\tSection __text: 36
\tSection __unwind_info: 88
\ttotal 124
Segment __DATA: 16384
\tSection __data: 4
\tSection __bss: 4096 (zerofill)
\ttotal 4100
Segment __LINKEDIT: 16384
total 4295016448
"""


class TestMachOSections:
    """Apple's size(1) reports segments, which are page-aligned: __TEXT reads
    as 16 KB for the 124 bytes below. Only the section numbers mean what the
    Berkeley columns mean, and the two tools must not disagree."""

    def _measured(self, monkeypatch, stdout):
        monkeypatch.setattr(subprocess, "run",
                            lambda *_a, **_kw: _completed(stdout=stdout))
        return _measure_macho("size", Path("app"))

    def test_sections_land_in_the_region_that_holds_them(self, monkeypatch):
        fp = self._measured(monkeypatch, _MACHO_SIZE_M)
        assert fp.text == 36 + 88
        assert fp.data == 4       # __data: stored in the image and copied to RAM
        assert fp.bss == 4096     # zerofill: RAM only

    def test_the_page_aligned_segment_totals_are_not_the_answer(self, monkeypatch):
        """Reading "Segment __TEXT: 16384" would report 16 KB of flash for
        124 bytes of code, and disagree with `size` on the same binary."""
        fp = self._measured(monkeypatch, _MACHO_SIZE_M)
        assert fp.flash == 128
        assert 16384 not in (fp.text, fp.data, fp.bss)

    def test_linkedit_and_pagezero_are_not_charged_to_the_image(self, monkeypatch):
        """__LINKEDIT holds symbol tables stripped at load and __PAGEZERO is
        an unmapped guard region. Neither costs the device anything, and
        __PAGEZERO alone would add 4 GB of "data"."""
        fp = self._measured(monkeypatch, _MACHO_SIZE_M + (
            "Segment __LINKEDIT: 16384\n"
            "\tSection __symtab: 900\n"
        ))
        assert fp.data == 4

    def test_a_non_text_segment_is_charged_to_data(self, monkeypatch):
        """__DATA_CONST is neither __TEXT nor zerofill: it is stored in the
        image, so it is flash, and dropping it would understate the binary."""
        fp = self._measured(monkeypatch, (
            "Segment __DATA_CONST: 16384\n"
            "\tSection __const: 256\n"
        ))
        assert fp.data == 256
        assert fp.text == 0

    def test_output_with_no_sections_raises_rather_than_reporting_zero(
            self, monkeypatch):
        """A parser that stopped matching would otherwise report a firmware
        image of 0 bytes, which reads as a successful measurement."""
        with pytest.raises(FootprintError, match="could not read any section"):
            self._measured(monkeypatch, "Segment __TEXT: 16384\ntotal 16384\n")


class TestOutputFormatDispatch:
    """Which parser runs is decided by the output, not by the host platform,
    so both branches are reachable from either."""

    def _measure_with(self, tmp_path, monkeypatch, stdout):
        artifact = tmp_path / "app"
        artifact.write_bytes(b"\x7fELF")
        monkeypatch.setattr(subprocess, "run",
                            lambda *_a, **_kw: _completed(stdout=stdout))
        return measure(artifact, size_tool="size")

    def test_berkeley_columns_are_read_as_text_data_bss(self, tmp_path, monkeypatch):
        fp = self._measure_with(tmp_path, monkeypatch, (
            "   text\t   data\t    bss\t    dec\t    hex\tfilename\n"
            "   1720\t    600\t   4096\t   6416\t   1910\tapp\n"
        ))
        assert (fp.text, fp.data, fp.bss) == (1720, 600, 4096)

    def test_the_apple_column_header_routes_to_the_section_parser(
            self, tmp_path, monkeypatch):
        """Apple's header row matches _SIZE_LINE too, and its __OBJC column --
        always 0 -- was being read as bss. Every footprint measured on macOS
        reported RAM with no zero-initialised data in it."""
        columns = ("__TEXT\t__DATA\t__OBJC\tothers\tdec\thex\n"
                   "16384\t16384\t0\t4294983680\t4295016448\t10000c000\n")

        def size(argv, **_kw):
            # The second call is the `-m` re-run the header should trigger.
            return _completed(stdout=_MACHO_SIZE_M if "-m" in argv else columns)

        artifact = tmp_path / "app"
        artifact.write_bytes(b"\x7fELF")
        monkeypatch.setattr(subprocess, "run", size)

        fp = measure(artifact, size_tool="size")
        assert fp.bss == 4096, "the __OBJC column was read as bss"
        assert fp.flash == 128

    def test_unparseable_output_raises_rather_than_reporting_zero(
            self, tmp_path, monkeypatch):
        with pytest.raises(FootprintError, match="could not read a size line"):
            self._measure_with(tmp_path, monkeypatch, "size: bad file\n")
