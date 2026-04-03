# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EViewer — Hex viewer rendering and navigation.
"""
import tkinter as tk
import pytest


def _colors():
    return {
        "bg": "#1e1e1e", "fg": "#d4d4d4", "accent": "#0078d4",
        "sidebar_bg": "#252526", "toolbar_bg": "#2d2d2d",
        "tab_bg": "#2d2d2d", "tab_active": "#1e1e1e",
        "input_bg": "#3c3c3c", "input_fg": "#d4d4d4",
        "border": "#3c3c3c", "hover": "#094771",
        "button_bg": "#0e639c", "button_fg": "#ffffff",
        "status_bg": "#007acc", "status_fg": "#ffffff",
        "tree_bg": "#252526", "tree_fg": "#cccccc",
        "tree_select": "#094771", "menu_bg": "#2d2d2d",
        "menu_fg": "#cccccc", "terminal_bg": "#0c0c0c",
        "terminal_fg": "#cccccc",
    }


def _make_viewer(tk_root):
    from gui.apps.eviewer import EViewer
    return EViewer(tk_root, type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "set_status": lambda self, t: None,
    })())


class TestEViewerConstants:
    def test_bytes_per_row(self):
        from gui.apps.eviewer import EViewer
        assert EViewer.BYTES_PER_ROW == 16


@pytest.mark.gui
class TestEViewer:
    def test_initial_data_empty(self, tk_root):
        v = _make_viewer(tk_root)
        assert v._data == b""

    def test_render_with_data(self, tk_root):
        v = _make_viewer(tk_root)
        v._data = b"Hello World!"
        v._render()
        content = v.hex_view.get("1.0", tk.END)
        assert "48" in content  # 'H' = 0x48
        assert "65" in content  # 'e' = 0x65

    def test_render_shows_ascii(self, tk_root):
        v = _make_viewer(tk_root)
        v._data = b"ABCD"
        v._render()
        content = v.hex_view.get("1.0", tk.END)
        assert "ABCD" in content

    def test_render_non_printable_as_dot(self, tk_root):
        v = _make_viewer(tk_root)
        v._data = b"\x00\x01\x02"
        v._render()
        content = v.hex_view.get("1.0", tk.END)
        assert "..." in content

    def test_render_shows_offset(self, tk_root):
        v = _make_viewer(tk_root)
        v._data = b"A" * 32
        v._render()
        content = v.hex_view.get("1.0", tk.END)
        assert "00000000" in content
        assert "00000010" in content

    def test_goto_offset(self, tk_root):
        v = _make_viewer(tk_root)
        v._data = b"A" * 256
        v._render()
        v.goto_var.set("20")
        v._goto_offset()  # should not raise

    def test_goto_invalid_offset(self, tk_root):
        v = _make_viewer(tk_root)
        v.goto_var.set("not_hex")
        v._goto_offset()  # should not raise (ValueError caught)

    def test_info_label_initial(self, tk_root):
        v = _make_viewer(tk_root)
        assert "No file" in v.info_label.cget("text")

    def test_hex_view_readonly(self, tk_root):
        v = _make_viewer(tk_root)
        assert str(v.hex_view.cget("state")) == "disabled"

    def test_render_empty_data(self, tk_root):
        v = _make_viewer(tk_root)
        v._data = b""
        v._render()
        content = v.hex_view.get("1.0", tk.END).strip()
        assert content == ""

    def test_render_single_byte(self, tk_root):
        v = _make_viewer(tk_root)
        v._data = b"\x42"
        v._render()
        content = v.hex_view.get("1.0", tk.END)
        assert "42" in content
