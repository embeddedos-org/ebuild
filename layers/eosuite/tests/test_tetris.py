# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for Tetris game.
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


class TestTetrisConstants:
    def test_shapes_defined(self):
        from gui.apps.tetris import SHAPES
        assert len(SHAPES) == 7
        for name in ["I", "O", "T", "S", "Z", "J", "L"]:
            assert name in SHAPES

    def test_colors_defined(self):
        from gui.apps.tetris import COLORS, SHAPES
        for name in SHAPES:
            assert name in COLORS

    def test_grid_dimensions(self):
        from gui.apps.tetris import GRID_WIDTH, GRID_HEIGHT
        assert GRID_WIDTH == 10
        assert GRID_HEIGHT == 20


@pytest.mark.gui
class TestTetrisGame:
    def _make(self, tk_root):
        from gui.apps.tetris import Tetris
        return Tetris(tk_root, type("App", (), {
            "theme": type("T", (), {"colors": _colors()})(),
            "set_status": lambda self, t: None,
        })())

    def test_initial_state(self, tk_root):
        t = self._make(tk_root)
        assert t._score == 0
        assert t._level == 1
        assert t._running is False
        assert t._game_over is False

    def test_grid_initialized_empty(self, tk_root):
        t = self._make(tk_root)
        for row in t._grid:
            assert all(cell is None for cell in row)

    def test_start_game(self, tk_root):
        t = self._make(tk_root)
        t._start_game()
        assert t._running is True
        assert t._current is not None
        t.on_close()

    def test_valid_pos_empty_grid(self, tk_root):
        t = self._make(tk_root)
        from gui.apps.tetris import SHAPES
        shape = SHAPES["O"]
        assert t._valid_pos(shape, 4, 0) is True

    def test_valid_pos_out_of_bounds(self, tk_root):
        t = self._make(tk_root)
        from gui.apps.tetris import SHAPES
        shape = SHAPES["I"]
        assert t._valid_pos(shape, -1, 0) is False

    def test_clear_lines(self, tk_root):
        from gui.apps.tetris import GRID_WIDTH
        t = self._make(tk_root)
        t._grid[-1] = ["I"] * GRID_WIDTH
        cleared = t._clear_lines()
        assert cleared == 1
        assert all(cell is None for cell in t._grid[-1])

    def test_on_close(self, tk_root):
        t = self._make(tk_root)
        t._start_game()
        t.on_close()
        assert t._running is False
