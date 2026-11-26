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

import pytest

from ebuild.eos_ai.kicad_parser import KiCadParser, SExprParser, _unescape

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


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Control escapes. These had no coverage at all: a break in the
        # mapping reached callers unnoticed (review of #205).
        (r"line1\nline2", "line1\nline2"),
        (r"before\rafter", "before\rafter"),
        (r"col1\tcol2", "col1\tcol2"),
        (r"bell\a", "bell\x07"),
        (r"back\b", "back\x08"),
        (r"feed\f", "feed\x0c"),
        (r"vtab\v", "vtab\x0b"),
        # Quote and backslash, the two KiCad actually writes.
        (r"say \"hi\"", 'say "hi"'),
        (r"C:\\parts\\manual.pdf", r"C:\parts\manual.pdf"),
        # Hex and octal, as DSNLEXER decodes them.
        (r"\x41BC", "ABC"),
        (r"\x7E", "~"),
        (r"\101BC", "ABC"),
        (r"\0", "\x00"),
        # A "goofed" hex escape is a literal x, per KiCad's own comment.
        (r"\xZZ", "xZZ"),
        # Unknown escapes keep their backslash (review of #205): a Windows
        # path written without doubled separators must not be flattened to
        # "C:partsmanual.pdf".
        (r"C:\parts\manual.pdf", r"C:\parts\manual.pdf"),
        (r"\q", r"\q"),
        (r"100\%", r"100\%"),
        # A trailing backslash is kept rather than silently dropped.
        ("ends\\", "ends\\"),
        # No backslash at all: returned unchanged.
        ("plain value", "plain value"),
        ("", ""),
    ],
)
def test_unescape_follows_kicad_lexer(raw: str, expected: str) -> None:
    """Semantics are ported from KiCad's DSNLEXER::NextTok()
    (common/dsnlexer.cpp, non-specctra mode), not invented here."""
    assert _unescape(raw) == expected


def test_control_escapes_survive_a_whole_parse(tmp_path: Path) -> None:
    """Through the public parser, not just the helper."""
    schematic = (
        '(kicad_sch (version 20231120) (generator "eeschema")\n'
        '  (symbol (lib_id "Device:R") (at 100 50 0)\n'
        '    (property "Reference" "R1")\n'
        '    (property "Value" "10k")\n'
        '    (property "Notes" "line1\\nline2\\ttabbed")\n'
        '    (property "Datasheet" "C:\\parts\\manual.pdf")\n'
        '    (property "Escaped" "C:\\\\parts\\\\r0603.pdf")\n'
        "  )\n"
        ")\n"
    )
    sch = tmp_path / "board.kicad_sch"
    sch.write_text(schematic, encoding="utf-8")

    result = KiCadParser().parse(str(sch))

    assert result.errors == []
    (r1,) = result.components
    assert r1.properties["Notes"] == "line1\nline2\ttabbed"
    # An unknown escape keeps its backslash, so a Windows path written
    # without doubled separators survives instead of being flattened.
    assert r1.properties["Datasheet"] == "C:\\parts\\manual.pdf"
    # Doubled separators -- what KiCad itself writes -- decode to single
    # ones. Note '\\r' here is the escape KiCad means by it: had the file
    # said 'C:\\parts\\r0603.pdf' with a single backslash, '\\r' would be a
    # carriage return, which is KiCad's behaviour too, not a bug.
    assert r1.properties["Escaped"] == "C:\\parts\\r0603.pdf"
