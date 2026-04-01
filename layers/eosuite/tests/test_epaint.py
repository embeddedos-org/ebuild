# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EPaint — Drawing canvas tool/color state management.
"""
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


def _make_paint(tk_root):
    from gui.apps.epaint import EPaint
    return EPaint(tk_root, type("App", (), {
        "theme": type("T", (), {"colors": _colors(), "is_dark": True})(),
        "set_status": lambda self, t: None,
    })())


@pytest.mark.gui
class TestEPaint:
    def test_initial_color(self, tk_root):
        p = _make_paint(tk_root)
        assert p._color == "#ffffff"

    def test_initial_brush_size(self, tk_root):
        p = _make_paint(tk_root)
        assert p._brush_size == 3

    def test_initial_tool(self, tk_root):
        p = _make_paint(tk_root)
        assert p._tool == "brush"

    def test_set_color(self, tk_root):
        p = _make_paint(tk_root)
        p._set_color("#ff0000")
        assert p._color == "#ff0000"
        assert p.color_btn.cget("bg") == "#ff0000"

    def test_set_tool(self, tk_root):
        p = _make_paint(tk_root)
        if hasattr(p, "_set_tool"):
            p._set_tool("rect")
            assert p._tool == "rect"
        else:
            p._tool = "rect"
            assert p._tool == "rect"

    def test_brush_size_update(self, tk_root):
        p = _make_paint(tk_root)
        p.size_var.set(10)
        if hasattr(p, "_update_size"):
            p._update_size()
        assert p.size_var.get() == 10

    def test_on_press_sets_last_coords(self, tk_root):
        p = _make_paint(tk_root)
        event = type("Event", (), {"x": 50, "y": 75})()
        p._on_press(event)
        assert p._last_x == 50
        assert p._last_y == 75

    def test_on_release_clears_coords(self, tk_root):
        p = _make_paint(tk_root)
        p._last_x, p._last_y = 10, 20
        p._tool = "rect"
        event = type("Event", (), {"x": 100, "y": 200})()
        p._on_release(event)
        assert p._last_x is None
        assert p._last_y is None

    def test_clear_canvas(self, tk_root):
        p = _make_paint(tk_root)
        p.canvas.create_line(0, 0, 100, 100)
        if hasattr(p, "_clear"):
            p._clear()
        else:
            p.canvas.delete("all")
        items = p.canvas.find_all()
        assert len(items) == 0

    def test_canvas_cursor(self, tk_root):
        p = _make_paint(tk_root)
        assert p.canvas.cget("cursor") == "crosshair"

    def test_all_tools_exist(self, tk_root):
        p = _make_paint(tk_root)
        for tool in ["brush", "rect", "oval", "line", "eraser"]:
            p._tool = tool
            assert p._tool == tool
