# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EGuard — Keep-awake utility toggle and state.
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


def _make_guard(tk_root):
    from gui.apps.eguard import EGuard
    return EGuard(tk_root, type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "set_status": lambda self, t: None,
    })())


@pytest.mark.gui
class TestEGuard:
    def test_initial_state_inactive(self, tk_root):
        g = _make_guard(tk_root)
        assert g._active is False

    def test_toggle_activates(self, tk_root):
        g = _make_guard(tk_root)
        g._toggle()
        assert g._active is True

    def test_toggle_deactivates(self, tk_root):
        g = _make_guard(tk_root)
        g._toggle()  # activate
        g._toggle()  # deactivate
        assert g._active is False

    def test_status_label_inactive(self, tk_root):
        g = _make_guard(tk_root)
        assert "Inactive" in g.status_label.cget("text")

    def test_status_label_active(self, tk_root):
        g = _make_guard(tk_root)
        g._toggle()
        assert "Active" in g.status_label.cget("text")

    def test_on_close_deactivates(self, tk_root):
        g = _make_guard(tk_root)
        g._active = True
        g.on_close()
        assert g._active is False

    def test_toggle_button_text_changes(self, tk_root):
        g = _make_guard(tk_root)
        assert "Activate" in g.toggle_btn.cget("text")
        g._toggle()
        assert "Deactivate" in g.toggle_btn.cget("text")

    def test_double_toggle_restores_button(self, tk_root):
        g = _make_guard(tk_root)
        g._toggle()
        g._toggle()
        assert "Activate" in g.toggle_btn.cget("text")
