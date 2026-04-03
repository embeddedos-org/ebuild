# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for SnakeGame logic.
"""
import pytest

tk = pytest.importorskip("tkinter")

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


@pytest.mark.gui
class TestSnakeGame:
    def test_initial_snake_length(self, tk_root):
        from gui.apps.snake import SnakeGame
        g = SnakeGame(tk_root, _make_app())
        assert len(g._snake) == 3

    def test_initial_direction(self, tk_root):
        from gui.apps.snake import SnakeGame
        g = SnakeGame(tk_root, _make_app())
        assert g._direction == "Right"

    def test_initial_score(self, tk_root):
        from gui.apps.snake import SnakeGame
        g = SnakeGame(tk_root, _make_app())
        assert g._score == 0 and g._high_score == 0

    def test_not_running(self, tk_root):
        from gui.apps.snake import SnakeGame
        g = SnakeGame(tk_root, _make_app())
        assert not g._running and not g._game_over

    def test_food_not_on_snake(self, tk_root):
        from gui.apps.snake import SnakeGame
        g = SnakeGame(tk_root, _make_app())
        g._place_food()
        assert g._food not in g._snake

    def test_reset(self, tk_root):
        from gui.apps.snake import SnakeGame
        g = SnakeGame(tk_root, _make_app())
        g._score = 50; g._direction = "Left"; g._running = True
        g._reset_game()
        assert g._score == 0 and g._direction == "Right" and not g._running

    def test_no_reverse(self, tk_root):
        from gui.apps.snake import SnakeGame
        g = SnakeGame(tk_root, _make_app())
        g._direction = "Right"
        g._on_key(type("E", (), {"keysym": "Left"})())
        assert g._next_direction == "Right"

    def test_perpendicular(self, tk_root):
        from gui.apps.snake import SnakeGame
        g = SnakeGame(tk_root, _make_app())
        g._direction = "Right"
        g._on_key(type("E", (), {"keysym": "Up"})())
        assert g._next_direction == "Up"

    def test_wasd(self, tk_root):
        from gui.apps.snake import SnakeGame
        g = SnakeGame(tk_root, _make_app())
        g._direction = "Right"
        g._on_key(type("E", (), {"keysym": "w"})())
        assert g._next_direction == "Up"

    def test_grid_size(self, tk_root):
        from gui.apps.snake import SnakeGame
        g = SnakeGame(tk_root, _make_app())
        assert g.GRID_WIDTH == 30 and g.GRID_HEIGHT == 20
"""
Unit tests for the SnakeGame logic.
"""
import pytest


@pytest.mark.gui
class TestSnakeGame:
    def _make_game(self, tk_root):
        from gui.apps.snake import SnakeGame
        app = type("App", (), {
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
        })()
        return SnakeGame(tk_root, app)

    def test_initial_snake_length(self, tk_root):
        game = self._make_game(tk_root)
        assert len(game._snake) == 3

    def test_initial_direction(self, tk_root):
        game = self._make_game(tk_root)
        assert game._direction == "Right"

    def test_initial_score(self, tk_root):
        game = self._make_game(tk_root)
        assert game._score == 0
        assert game._high_score == 0

    def test_not_running_initially(self, tk_root):
        game = self._make_game(tk_root)
        assert game._running is False
        assert game._game_over is False

    def test_place_food_not_on_snake(self, tk_root):
        game = self._make_game(tk_root)
        game._place_food()
        assert game._food is not None
        assert game._food not in game._snake

    def test_reset_restores_state(self, tk_root):
        game = self._make_game(tk_root)
        game._score = 50
        game._direction = "Left"
        game._running = True
        game._reset_game()
        assert game._score == 0
        assert game._direction == "Right"
        assert game._running is False
        assert len(game._snake) == 3

    def test_speed_update(self, tk_root):
        game = self._make_game(tk_root)
        game.speed_var.set(10)
        game._update_speed()
        assert game._speed < 120  # faster than default

    def test_direction_change_prevents_reverse(self, tk_root):
        """Snake moving Right should not be able to go Left directly."""
        game = self._make_game(tk_root)
        game._direction = "Right"
        event = type("Event", (), {"keysym": "Left"})()
        game._on_key(event)
        assert game._next_direction == "Right"  # unchanged

    def test_direction_change_allows_perpendicular(self, tk_root):
        """Snake moving Right should be able to go Up."""
        game = self._make_game(tk_root)
        game._direction = "Right"
        event = type("Event", (), {"keysym": "Up"})()
        game._on_key(event)
        assert game._next_direction == "Up"

    def test_wasd_controls(self, tk_root):
        """WASD keys should work for direction."""
        game = self._make_game(tk_root)
        game._direction = "Right"
        event = type("Event", (), {"keysym": "w"})()
        game._on_key(event)
        assert game._next_direction == "Up"

    def test_grid_dimensions(self, tk_root):
        game = self._make_game(tk_root)
        assert game.GRID_WIDTH == 30
        assert game.GRID_HEIGHT == 20
        assert game.CELL_SIZE == 20
