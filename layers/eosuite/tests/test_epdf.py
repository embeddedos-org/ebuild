# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EPdf — PDF viewer page navigation and state.
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


def _make_pdf(tk_root):
    from gui.apps.epdf import EPdf
    return EPdf(tk_root, type("App", (), {
        "theme": type("T", (), {"colors": _colors(), "is_dark": True})(),
        "set_status": lambda self, t: None,
    })())


@pytest.mark.gui
class TestEPdf:
    def test_initial_state(self, tk_root):
        pdf = _make_pdf(tk_root)
        assert pdf._filepath is None
        assert pdf._pages == []
        assert pdf._current_page == 0

    def test_show_page_displays_content(self, tk_root):
        pdf = _make_pdf(tk_root)
        pdf._pages = ["Page 1 content", "Page 2 content"]
        pdf._current_page = 0
        pdf._show_page()
        content = pdf.text_view.get("1.0", tk.END).strip()
        assert "Page 1 content" in content

    def test_next_page(self, tk_root):
        pdf = _make_pdf(tk_root)
        pdf._pages = ["Page A", "Page B", "Page C"]
        pdf._current_page = 0
        pdf._next_page()
        assert pdf._current_page == 1

    def test_next_page_at_last(self, tk_root):
        pdf = _make_pdf(tk_root)
        pdf._pages = ["Page A", "Page B"]
        pdf._current_page = 1
        pdf._next_page()
        assert pdf._current_page == 1  # stays at last

    def test_prev_page(self, tk_root):
        pdf = _make_pdf(tk_root)
        pdf._pages = ["Page A", "Page B", "Page C"]
        pdf._current_page = 2
        pdf._prev_page()
        assert pdf._current_page == 1

    def test_prev_page_at_first(self, tk_root):
        pdf = _make_pdf(tk_root)
        pdf._pages = ["Page A", "Page B"]
        pdf._current_page = 0
        pdf._prev_page()
        assert pdf._current_page == 0  # stays at first

    def test_page_label_updates(self, tk_root):
        pdf = _make_pdf(tk_root)
        pdf._pages = ["Page A", "Page B"]
        pdf._current_page = 0
        pdf._show_page()
        label_text = pdf.page_label.cget("text")
        assert "1/2" in label_text

    def test_text_view_readonly(self, tk_root):
        pdf = _make_pdf(tk_root)
        assert str(pdf.text_view.cget("state")) == "disabled"

    def test_has_required_methods(self, tk_root):
        pdf = _make_pdf(tk_root)
        assert hasattr(pdf, "_open")
        assert hasattr(pdf, "_extract_text")
        assert hasattr(pdf, "_find")
        assert hasattr(pdf, "_save_text")
        assert hasattr(pdf, "_merge")

    def test_navigate_through_all_pages(self, tk_root):
        pdf = _make_pdf(tk_root)
        pdf._pages = ["P1", "P2", "P3"]
        pdf._current_page = 0
        pdf._next_page()
        pdf._next_page()
        assert pdf._current_page == 2
        content = pdf.text_view.get("1.0", tk.END).strip()
        assert "P3" in content
