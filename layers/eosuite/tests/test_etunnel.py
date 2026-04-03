# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for eTunnel — SSH tunneling command generation and state management.
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

def _make_tunnel(tk_root):
    from gui.apps.etunnel import ETunnel
    return ETunnel(tk_root, _make_app())


@pytest.mark.gui
class TestETunnelCommandPreview:
    def test_local_forward_default(self, tk_root):
        t = _make_tunnel(tk_root)
        t.type_var.set("Local (-L)")
        t.host_var.set("myserver.com")
        t.user_var.set("admin")
        t.local_port_var.set("8080")
        t.remote_var.set("localhost:80")
        t.ssh_port_var.set("22")
        t._update_preview()
        cmd = t.preview_var.get()
        assert "ssh -N -L" in cmd
        assert "8080:localhost:80" in cmd
        assert "admin@myserver.com" in cmd
        assert "-p" not in cmd

    def test_local_forward_custom_port(self, tk_root):
        t = _make_tunnel(tk_root)
        t.type_var.set("Local (-L)")
        t.host_var.set("server.io")
        t.user_var.set("root")
        t.local_port_var.set("3306")
        t.remote_var.set("db-host:3306")
        t.ssh_port_var.set("2222")
        t._update_preview()
        cmd = t.preview_var.get()
        assert "-p 2222" in cmd
        assert "3306:db-host:3306" in cmd
        assert "root@server.io" in cmd

    def test_remote_forward(self, tk_root):
        t = _make_tunnel(tk_root)
        t.type_var.set("Remote (-R)")
        t.host_var.set("gateway.com")
        t.user_var.set("user")
        t.local_port_var.set("9090")
        t.remote_var.set("localhost:3000")
        t.ssh_port_var.set("22")
        t._update_preview()
        cmd = t.preview_var.get()
        assert "ssh -N -R" in cmd
        assert "9090:localhost:3000" in cmd

    def test_dynamic_socks(self, tk_root):
        t = _make_tunnel(tk_root)
        t.type_var.set("Dynamic SOCKS (-D)")
        t.host_var.set("proxy.net")
        t.user_var.set("socks")
        t.local_port_var.set("1080")
        t.ssh_port_var.set("22")
        t._update_preview()
        cmd = t.preview_var.get()
        assert "ssh -N -D" in cmd
        assert "1080" in cmd
        assert "socks@proxy.net" in cmd

    def test_no_user(self, tk_root):
        t = _make_tunnel(tk_root)
        t.type_var.set("Local (-L)")
        t.host_var.set("bare-host.com")
        t.user_var.set("")
        t.local_port_var.set("5000")
        t.remote_var.set("localhost:5000")
        t.ssh_port_var.set("22")
        t._update_preview()
        cmd = t.preview_var.get()
        assert "bare-host.com" in cmd
        assert "@" not in cmd


@pytest.mark.gui
class TestETunnelState:
    def test_initial_state(self, tk_root):
        t = _make_tunnel(tk_root)
        assert t._tunnels == []
        assert t.type_var.get() == "Local (-L)"
        assert t.local_port_var.get() == "8080"

    def test_stop_all_clears(self, tk_root):
        t = _make_tunnel(tk_root)
        t._tunnels.append({"process": type("P", (), {"terminate": lambda s: None})(),
                           "type": "Local", "local": "8080",
                           "remote": "localhost:80", "host": "test"})
        t.tree.insert("", "end", values=("Local", "8080", "localhost:80", "test", "Running"))
        t._stop_all()
        assert t._tunnels == []
        assert len(t.tree.get_children()) == 0

    def test_on_close_terminates(self, tk_root):
        t = _make_tunnel(tk_root)
        stopped = []
        t._tunnels.append({"process": type("P", (), {"terminate": lambda s: stopped.append(1)})(),
                           "type": "Local", "local": "8080",
                           "remote": "localhost:80", "host": "test"})
        t.on_close()
        assert len(stopped) == 1

    def test_log_writes(self, tk_root):
        t = _make_tunnel(tk_root)
        t._log("Test message")
        assert "Test message" in t.log_text.get("1.0", "end")

    def test_preview_updates(self, tk_root):
        t = _make_tunnel(tk_root)
        t.host_var.set("a.com")
        t._update_preview()
        assert "a.com" in t.preview_var.get()
        t.host_var.set("b.com")
        t._update_preview()
        assert "b.com" in t.preview_var.get()
        assert "a.com" not in t.preview_var.get()
