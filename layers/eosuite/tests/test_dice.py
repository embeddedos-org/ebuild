# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for Dice Roller.
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


class TestDiceConstants:
    def test_dice_faces_defined(self):
        from gui.apps.dice import DICE_FACES
        assert len(DICE_FACES) == 6
        for i in range(1, 7):
            assert i in DICE_FACES


@pytest.mark.gui
class TestDiceRoller:
    def _make(self, tk_root):
        from gui.apps.dice import DiceRoller
        return DiceRoller(tk_root, type("App", (), {
            "theme": type("T", (), {"colors": _colors()})(),
            "set_status": lambda self, t: None,
        })())

    def test_initial_state(self, tk_root):
        d = self._make(tk_root)
        assert d._total_rolls == 0
        assert d._sum_total == 0
        assert d._history == []

    def test_default_dice_count(self, tk_root):
        d = self._make(tk_root)
        assert d.dice_var.get() == 2

    def test_default_sides(self, tk_root):
        d = self._make(tk_root)
        assert d.sides_var.get() == 6

    def test_roll_updates_state(self, tk_root):
        d = self._make(tk_root)
        d._roll()
        assert d._total_rolls == 1
        assert d._sum_total > 0
        assert len(d._history) == 1

    def test_roll_results_in_range(self, tk_root):
        d = self._make(tk_root)
        d.dice_var.set(3)
        d.sides_var.set(6)
        d._roll()
        _, _, results, total = d._history[0]
        assert len(results) == 3
        assert all(1 <= r <= 6 for r in results)
        assert total == sum(results)

    def test_clear_resets(self, tk_root):
        d = self._make(tk_root)
        d._roll()
        d._roll()
        d._clear()
        assert d._total_rolls == 0
        assert d._sum_total == 0
        assert d._history == []

    def test_multiple_rolls_accumulate(self, tk_root):
        d = self._make(tk_root)
        d._roll()
        d._roll()
        d._roll()
        assert d._total_rolls == 3
        assert len(d._history) == 3
