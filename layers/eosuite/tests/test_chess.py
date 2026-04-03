# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for Chess game.
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


class TestChessConstants:
    def test_pieces_defined(self):
        from gui.apps.chess import PIECES
        assert len(PIECES) == 12
        for p in ["K", "Q", "R", "B", "N", "P", "k", "q", "r", "b", "n", "p"]:
            assert p in PIECES

    def test_initial_board_dimensions(self):
        from gui.apps.chess import INITIAL_BOARD
        assert len(INITIAL_BOARD) == 8
        for row in INITIAL_BOARD:
            assert len(row) == 8

    def test_initial_board_pieces(self):
        from gui.apps.chess import INITIAL_BOARD
        assert INITIAL_BOARD[0][4] == "k"
        assert INITIAL_BOARD[7][4] == "K"
        assert INITIAL_BOARD[1] == ["p"] * 8
        assert INITIAL_BOARD[6] == ["P"] * 8


@pytest.mark.gui
class TestChessGame:
    def _make(self, tk_root):
        from gui.apps.chess import Chess
        return Chess(tk_root, type("App", (), {
            "theme": type("T", (), {"colors": _colors()})(),
            "set_status": lambda self, t: None,
        })())

    def test_initial_turn(self, tk_root):
        c = self._make(tk_root)
        assert c._turn == "white"

    def test_initial_no_selection(self, tk_root):
        c = self._make(tk_root)
        assert c._selected is None
        assert c._valid_moves == []

    def test_board_setup(self, tk_root):
        c = self._make(tk_root)
        assert c._board[7][4] == "K"
        assert c._board[0][4] == "k"

    def test_pawn_moves(self, tk_root):
        c = self._make(tk_root)
        moves = c._get_moves(6, 4)
        assert (5, 4) in moves
        assert (4, 4) in moves

    def test_knight_moves(self, tk_root):
        c = self._make(tk_root)
        moves = c._get_moves(7, 1)
        assert (5, 0) in moves
        assert (5, 2) in moves

    def test_own_piece_detection(self, tk_root):
        c = self._make(tk_root)
        assert c._own_piece("P") is True
        assert c._own_piece("p") is False

    def test_enemy_piece_detection(self, tk_root):
        c = self._make(tk_root)
        assert c._enemy_piece("p") is True
        assert c._enemy_piece("P") is False
        assert c._enemy_piece("") is False

    def test_make_move_switches_turn(self, tk_root):
        c = self._make(tk_root)
        c._make_move(6, 4, 4, 4)
        assert c._turn == "black"

    def test_make_move_captures(self, tk_root):
        c = self._make(tk_root)
        c._board[5][3] = "p"
        c._make_move(6, 4, 5, 3)
        assert c._board[5][3] == "P"
        assert len(c._captured_white) == 1

    def test_new_game_resets(self, tk_root):
        c = self._make(tk_root)
        c._make_move(6, 4, 4, 4)
        c._new_game()
        assert c._turn == "white"
        assert c._move_history == []
        assert c._board[6][4] == "P"

    def test_slide_rook(self, tk_root):
        c = self._make(tk_root)
        c._board = [[""] * 8 for _ in range(8)]
        c._board[4][4] = "R"
        moves = c._get_moves(4, 4)
        assert len(moves) > 10
