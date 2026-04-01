# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EFTP — FTP/SFTP client state and utility methods.
"""
import os
import pytest


class TestEFTPFormatSize:
    """Test _format_size utility without GUI."""

    def test_bytes(self):
        from gui.apps.eftp import EFTP
        ftp = EFTP.__new__(EFTP)
        assert "B" in ftp._format_size(512)

    def test_kilobytes(self):
        from gui.apps.eftp import EFTP
        ftp = EFTP.__new__(EFTP)
        result = ftp._format_size(2048)
        assert "KB" in result

    def test_megabytes(self):
        from gui.apps.eftp import EFTP
        ftp = EFTP.__new__(EFTP)
        result = ftp._format_size(5 * 1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self):
        from gui.apps.eftp import EFTP
        ftp = EFTP.__new__(EFTP)
        result = ftp._format_size(3 * 1024 * 1024 * 1024)
        assert "GB" in result

    def test_zero(self):
        from gui.apps.eftp import EFTP
        ftp = EFTP.__new__(EFTP)
        assert "0 B" in ftp._format_size(0)


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


def _make_ftp(tk_root):
    from gui.apps.eftp import EFTP
    return EFTP(tk_root, type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "set_status": lambda self, t: None,
    })())


@pytest.mark.gui
class TestEFTPGUI:
    def test_initial_state(self, tk_root):
        ftp = _make_ftp(tk_root)
        assert ftp.remote_host == ""
        assert ftp.remote_user == ""
        assert ftp.remote_port == 22

    def test_local_path_default(self, tk_root):
        ftp = _make_ftp(tk_root)
        assert ftp.local_path == os.path.expanduser("~")

    def test_remote_path_default(self, tk_root):
        ftp = _make_ftp(tk_root)
        assert ftp.remote_path == "/"

    def test_default_port(self, tk_root):
        ftp = _make_ftp(tk_root)
        assert ftp.port_var.get() == "22"

    def test_default_protocol(self, tk_root):
        ftp = _make_ftp(tk_root)
        assert ftp.proto_var.get() == "SFTP"

    def test_disconnect_clears_remote(self, tk_root):
        ftp = _make_ftp(tk_root)
        ftp.remote_tree.insert("", "end", text="test", values=("1KB", "rwx"))
        ftp._disconnect()
        assert len(ftp.remote_tree.get_children()) == 0

    def test_log_writes(self, tk_root):
        ftp = _make_ftp(tk_root)
        ftp._log("Test log message")
        content = ftp.log_text.get("1.0", "end")
        assert "Test log message" in content

    def test_conn_status_initial(self, tk_root):
        ftp = _make_ftp(tk_root)
        assert "Disconnected" in ftp.conn_status.cget("text")

    def test_status_var_initial(self, tk_root):
        ftp = _make_ftp(tk_root)
        assert ftp.status_var.get() == "Disconnected"

    def test_on_close_no_error(self, tk_root):
        ftp = _make_ftp(tk_root)
        ftp.on_close()

    def test_local_up(self, tk_root):
        ftp = _make_ftp(tk_root)
        ftp.local_path_var.set(os.path.expanduser("~"))
        ftp._local_up()

    def test_get_selected_names_empty(self, tk_root):
        ftp = _make_ftp(tk_root)
        names = ftp._get_selected_names(ftp.local_tree)
        assert names == []
