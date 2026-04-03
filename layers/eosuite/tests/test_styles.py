# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for ThemeManager and style definitions.
"""
import pytest

tk = pytest.importorskip("tkinter")

from gui.styles import DARK, LIGHT, ThemeManager


class TestColorDefinitions:
    """Test that color theme dictionaries are properly defined."""

    REQUIRED_KEYS = [
        "bg", "fg", "accent", "sidebar_bg", "toolbar_bg",
        "tab_bg", "tab_active", "input_bg", "input_fg",
        "border", "hover", "button_bg", "button_fg",
        "status_bg", "status_fg", "tree_bg", "tree_fg",
        "tree_select", "menu_bg", "menu_fg",
        "terminal_bg", "terminal_fg",
    ]

    def test_dark_has_all_keys(self):
        for key in self.REQUIRED_KEYS:
            assert key in DARK, f"DARK missing key: {key}"

    def test_light_has_all_keys(self):
        for key in self.REQUIRED_KEYS:
            assert key in LIGHT, f"LIGHT missing key: {key}"

    def test_dark_light_same_keys(self):
        assert set(DARK.keys()) == set(LIGHT.keys())

    def test_all_values_are_hex_colors(self):
        for name, theme in [("DARK", DARK), ("LIGHT", LIGHT)]:
            for key, value in theme.items():
                assert isinstance(value, str), f"{name}[{key}] is not a string"
                assert value.startswith("#"), f"{name}[{key}] = {value} is not a hex color"
                assert len(value) in (4, 7), f"{name}[{key}] = {value} has wrong length"

    def test_dark_and_light_differ(self):
        """Dark and light themes should have different bg colors."""
        assert DARK["bg"] != LIGHT["bg"]
        assert DARK["fg"] != LIGHT["fg"]


@pytest.mark.gui
class TestThemeManager:
    def test_initial_theme_is_dark(self, theme):
        assert theme.is_dark is True
        assert theme.colors == DARK

    def test_toggle_to_light(self, theme):
        theme.toggle()
        assert theme.is_dark is False
        assert theme.colors["bg"] == LIGHT["bg"]

    def test_toggle_back_to_dark(self, theme):
        theme.toggle()  # to light
        theme.toggle()  # back to dark
        assert theme.is_dark is True
        assert theme.colors["bg"] == DARK["bg"]

    def test_apply_light(self, theme):
        theme.apply("light")
        assert theme.is_dark is False
        assert theme.colors["bg"] == LIGHT["bg"]

    def test_apply_dark(self, theme):
        theme.apply("light")
        theme.apply("dark")
        assert theme.is_dark is True
        assert theme.colors["bg"] == DARK["bg"]

    def test_colors_is_copy(self, theme):
        """colors should be a copy, not the original dict."""
        theme.colors["bg"] = "#ff0000"
        assert DARK["bg"] != "#ff0000"
