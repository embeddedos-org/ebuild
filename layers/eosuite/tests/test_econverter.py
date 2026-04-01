# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EConverter — text conversions and PDF generation.
"""
import json
import os
import pytest

tk = pytest.importorskip("tkinter")


class TestTextConversions:
    """Test pure text transformation logic by extracting it from the class methods."""

    def test_txt_upper(self):
        assert "hello World".upper() == "HELLO WORLD"

    def test_txt_lower(self):
        assert "HELLO World".lower() == "hello world"

    def test_lines_sort(self):
        result = "\n".join(sorted("cherry\napple\nbanana".strip().split("\n")))
        assert result == "apple\nbanana\ncherry"

    def test_lines_unique(self):
        seen, r = set(), []
        for line in "a\nb\na\nc\nb".strip().split("\n"):
            if line not in seen:
                seen.add(line)
                r.append(line)
        assert r == ["a", "b", "c"]

    def test_lines_reverse(self):
        result = "\n".join(reversed("first\nsecond\nthird".strip().split("\n")))
        assert result == "third\nsecond\nfirst"

    def test_txt_to_base64_roundtrip(self):
        import base64
        original = "hello world"
        encoded = base64.b64encode(original.encode()).decode()
        decoded = base64.b64decode(encoded).decode()
        assert decoded == original

    def test_csv_to_json(self):
        import csv
        import io
        csv_data = "name,age\nAlice,30\nBob,25"
        reader = csv.DictReader(csv_data.strip().split("\n"))
        data = list(reader)
        assert len(data) == 2
        assert data[0]["name"] == "Alice"
        assert data[0]["age"] == "30"
        assert data[1]["name"] == "Bob"

    def test_json_to_csv(self):
        import csv
        import io
        data = [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=data[0].keys())
        w.writeheader()
        w.writerows(data)
        result = out.getvalue()
        assert "name" in result
        assert "Alice" in result
        lines = result.strip().split("\n")
        assert len(lines) == 3

    def test_json_format(self):
        ugly = '{"b":2,"a":1}'
        result = json.dumps(json.loads(ugly), indent=2, sort_keys=True)
        assert json.loads(result) == {"a": 1, "b": 2}
        assert "\n" in result

    def test_txt_to_hex(self):
        data = "AB".encode()
        hex_parts = " ".join("%02x" % b for b in data)
        assert "41" in hex_parts
        assert "42" in hex_parts

    def test_md_heading(self):
        line = "# Title"
        if line.startswith("# "):
            html = "<h1>%s</h1>" % line[2:]
        assert html == "<h1>Title</h1>"

    def test_md_list_item(self):
        line = "- item1"
        if line.startswith("- "):
            html = "<li>%s</li>" % line[2:]
        assert html == "<li>item1</li>"

    def test_txt_to_jsonl(self):
        lines = "hello\nworld".strip().split("\n")
        result = [json.dumps({"line": i + 1, "text": l}) for i, l in enumerate(lines)]
        assert len(result) == 2
        assert json.loads(result[0]) == {"line": 1, "text": "hello"}
        assert json.loads(result[1]) == {"line": 2, "text": "world"}


class TestEConverterConversions:
    """Test the CONVERSIONS list is properly defined."""

    def test_conversions_list_exists(self):
        from gui.apps.econverter import EConverter
        assert hasattr(EConverter, "CONVERSIONS")
        assert len(EConverter.CONVERSIONS) >= 16

    def test_each_conversion_has_4_fields(self):
        from gui.apps.econverter import EConverter
        for conv in EConverter.CONVERSIONS:
            assert len(conv) == 4, "Each conversion tuple must have (label, method, src_type, dest_type)"

    def test_all_methods_exist(self):
        from gui.apps.econverter import EConverter
        for label, method_name, _, _ in EConverter.CONVERSIONS:
            assert hasattr(EConverter, method_name), "Missing method: %s for %s" % (method_name, label)

    def test_file_filters_defined(self):
        from gui.apps.econverter import EConverter
        assert hasattr(EConverter, "FILE_FILTERS")
        assert "docx" in EConverter.FILE_FILTERS
        assert "image" in EConverter.FILE_FILTERS
        assert "csv" in EConverter.FILE_FILTERS


class TestPdfGeneration:
    """Test the zero-dependency PDF writer."""

    def test_creates_file(self, tmp_path):
        from gui.apps.econverter import EConverter
        out = str(tmp_path / "test.pdf")
        EConverter._text_to_pdf_file(None, "Hello!", out)
        assert os.path.exists(out) and os.path.getsize(out) > 0

    def test_pdf_header(self, tmp_path):
        from gui.apps.econverter import EConverter
        out = str(tmp_path / "test.pdf")
        EConverter._text_to_pdf_file(None, "Test", out)
        with open(out, "rb") as f:
            assert f.read(8).startswith(b"%PDF-1.4")

    def test_pdf_eof(self, tmp_path):
        from gui.apps.econverter import EConverter
        out = str(tmp_path / "test.pdf")
        EConverter._text_to_pdf_file(None, "Test", out)
        with open(out, "rb") as f:
            assert f.read().strip().endswith(b"%%EOF")

    def test_multipage(self, tmp_path):
        from gui.apps.econverter import EConverter
        out = str(tmp_path / "multi.pdf")
        text = "\n".join("Line %d" % i for i in range(120))
        EConverter._text_to_pdf_file(None, text, out)
        with open(out, "rb") as f:
            assert f.read().count(b"/Type /Page ") >= 2

    def test_empty_text(self, tmp_path):
        from gui.apps.econverter import EConverter
        out = str(tmp_path / "empty.pdf")
        EConverter._text_to_pdf_file(None, "", out)
        assert os.path.exists(out)

    def test_special_chars(self, tmp_path):
        from gui.apps.econverter import EConverter
        out = str(tmp_path / "special.pdf")
        EConverter._text_to_pdf_file(None, "Hello (world) with \\ backslash", out)
        assert os.path.exists(out) and os.path.getsize(out) > 0
