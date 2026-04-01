# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Unit tests for eCal - Basic, Scientific, and Tax Calculator."""
import pytest
tk = pytest.importorskip("tkinter")


def _colors():
    return {
        "bg": "#1e1e1e", "fg": "#d4d4d4", "accent": "#2998ff",
        "sidebar_bg": "#252526", "toolbar_bg": "#2d2d2d",
        "tab_bg": "#2d2d2d", "tab_active": "#1e1e1e",
        "input_bg": "#3c3c3c", "input_fg": "#d4d4d4",
        "border": "#3c3c3c", "hover": "#1a6ea8",
        "button_bg": "#258cd4", "button_fg": "#ffffff",
        "status_bg": "#1a8ef0", "status_fg": "#ffffff",
        "tree_bg": "#252526", "tree_fg": "#cccccc",
        "tree_select": "#1a5276", "menu_bg": "#2d2d2d",
        "menu_fg": "#cccccc", "terminal_bg": "#0c0c0c",
        "terminal_fg": "#cccccc",
    }


@pytest.mark.gui
class TestECal:
    def _make(c, tk_root):
        from gui.apps.ecal import ECal
        app = type("App", (), {"theme": type("T", (), {"colors": _colors(), "is_dark": True})(), "set_status": lambda self, t: None})()
        return ECal(tk_root, app)

    def test_basic_addition(self, tk_root):
        calc = self._make(tk_root)
        calc.basic_expression.set("2+3")
        calc._basic_press("=")
        assert calc.basic_result.get() == "5"

    def test_basic_subtraction(self, tk_root):
        calc = self._make(tk_root)
        calc.basic_expression.set("10-4")
        calc._basic_press("=")
        assert calc.basic_result.get() == "6"

    def test_multiplication(self, tk_root):
        calc = self._make(tk_root)
        calc.basic_expression.set("7*8")
        calc._basic_press("=")
        assert calc.basic_result.get() == "56"

    def test_division(self, tk_root):
        calc = self._make(tk_root)
        calc.basic_expression.set("20/5")
        calc._basic_press("=")
        assert calc.basic_result.get() == "4"

    def test_float_division(self, tk_root):
        calc = self._make(tk_root)
        calc.basic_expression.set("10/3")
        calc._basic_press("=")
        result = float(calc.basic_result.get())
        assert abs(result - 3.3333333333) < 0.001

    def test_complex_expression(self, tk_root):
        calc = self._make(tk_root)
        calc.basic_expression.set("2+3*2")
        calc._basic_press("=")
        assert calc.basic_result.get() == "8"

    def test_invalid_expression(self, tk_root):
        calc = self._make(tk_root)
        calc.basic_expression.set("2/0")
        calc._basic_press("=")
        assert "Error" in calc.basic_result.get()

    def test_clear_button(self, tk_root):
        calc = self._make(tk_root)
        calc.basic_expression.set("123")
        calc._basic_press("C")
        assert calc.basic_expression.get() == ""

    def test_modulo(self, tk_root):
        calc = self._make(tk_root)
        calc.basic_expression.set("10%3")
        calc._basic_press("=")
        assert calc.basic_result.get() == "1"

    def test_safe_eval_basic(self, tk_root):
        calc = self._make(tk_root)
        assert calc._safe_eval("2+3") == 5
        assert calc._safe_eval("10*5") == 50
        assert calc._safe_eval("2**3") == 8

    def test_safe_eval_div_zero(self, tk_root):
        calc = self._make(tk_root)
        try:
            result = calc._safe_eval("1/0")
            assert result is None or isinstance(result, (int, float, str))
        except ZeroDivisionError:
            pass

    def test_has_notebook(self, tk_root):
        calc = self._make(tk_root)
        assert hasattr(calc, "basic_expression")
        assert hasattr(calc, "basic_result")

    def test_tax_attributes(self, tk_root):
        calc = self._make(tk_root)
        assert hasattr(calc, "tax_income_var")
        assert hasattr(calc, "_calculate_tax")
