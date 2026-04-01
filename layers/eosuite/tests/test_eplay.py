# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EPlay — Media player state management.
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


def _make_player(tk_root):
    from gui.apps.eplay import EPlay
    return EPlay(tk_root, type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "set_status": lambda self, t: None,
        "notebook": tk_root,
    })())


@pytest.mark.gui
class TestEPlay:
    def test_initial_state(self, tk_root):
        p = _make_player(tk_root)
        assert p._filepath is None
        assert p._playing is False
        assert p._process is None

    def test_stop_sets_not_playing(self, tk_root):
        p = _make_player(tk_root)
        p._playing = True
        p._stop()
        assert p._playing is False

    def test_default_volume(self, tk_root):
        p = _make_player(tk_root)
        assert p.volume_var.get() == 75

    def test_playlist_empty(self, tk_root):
        p = _make_player(tk_root)
        assert p.playlist.size() == 0

    def test_prev_no_selection(self, tk_root):
        p = _make_player(tk_root)
        p._prev()  # should not raise

    def test_next_no_selection(self, tk_root):
        p = _make_player(tk_root)
        p._next()  # should not raise

    def test_rewind_sets_status(self, tk_root):
        statuses = []
        app = type("App", (), {
            "theme": type("T", (), {"colors": _colors()})(),
            "set_status": lambda self, t: statuses.append(t),
            "notebook": tk_root,
        })()
        from gui.apps.eplay import EPlay
        p = EPlay(tk_root, app)
        p._rewind()
        assert any("Rewind" in s for s in statuses)

    def test_forward_sets_status(self, tk_root):
        statuses = []
        app = type("App", (), {
            "theme": type("T", (), {"colors": _colors()})(),
            "set_status": lambda self, t: statuses.append(t),
            "notebook": tk_root,
        })()
        from gui.apps.eplay import EPlay
        p = EPlay(tk_root, app)
        p._forward()
        assert any("Forward" in s for s in statuses)

    def test_has_control_methods(self, tk_root):
        p = _make_player(tk_root)
        for method in ["_play_pause", "_stop", "_rewind", "_forward", "_prev", "_next"]:
            assert hasattr(p, method), f"EPlay missing {method}"
