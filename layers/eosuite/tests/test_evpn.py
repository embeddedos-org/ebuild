# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EVpn — VPN/proxy manager state and connection logic.
"""
import tkinter as tk
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


def _make_vpn(tk_root):
    from gui.apps.evpn import EVpn
    return EVpn(tk_root, type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "set_status": lambda self, t: None,
    })())


class TestFreeProxyAPIs:
    def test_apis_defined(self):
        from gui.apps.evpn import FREE_PROXY_APIS
        assert isinstance(FREE_PROXY_APIS, list)
        assert len(FREE_PROXY_APIS) >= 1

    def test_each_api_has_name_and_url(self):
        from gui.apps.evpn import FREE_PROXY_APIS
        for name, url in FREE_PROXY_APIS:
            assert isinstance(name, str) and len(name) > 0
            assert url.startswith("http")


@pytest.mark.gui
class TestEVpn:
    def test_initial_state_disconnected(self, tk_root):
        vpn = _make_vpn(tk_root)
        assert vpn._connected is False

    def test_vpn_connect_sets_connected(self, tk_root):
        vpn = _make_vpn(tk_root)
        vpn.server_var.set("test.vpn.com")
        vpn._vpn_connect()
        assert vpn._connected is True
        assert "Connected" in vpn.status_label.cget("text")

    def test_vpn_disconnect(self, tk_root):
        vpn = _make_vpn(tk_root)
        vpn._connected = True
        vpn._vpn_disconnect()
        assert vpn._connected is False
        assert "Disconnected" in vpn.status_label.cget("text")

    def test_vpn_log_writes(self, tk_root):
        vpn = _make_vpn(tk_root)
        vpn._vpn_log_msg("Test VPN log")
        content = vpn.vpn_log.get("1.0", tk.END)
        assert "Test VPN log" in content

    def test_default_server_value(self, tk_root):
        vpn = _make_vpn(tk_root)
        assert "vpn.example.com" in vpn.server_var.get()

    def test_default_protocol(self, tk_root):
        vpn = _make_vpn(tk_root)
        assert vpn.protocol_var.get() == "OpenVPN"

    def test_ssh_vars_exist(self, tk_root):
        vpn = _make_vpn(tk_root)
        assert "ssh_host" in vpn.ssh_vars
        assert "ssh_user" in vpn.ssh_vars
        assert "ssh_port" in vpn.ssh_vars
        assert "socks_port" in vpn.ssh_vars

    def test_default_socks_port(self, tk_root):
        vpn = _make_vpn(tk_root)
        assert vpn.ssh_vars["socks_port"].get() == "1080"

    def test_default_ssh_port(self, tk_root):
        vpn = _make_vpn(tk_root)
        assert vpn.ssh_vars["ssh_port"].get() == "22"

    def test_status_var_initial(self, tk_root):
        vpn = _make_vpn(tk_root)
        assert vpn.status_var.get() == "Disconnected"

    def test_on_close_no_error(self, tk_root):
        vpn = _make_vpn(tk_root)
        vpn.on_close()  # should not raise

    def test_country_default(self, tk_root):
        vpn = _make_vpn(tk_root)
        assert vpn.country_var.get() == "all"

    def test_proxy_type_default(self, tk_root):
        vpn = _make_vpn(tk_root)
        assert vpn.proxy_type_var.get() == "socks5"
