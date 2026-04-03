# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for Minesweeper game.
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


class TestMinesweeperConstants:
    def test_difficulties_defined(self):
        from gui.apps.minesweeper import DIFFICULTIES
        assert "Easy" in DIFFICULTIES
        assert "Medium" in DIFFICULTIES
        assert "Hard" in DIFFICULTIES

    def test_easy_dimensions(self):
        from gui.apps.minesweeper import DIFFICULTIES
        w, h, m = DIFFICULTIES["Easy"]
        assert w == 9 and h == 9 and m == 10

    def test_num_colors_defined(self):
        from gui.apps.minesweeper import NUM_COLORS
        for i in range(1, 9):
            assert i in NUM_COLORS


@pytest.mark.gui
class TestMinesweeperGame:
    def _make(self, tk_root):
        from gui.apps.minesweeper import Minesweeper
        return Minesweeper(tk_root, type("App", (), {
            "theme": type("T", (), {"colors": _colors()})(),
            "set_status": lambda self, t: None,
        })())

    def test_initial_state(self, tk_root):
        m = self._make(tk_root)
        assert m._game_over is False
        assert m._first_click is True
        assert m._mines_remaining == 10

    def test_grid_dimensions(self, tk_root):
        m = self._make(tk_root)
        assert len(m._grid) == 9
        assert len(m._grid[0]) == 9

    def test_place_mines_count(self, tk_root):
        m = self._make(tk_root)
        m._place_mines(4, 4)
        mine_count = sum(1 for r in m._grid for c in r if c == -1)
        assert mine_count == 10

    def test_first_click_safe(self, tk_root):
        m = self._make(tk_root)
        m._place_mines(4, 4)
        assert m._grid[4][4] != -1

    def test_reveal_empty_cascades(self, tk_root):
        m = self._make(tk_root)
        m._grid = [[0] * 9 for _ in range(9)]
        m._reveal(4, 4)
        revealed_count = sum(1 for r in m._revealed for c in r if c)
        assert revealed_count > 1

    def test_check_win_false_initially(self, tk_root):
        m = self._make(tk_root)
        m._place_mines(4, 4)
        assert m._check_win() is False

    def test_new_game_resets(self, tk_root):
        m = self._make(tk_root)
        m._game_over = True
        m._new_game()
        assert m._game_over is False
        assert m._first_click is True

    def test_on_close(self, tk_root):
        m = self._make(tk_root)
        m.on_close()
        assert m._game_over is True
