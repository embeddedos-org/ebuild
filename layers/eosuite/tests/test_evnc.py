# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EVnc — VNC remote desktop viewer state and constants.
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


def _make_vnc(tk_root):
    from gui.apps.evnc import EVnc
    return EVnc(tk_root, type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "set_status": lambda self, t: None,
    })())


class TestEVncConstants:
    def test_viewers_defined(self):
        from gui.apps.evnc import EVnc
        assert hasattr(EVnc, "VIEWERS")
        assert len(EVnc.VIEWERS) >= 1

    def test_viewers_have_name_and_cmd(self):
        from gui.apps.evnc import EVnc
        for name, cmd in EVnc.VIEWERS:
            assert isinstance(name, str)
            assert isinstance(cmd, str)


@pytest.mark.gui
class TestEVnc:
    def test_initial_state(self, tk_root):
        vnc = _make_vnc(tk_root)
        assert vnc._process is None

    def test_default_port(self, tk_root):
        vnc = _make_vnc(tk_root)
        assert vnc.port_var.get() == "5900"

    def test_default_display(self, tk_root):
        vnc = _make_vnc(tk_root)
        assert vnc.display_var.get() == "0"

    def test_default_quality(self, tk_root):
        vnc = _make_vnc(tk_root)
        assert vnc.quality_var.get() == "Medium"

    def test_fullscreen_default_off(self, tk_root):
        vnc = _make_vnc(tk_root)
        assert vnc.fullscreen_var.get() is False

    def test_viewonly_default_off(self, tk_root):
        vnc = _make_vnc(tk_root)
        assert vnc.viewonly_var.get() is False

    def test_log_writes(self, tk_root):
        vnc = _make_vnc(tk_root)
        vnc._log("Test VNC log")
        content = vnc.log.get("1.0", "end")
        assert "Test VNC log" in content

    def test_disconnect_no_process(self, tk_root):
        vnc = _make_vnc(tk_root)
        vnc._disconnect()  # should not raise
        content = vnc.log.get("1.0", "end")
        assert "No active" in content

    def test_save_connection(self, tk_root):
        vnc = _make_vnc(tk_root)
        vnc.host_var.set("192.168.1.100")
        vnc.port_var.set("5901")
        vnc.display_var.set("1")
        vnc._save_connection()
        children = vnc.saved_tree.get_children()
        assert len(children) >= 1

    def test_save_empty_host_ignored(self, tk_root):
        vnc = _make_vnc(tk_root)
        initial_count = len(vnc.saved_tree.get_children())
        vnc.host_var.set("")
        vnc._save_connection()
        assert len(vnc.saved_tree.get_children()) == initial_count

    def test_remove_saved(self, tk_root):
        vnc = _make_vnc(tk_root)
        vnc.host_var.set("test-host")
        vnc._save_connection()
        children = vnc.saved_tree.get_children()
        assert len(children) >= 1
        vnc.saved_tree.selection_set(children[-1])
        vnc._remove_saved()

    def test_on_close_no_error(self, tk_root):
        vnc = _make_vnc(tk_root)
        vnc.on_close()  # should not raise

    def test_find_viewer_returns_tuple(self, tk_root):
        vnc = _make_vnc(tk_root)
        cmd, name = vnc._find_viewer()
        assert cmd is None or isinstance(cmd, str)
        assert name is None or isinstance(name, str)
