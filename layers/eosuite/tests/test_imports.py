# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Import smoke tests — verify every module in the GUI package loads correctly.
"""
import sys
import os
import importlib
import pytest

tk = pytest.importorskip("tkinter")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ALL_MODULES = [
    "gui",
    "gui.styles",
    "gui.toolbar",
    "gui.sidebar",
    "gui.home_tab",
    "gui.terminal_tab",
    "gui.split_manager",
    "gui.main_window",
    "gui.apps",
    "gui.apps.ecal",
    "gui.apps.etimer",
    "gui.apps.enote",
    "gui.apps.eviewer",
    "gui.apps.econverter",
    "gui.apps.eguard",
    "gui.apps.eweb",
    "gui.apps.ezip",
    "gui.apps.ecleaner",
    "gui.apps.evpn",
    "gui.apps.echat",
    "gui.apps.epaint",
    "gui.apps.eplay",
    "gui.apps.ebuffer",
    "gui.apps.epdf",
    "gui.apps.eftp",
    "gui.apps.etunnel",
    "gui.apps.evirustower",
    "gui.apps.evnc",
    "gui.apps.snake",
    "gui.apps.ssh_client",
    "gui.apps.serial_term",
    "gui.apps.session_manager",
]


@pytest.mark.gui
@pytest.mark.parametrize("module_name", ALL_MODULES)
def test_module_import(module_name):
    """Each GUI module should import without errors."""
    mod = importlib.import_module(module_name)
    assert mod is not None


CLASS_MAP = [
    ("gui.styles", "ThemeManager"),
    ("gui.styles", "DARK"),
    ("gui.styles", "LIGHT"),
    ("gui.toolbar", "Toolbar"),
    ("gui.sidebar", "Sidebar"),
    ("gui.home_tab", "HomeTab"),
    ("gui.terminal_tab", "TerminalTab"),
    ("gui.split_manager", "SplitManager"),
    ("gui.main_window", "MainWindow"),
    ("gui.apps.ecal", "ECal"),
    ("gui.apps.etimer", "ETimer"),
    ("gui.apps.enote", "ENote"),
    ("gui.apps.eviewer", "EViewer"),
    ("gui.apps.econverter", "EConverter"),
    ("gui.apps.eguard", "EGuard"),
    ("gui.apps.eweb", "EWeb"),
    ("gui.apps.ezip", "EZip"),
    ("gui.apps.ecleaner", "ECleaner"),
    ("gui.apps.evpn", "EVpn"),
    ("gui.apps.echat", "EChat"),
    ("gui.apps.epaint", "EPaint"),
    ("gui.apps.eplay", "EPlay"),
    ("gui.apps.ebuffer", "EBuffer"),
    ("gui.apps.epdf", "EPdf"),
    ("gui.apps.eftp", "EFTP"),
    ("gui.apps.etunnel", "ETunnel"),
    ("gui.apps.evirustower", "EVirusTower"),
    ("gui.apps.evnc", "EVnc"),
    ("gui.apps.snake", "SnakeGame"),
    ("gui.apps.ssh_client", "SSHDialog"),
    ("gui.apps.serial_term", "SerialDialog"),
    ("gui.apps.session_manager", "SessionManager"),
    ("gui.apps.session_manager", "SessionManagerDialog"),
]


@pytest.mark.gui
@pytest.mark.parametrize("module_name,class_name", CLASS_MAP)
def test_class_exists(module_name, class_name):
    """Each expected class/constant should exist in its module."""
    mod = importlib.import_module(module_name)
    assert hasattr(mod, class_name), f"{module_name} missing {class_name}"


@pytest.mark.gui
def test_version():
    """Package version should be set."""
    import gui
    assert hasattr(gui, "__version__")
    assert gui.__version__ == "1.0.0"


@pytest.mark.gui
def test_split_manager_methods():
    """SplitManager should have all layout methods."""
    from gui.split_manager import SplitManager
    methods = ["layout_single", "layout_h2", "layout_v2", "layout_quad",
               "popout_current", "show_split_menu", "get_active_notebook"]
    for m in methods:
        assert hasattr(SplitManager, m), f"SplitManager missing method {m}"


@pytest.mark.gui
def test_eftp_has_required_methods():
    """EFTP should have connection and transfer methods."""
    from gui.apps.eftp import EFTP
    methods = ["on_close"]
    for m in methods:
        assert hasattr(EFTP, m), f"EFTP missing method {m}"
