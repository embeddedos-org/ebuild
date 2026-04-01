# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Shared pytest fixtures for EoSuite tests.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import tkinter as tk
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False
    # Provide lightweight tkinter stubs so gui.apps.* modules can be imported
    # for testing pure-logic helpers (formatters, parsers, constants).
    from unittest.mock import MagicMock

    _tk = MagicMock()
    for mod_name in (
        "tkinter", "tkinter.ttk", "tkinter.filedialog",
        "tkinter.messagebox", "tkinter.scrolledtext",
        "tkinter.colorchooser", "tkinter.simpledialog",
        "_tkinter",
    ):
        sys.modules.setdefault(mod_name, _tk)
    tk = _tk


def pytest_collection_modifyitems(config, items):
    """Skip GUI tests when tkinter is unavailable."""
    if not HAS_TKINTER:
        skip_gui = pytest.mark.skip(reason="tkinter not available")
        for item in items:
            if "gui" in item.keywords:
                item.add_marker(skip_gui)


@pytest.fixture(scope="session")
def tk_root():
    """Create a single Tk root for all GUI tests in the session."""
    pytest.importorskip("tkinter")
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def theme(tk_root):
    """Create a ThemeManager instance."""
    from gui.styles import ThemeManager
    return ThemeManager(tk_root)


@pytest.fixture
def tmp_sessions_file(tmp_path):
    """Provide a temporary sessions file path and patch the module."""
    import gui.apps.session_manager as sm
    original_file = sm.SESSIONS_FILE
    original_dir = sm.CONFIG_DIR
    sm.CONFIG_DIR = str(tmp_path)
    sm.SESSIONS_FILE = str(tmp_path / "sessions.json")
    yield sm.SESSIONS_FILE
    sm.CONFIG_DIR = original_dir
    sm.SESSIONS_FILE = original_file
