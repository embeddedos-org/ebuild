# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""KiCad quoted strings must come back unescaped.

KiCad writes a '"' or '\\' inside a quoted string as '\\"' or '\\\\'.
SExprParser._parse_string skipped over those escapes while scanning but
returned the raw slice, so a part valued ``10k "thin film"`` was read as
``10k \\"thin film\\"`` -- backslashes included -- and that text flowed into
every component, property and net name the analyzer reported.
"""

from pathlib import Path

from ebuild.eos_ai.kicad_parser import KiCadParser, SExprParser

_SCHEMATIC = r'''(kicad_sch (version 20231120) (generator "eeschema")
  (symbol (lib_id "Device:R") (at 100 50 0)
    (property "Reference" "R1")
    (property "Value" "10k \"thin film\"")
    (property "Footprint" "Resistor_SMD:R_0603")
    (property "Datasheet" "C:\\parts\\r0603.pdf")
  )
)
'''


def test_escaped_quotes_and_backslashes_are_unescaped(tmp_path: Path) -> None:
    sch = tmp_path / "board.kicad_sch"
    sch.write_text(_SCHEMATIC, encoding="utf-8")

    result = KiCadParser().parse(str(sch))

    assert result.errors == []
    (r1,) = result.components
    assert r1.reference == "R1"
    assert r1.value == '10k "thin film"'
    assert r1.properties["Datasheet"] == "C:\\parts\\r0603.pdf"


def test_plain_strings_are_unchanged() -> None:
    tree = SExprParser('(property "Value" "100nF" "")').parse()

    assert tree == ["property", "Value", "100nF", ""]
