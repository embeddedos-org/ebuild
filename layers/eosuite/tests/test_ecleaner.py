# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for ECleaner — Disk cleanup tool formatting and scanning logic.
"""
import os
import sys
import tkinter as tk
import pytest


class TestECleanerFormatSize:
    """Test the static _fmt_size / _fmt method (no GUI needed)."""

    def _fmt(self, size):
        from gui.apps.ecleaner import ECleaner
        if hasattr(ECleaner, "_fmt_size"):
            return ECleaner._fmt_size(size)
        return ECleaner._fmt(size)

    def test_bytes(self):
        assert "B" in self._fmt(500)

    def test_kilobytes(self):
        result = self._fmt(2048)
        assert "KB" in result

    def test_megabytes(self):
        result = self._fmt(5 * 1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self):
        result = self._fmt(3 * 1024 * 1024 * 1024)
        assert "GB" in result

    def test_terabytes(self):
        result = self._fmt(2 * 1024 * 1024 * 1024 * 1024)
        assert "TB" in result

    def test_zero_bytes(self):
        result = self._fmt(0)
        assert "0.0 B" in result

    def test_one_byte(self):
        result = self._fmt(1)
        assert "B" in result


class TestECleanerCategories:
    """Test category definitions."""

    def test_categories_defined(self):
        from gui.apps.ecleaner import ECleaner
        assert hasattr(ECleaner, "CATEGORIES")
        assert len(ECleaner.CATEGORIES) >= 6

    def test_categories_have_three_fields(self):
        from gui.apps.ecleaner import ECleaner
        for cat in ECleaner.CATEGORIES:
            assert len(cat) == 3, f"Category tuple must have (label, key, description)"


class TestECleanerScanLogic:
    """Test scanning logic with temp directories."""

    def test_scan_dir_empty(self, tmp_path):
        from gui.apps.ecleaner import ECleaner
        cleaner = ECleaner.__new__(ECleaner)
        assert cleaner._scan_dir(str(tmp_path)) == 0

    def test_scan_dir_with_files(self, tmp_path):
        from gui.apps.ecleaner import ECleaner
        cleaner = ECleaner.__new__(ECleaner)
        (tmp_path / "a.txt").write_text("hello")
        (tmp_path / "b.txt").write_text("world!")
        total = cleaner._scan_dir(str(tmp_path))
        assert total > 0

    def test_scan_dir_nonexistent(self, tmp_path):
        from gui.apps.ecleaner import ECleaner
        cleaner = ECleaner.__new__(ECleaner)
        assert cleaner._scan_dir(str(tmp_path / "does_not_exist")) == 0

    def test_scan_logs_returns_int(self, tmp_path):
        from gui.apps.ecleaner import ECleaner
        cleaner = ECleaner.__new__(ECleaner)
        result = cleaner._scan_logs()
        assert isinstance(result, int)

    def test_scan_pycache_returns_int(self):
        from gui.apps.ecleaner import ECleaner
        cleaner = ECleaner.__new__(ECleaner)
        result = cleaner._scan_pycache()
        assert isinstance(result, int)


@pytest.mark.gui
class TestECleanerGUI:
    def _make_cleaner(self, tk_root):
        from gui.apps.ecleaner import ECleaner
        return ECleaner(tk_root, type("App", (), {
            "theme": type("T", (), {"colors": {
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
            }})(),
            "set_status": lambda self, t: None,
        })())

    def test_initial_state(self, tk_root):
        c = self._make_cleaner(tk_root)
        assert c._scan_results == {}

    def test_log_writes(self, tk_root):
        c = self._make_cleaner(tk_root)
        c._log("Test log entry")
        content = c.results_text.get("1.0", tk.END)
        assert "Test log entry" in content

    def test_all_checks_default_true(self, tk_root):
        c = self._make_cleaner(tk_root)
        for key, var in c._checks.items():
            assert var.get() is True, f"Checkbox {key} should default to True"