"""
Unit tests for eTunnel — SSH tunneling command generation and state management.
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

def _make_app():
    return type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "set_status": lambda self, t: None,
    })()

def _make_tunnel(tk_root):
    from gui.apps.etunnel import ETunnel
    return ETunnel(tk_root, _make_app())


@pytest.mark.gui
class TestETunnelCommandPreview:
    """Test SSH command string generation."""

    def test_local_forward_default(self, tk_root):
        t = _make_tunnel(tk_root)
        t.type_var.set("Local (-L)")
        t.host_var.set("myserver.com")
        t.user_var.set("admin")
        t.local_port_var.set("8080")
        t.remote_var.set("localhost:80")
        t.ssh_port_var.set("22")
        t._update_preview()
        cmd = t.preview_var.get()
        assert "ssh -N -L" in cmd
        assert "8080:localhost:80" in cmd
        assert "admin@myserver.com" in cmd
        assert "-p" not in cmd  # port 22 is default, no -p flag

    def test_local_forward_custom_port(self, tk_root):
        t = _make_tunnel(tk_root)
        t.type_var.set("Local (-L)")
        t.host_var.set("server.io")
        t.user_var.set("root")
        t.local_port_var.set("3306")
        t.remote_var.set("db-host:3306")
        t.ssh_port_var.set("2222")
        t._update_preview()
        cmd = t.preview_var.get()
        assert "-p 2222" in cmd
        assert "3306:db-host:3306" in cmd
        assert "root@server.io" in cmd

    def test_remote_forward(self, tk_root):
        t = _make_tunnel(tk_root)
        t.type_var.set("Remote (-R)")
        t.host_var.set("gateway.com")
        t.user_var.set("user")
        t.local_port_var.set("9090")
        t.remote_var.set("localhost:3000")
        t.ssh_port_var.set("22")
        t._update_preview()
        cmd = t.preview_var.get()
        assert "ssh -N -R" in cmd
        assert "9090:localhost:3000" in cmd
        assert "user@gateway.com" in cmd

    def test_dynamic_socks(self, tk_root):
        t = _make_tunnel(tk_root)
        t.type_var.set("Dynamic SOCKS (-D)")
        t.host_var.set("proxy.net")
        t.user_var.set("socks")
        t.local_port_var.set("1080")
        t.ssh_port_var.set("22")
        t._update_preview()
        cmd = t.preview_var.get()
        assert "ssh -N -D" in cmd
        assert "1080" in cmd
        assert "socks@proxy.net" in cmd
        assert "-L" not in cmd
        assert "-R" not in cmd

    def test_no_user(self, tk_root):
        t = _make_tunnel(tk_root)
        t.type_var.set("Local (-L)")
        t.host_var.set("bare-host.com")
        t.user_var.set("")
        t.local_port_var.set("5000")
        t.remote_var.set("localhost:5000")
        t.ssh_port_var.set("22")
        t._update_preview()
        cmd = t.preview_var.get()
        assert "bare-host.com" in cmd
        assert "@" not in cmd


@pytest.mark.gui
class TestETunnelState:
    """Test tunnel state management."""

    def test_initial_state(self, tk_root):
        t = _make_tunnel(tk_root)
        assert t._tunnels == []
        assert t.type_var.get() == "Local (-L)"
        assert t.local_port_var.get() == "8080"
        assert t.remote_var.get() == "localhost:80"
        assert t.ssh_port_var.get() == "22"

    def test_stop_all_clears_list(self, tk_root):
        t = _make_tunnel(tk_root)
        # Simulate having a tunnel (without a real process)
        t._tunnels.append({"process": type("P", (), {"terminate": lambda s: None})(),
                           "type": "Local", "local": "8080",
                           "remote": "localhost:80", "host": "test"})
        t.tree.insert("", "end", values=("Local", "8080", "localhost:80", "test", "Running"))
        assert len(t._tunnels) == 1
        assert len(t.tree.get_children()) == 1

        t._stop_all()
        assert t._tunnels == []
        assert len(t.tree.get_children()) == 0

    def test_on_close_stops_tunnels(self, tk_root):
        t = _make_tunnel(tk_root)
        stopped = []
        t._tunnels.append({"process": type("P", (), {"terminate": lambda s: stopped.append(True)})(),
                           "type": "Local", "local": "8080",
                           "remote": "localhost:80", "host": "test"})
        t.on_close()
        assert len(stopped) == 1
        assert t._tunnels == []

    def test_log_writes_text(self, tk_root):
        t = _make_tunnel(tk_root)
        t._log("Test message")
        content = t.log_text.get("1.0", "end").strip()
        assert "Test message" in content

    def test_preview_updates_on_change(self, tk_root):
        t = _make_tunnel(tk_root)
        t.host_var.set("initial.com")
        t._update_preview()
        cmd1 = t.preview_var.get()
        assert "initial.com" in cmd1

        t.host_var.set("changed.com")
        t._update_preview()
        cmd2 = t.preview_var.get()
        assert "changed.com" in cmd2
        assert "initial.com" not in cmd2
