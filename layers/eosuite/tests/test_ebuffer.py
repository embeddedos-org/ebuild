# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EBuffer — Clipboard manager with slots.
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


def _make_app():
    return type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "set_status": lambda self, t: None,
    })()


def _make_buffer(tk_root):
    from gui.apps.ebuffer import EBuffer
    buf = EBuffer(tk_root, _make_app())
    # Cancel polling to avoid background callbacks during tests
    for after_id in tk_root.tk.call("after", "info"):
        try:
            tk_root.after_cancel(after_id)
        except Exception:
            pass
    return buf


@pytest.mark.gui
class TestEBuffer:
    def test_max_slots_defined(self, tk_root):
        from gui.apps.ebuffer import EBuffer
        assert EBuffer.MAX_SLOTS == 20

    def test_initial_state(self, tk_root):
        buf = _make_buffer(tk_root)
        assert buf._slots == []

    def test_delete_slot_valid(self, tk_root):
        buf = _make_buffer(tk_root)
        buf._slots = ["aaa", "bbb", "ccc"]
        buf._delete_slot(1)
        assert buf._slots == ["aaa", "ccc"]

    def test_delete_slot_invalid_index(self, tk_root):
        buf = _make_buffer(tk_root)
        buf._slots = ["aaa"]
        buf._delete_slot(5)
        assert buf._slots == ["aaa"]

    def test_delete_slot_negative_index(self, tk_root):
        buf = _make_buffer(tk_root)
        buf._slots = ["aaa"]
        buf._delete_slot(-1)
        assert buf._slots == ["aaa"]

    def test_preview_slot(self, tk_root):
        buf = _make_buffer(tk_root)
        buf._preview_slot("Hello World")
        buf.preview_text.config(state=tk.NORMAL)
        content = buf.preview_text.get("1.0", tk.END).strip()
        assert "Hello World" in content

    def test_copy_slot(self, tk_root):
        buf = _make_buffer(tk_root)
        buf._copy_slot("test clipboard content")
        result = buf.clipboard_get()
        assert result == "test clipboard content"

    def test_capture_adds_to_front(self, tk_root):
        buf = _make_buffer(tk_root)
        buf.clipboard_clear()
        buf.clipboard_append("first item")
        buf._capture()
        assert len(buf._slots) >= 1
        assert buf._slots[0] == "first item"

    def test_capture_deduplicates(self, tk_root):
        buf = _make_buffer(tk_root)
        buf._slots = ["already here"]
        buf.clipboard_clear()
        buf.clipboard_append("already here")
        buf._capture()
        assert len(buf._slots) == 1

    def test_capture_respects_max_slots(self, tk_root):
        buf = _make_buffer(tk_root)
        buf._slots = [f"item{i}" for i in range(20)]
        buf.clipboard_clear()
        buf.clipboard_append("new item")
        buf._capture()
        assert len(buf._slots) <= buf.MAX_SLOTS

    def test_refresh_slots_empty(self, tk_root):
        buf = _make_buffer(tk_root)
        buf._slots = []
        buf._refresh_slots()
        children = buf.inner_frame.winfo_children()
        assert len(children) >= 1  # "No clipboard items" label
