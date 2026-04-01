# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for SSH client — connection string parsing.
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

def _make_dialog(tk_root):
    from gui.apps.ssh_client import SSHDialog
    app = type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "sidebar": type("S", (), {"add_ssh_session": lambda s, n, c: None})(),
        "connect_session": lambda self, c, n: None,
    })()
    return SSHDialog(tk_root, app)


@pytest.mark.gui
class TestSSHParsing:
    def test_user_at_host(self, tk_root):
        d = _make_dialog(tk_root)
        d.quick_var.set("admin@myserver.com")
        u, h, p = d._parse_quick()
        assert u == "admin" and h == "myserver.com" and p == "22"
        d.destroy()

    def test_user_host_port(self, tk_root):
        d = _make_dialog(tk_root)
        d.quick_var.set("root@10.0.0.1:2222")
        u, h, p = d._parse_quick()
        assert u == "root" and h == "10.0.0.1" and p == "2222"
        d.destroy()

    def test_host_only(self, tk_root):
        d = _make_dialog(tk_root)
        d.quick_var.set("myserver.com")
        u, h, p = d._parse_quick()
        assert u == "" and h == "myserver.com" and p == "22"
        d.destroy()

    def test_build_basic(self, tk_root):
        d = _make_dialog(tk_root)
        d.quick_var.set("user@host.com")
        assert d._build_command() == "ssh user@host.com"
        d.destroy()

    def test_build_with_port(self, tk_root):
        d = _make_dialog(tk_root)
        d.quick_var.set("user@host.com:2222")
        assert d._build_command() == "ssh -p 2222 user@host.com"
        d.destroy()

    def test_build_with_key(self, tk_root):
        d = _make_dialog(tk_root)
        d.quick_var.set("user@host.com")
        d.key_var.set("/path/to/key")
        assert "-i /path/to/key" in d._build_command()
        d.destroy()

    def test_name_auto(self, tk_root):
        d = _make_dialog(tk_root)
        d.quick_var.set("admin@prod")
        assert d._get_name() == "admin@prod"
        d.destroy()

    def test_name_custom(self, tk_root):
        d = _make_dialog(tk_root)
        d.quick_var.set("admin@prod")
        d.name_var.set("My Server")
        assert d._get_name() == "My Server"
        d.destroy()
"""
Unit tests for SSH client — connection string parsing.
"""
import pytest


@pytest.mark.gui
class TestSSHParsing:
    def _make_dialog(self, tk_root):
        from gui.apps.ssh_client import SSHDialog
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
            "sidebar": type("S", (), {"add_ssh_session": lambda s, n, c: None})(),
            "connect_session": lambda self, c, n: None,
        })()
        dialog = SSHDialog(tk_root, app)
        return dialog

    def test_parse_user_at_host(self, tk_root):
        d = self._make_dialog(tk_root)
        d.quick_var.set("admin@myserver.com")
        user, host, port = d._parse_quick()
        assert user == "admin"
        assert host == "myserver.com"
        assert port == "22"
        d.destroy()

    def test_parse_user_at_host_with_port(self, tk_root):
        d = self._make_dialog(tk_root)
        d.quick_var.set("root@10.0.0.1:2222")
        user, host, port = d._parse_quick()
        assert user == "root"
        assert host == "10.0.0.1"
        assert port == "2222"
        d.destroy()

    def test_parse_host_only(self, tk_root):
        d = self._make_dialog(tk_root)
        d.quick_var.set("myserver.com")
        user, host, port = d._parse_quick()
        assert user == ""
        assert host == "myserver.com"
        assert port == "22"
        d.destroy()

    def test_parse_host_with_port(self, tk_root):
        d = self._make_dialog(tk_root)
        d.quick_var.set("myserver.com:8022")
        user, host, port = d._parse_quick()
        assert user == ""
        assert host == "myserver.com"
        assert port == "8022"
        d.destroy()

    def test_build_command_basic(self, tk_root):
        d = self._make_dialog(tk_root)
        d.quick_var.set("user@host.com")
        cmd = d._build_command()
        assert cmd == "ssh user@host.com"
        d.destroy()

    def test_build_command_with_port(self, tk_root):
        d = self._make_dialog(tk_root)
        d.quick_var.set("user@host.com:2222")
        cmd = d._build_command()
        assert cmd == "ssh -p 2222 user@host.com"
        d.destroy()

    def test_build_command_with_key(self, tk_root):
        d = self._make_dialog(tk_root)
        d.quick_var.set("user@host.com")
        d.key_var.set("/path/to/key")
        cmd = d._build_command()
        assert "-i /path/to/key" in cmd
        d.destroy()

    def test_get_name_auto(self, tk_root):
        d = self._make_dialog(tk_root)
        d.quick_var.set("admin@prod-server")
        name = d._get_name()
        assert name == "admin@prod-server"
        d.destroy()

    def test_get_name_custom(self, tk_root):
        d = self._make_dialog(tk_root)
        d.quick_var.set("admin@prod-server")
        d.name_var.set("My Production")
        name = d._get_name()
        assert name == "My Production"
        d.destroy()
