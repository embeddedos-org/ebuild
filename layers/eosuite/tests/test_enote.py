# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for ENote — Text editor with file ops, find/replace, word count.
"""
import os
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


def _make_note(tk_root):
    from gui.apps.enote import ENote
    return ENote(tk_root, type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "set_status": lambda self, t: None,
    })())


@pytest.mark.gui
class TestENote:
    def test_initial_filepath_none(self, tk_root):
        note = _make_note(tk_root)
        assert note._filepath is None

    def test_initial_file_label(self, tk_root):
        note = _make_note(tk_root)
        assert "Untitled" in note.file_label.cget("text")

    def test_new_clears_text(self, tk_root):
        note = _make_note(tk_root)
        note.text.insert("1.0", "Some content here")
        note._new()
        content = note.text.get("1.0", tk.END).strip()
        assert content == ""
        assert note._filepath is None

    def test_new_resets_label(self, tk_root):
        note = _make_note(tk_root)
        note.file_label.config(text="  test.txt")
        note._new()
        assert "Untitled" in note.file_label.cget("text")

    def test_save_to_file(self, tk_root, tmp_path):
        note = _make_note(tk_root)
        note.text.insert("1.0", "Hello File!")
        filepath = str(tmp_path / "test.txt")
        note._filepath = filepath
        note._save()
        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            assert "Hello File!" in f.read()

    def test_update_status(self, tk_root):
        note = _make_note(tk_root)
        note.text.insert("1.0", "Hello")
        note._update_status()
        status_text = note.status.cget("text")
        assert "Ln" in status_text
        assert "Col" in status_text
        assert "chars" in status_text

    def test_text_widget_has_undo(self, tk_root):
        note = _make_note(tk_root)
        assert note.text.cget("undo") == 1

    def test_has_all_toolbar_buttons(self, tk_root):
        note = _make_note(tk_root)
        assert hasattr(note, "_new")
        assert hasattr(note, "_open")
        assert hasattr(note, "_save")
        assert hasattr(note, "_save_as")
        assert hasattr(note, "_find")
        assert hasattr(note, "_replace")
        assert hasattr(note, "_word_count")
