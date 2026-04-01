# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EClock — Multi-city world clock.
"""
import datetime
import tkinter as tk
import pytest


class TestTimezoneDB:
    """Test the timezone database and constants (headless)."""

    def test_timezone_db_exists(self):
        from gui.apps.eclock import TIMEZONE_DB
        assert isinstance(TIMEZONE_DB, dict)
        assert len(TIMEZONE_DB) >= 30

    def test_default_cities_exist(self):
        from gui.apps.eclock import DEFAULT_CITIES
        assert isinstance(DEFAULT_CITIES, list)
        assert len(DEFAULT_CITIES) == 10

    def test_all_default_cities_in_db(self):
        from gui.apps.eclock import TIMEZONE_DB, DEFAULT_CITIES
        for city in DEFAULT_CITIES:
            assert city in TIMEZONE_DB, f"{city} not in TIMEZONE_DB"

    def test_timezone_entry_format(self):
        from gui.apps.eclock import TIMEZONE_DB
        for city, (tz_label, offset) in TIMEZONE_DB.items():
            assert isinstance(tz_label, str) and len(tz_label) > 0
            assert isinstance(offset, (int, float))

    def test_known_offsets(self):
        from gui.apps.eclock import TIMEZONE_DB
        assert TIMEZONE_DB["London"][1] == 0
        assert TIMEZONE_DB["New York"][1] == -5
        assert TIMEZONE_DB["Tokyo"][1] == 9
        assert TIMEZONE_DB["Mumbai"][1] == 5.5
        assert TIMEZONE_DB["Sydney"][1] == 10

    def test_half_hour_offsets(self):
        from gui.apps.eclock import TIMEZONE_DB
        assert TIMEZONE_DB["Mumbai"][1] == 5.5
        assert TIMEZONE_DB["Kolkata"][1] == 5.5


class TestEClockStaticMethods:
    """Test static helper methods (headless)."""

    def test_get_city_time_known(self):
        from gui.apps.eclock import EClock
        result = EClock.get_city_time("London")
        assert isinstance(result, datetime.datetime)

    def test_get_city_time_unknown(self):
        from gui.apps.eclock import EClock
        assert EClock.get_city_time("Atlantis") is None

    def test_fmt_time(self):
        from gui.apps.eclock import EClock
        dt = datetime.datetime(2026, 3, 15, 14, 30, 45)
        assert EClock.fmt_time(dt) == "14:30:45"

    def test_fmt_time_midnight(self):
        from gui.apps.eclock import EClock
        dt = datetime.datetime(2026, 1, 1, 0, 0, 0)
        assert EClock.fmt_time(dt) == "00:00:00"

    def test_fmt_date(self):
        from gui.apps.eclock import EClock
        dt = datetime.datetime(2026, 3, 15, 14, 30, 45)
        result = EClock.fmt_date(dt)
        assert "Mar" in result
        assert "15" in result

    def test_fmt_date_contains_weekday(self):
        from gui.apps.eclock import EClock
        dt = datetime.datetime(2026, 3, 15, 0, 0, 0)
        result = EClock.fmt_date(dt)
        assert result.startswith("Sun")


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


def _make_clock(tk_root):
    from gui.apps.eclock import EClock
    clock = EClock(tk_root, type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "set_status": lambda self, t: None,
    })())
    return clock


@pytest.mark.gui
class TestEClockGUI:
    def test_initial_city_count(self, tk_root):
        clock = _make_clock(tk_root)
        assert len(clock._cities) == 10
        clock.on_close()

    def test_initial_selected_city(self, tk_root):
        clock = _make_clock(tk_root)
        assert clock._selected_city == "New York"
        clock.on_close()

    def test_add_city(self, tk_root):
        clock = _make_clock(tk_root)
        clock.add_var.set("Paris")
        clock._add_city()
        assert "Paris" in clock._cities
        assert len(clock._cities) == 11
        clock.on_close()

    def test_add_duplicate_city_ignored(self, tk_root):
        clock = _make_clock(tk_root)
        clock.add_var.set("London")
        clock._add_city()
        count = clock._cities.count("London")
        assert count == 1
        clock.on_close()

    def test_add_unknown_city_ignored(self, tk_root):
        clock = _make_clock(tk_root)
        initial = len(clock._cities)
        clock.add_var.set("Atlantis")
        clock._add_city()
        assert len(clock._cities) == initial
        clock.on_close()

    def test_add_empty_ignored(self, tk_root):
        clock = _make_clock(tk_root)
        initial = len(clock._cities)
        clock.add_var.set("")
        clock._add_city()
        assert len(clock._cities) == initial
        clock.on_close()

    def test_remove_prevents_empty(self, tk_root):
        clock = _make_clock(tk_root)
        clock._cities = ["London"]
        clock._update_times()
        children = clock.tree.get_children()
        if children:
            clock.tree.selection_set(children[0])
        clock._remove_city()
        assert len(clock._cities) >= 1
        clock.on_close()

    def test_on_close_cancels_timer(self, tk_root):
        clock = _make_clock(tk_root)
        assert clock._after_id is not None
        clock.on_close()
        assert clock._after_id is None

    def test_tree_has_columns(self, tk_root):
        clock = _make_clock(tk_root)
        cols = clock.tree.cget("columns")
        assert "City" in cols
        assert "Time" in cols
        assert "Date" in cols
        clock.on_close()

    def test_update_times_populates_tree(self, tk_root):
        clock = _make_clock(tk_root)
        clock._update_times()
        children = clock.tree.get_children()
        assert len(children) == len(clock._cities)
        clock.on_close()

    def test_tree_shows_city_names(self, tk_root):
        clock = _make_clock(tk_root)
        clock._update_times()
        children = clock.tree.get_children()
        cities_in_tree = [clock.tree.item(c)["values"][0] for c in children]
        assert "London" in cities_in_tree
        assert "Tokyo" in cities_in_tree
        clock.on_close()
