# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EChat — Chat interface with commands.
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


def _make_app():
    return type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "set_status": lambda self, t: None,
    })()


def _make_chat(tk_root):
    from gui.apps.echat import EChat
    return EChat(tk_root, _make_app())


@pytest.mark.gui
class TestEChat:
    def test_initial_username(self, tk_root):
        chat = _make_chat(tk_root)
        assert chat.name_var.get() == "You"

    def test_add_message(self, tk_root):
        chat = _make_chat(tk_root)
        chat._add_message("TestUser", "Hello World")
        content = chat.chat_display.get("1.0", tk.END)
        assert "TestUser" in content
        assert "Hello World" in content

    def test_add_system_message(self, tk_root):
        chat = _make_chat(tk_root)
        chat._add_system_message("System alert")
        content = chat.chat_display.get("1.0", tk.END)
        assert "System alert" in content

    def test_send_message_clears_input(self, tk_root):
        chat = _make_chat(tk_root)
        chat.input_var.set("test message")
        chat._send_message()
        assert chat.input_var.get() == ""

    def test_send_empty_message_ignored(self, tk_root):
        chat = _make_chat(tk_root)
        initial = chat.chat_display.get("1.0", tk.END)
        chat.input_var.set("   ")
        chat._send_message()
        assert chat.input_var.get() == "   "

    def test_custom_username(self, tk_root):
        chat = _make_chat(tk_root)
        chat.name_var.set("Alice")
        chat.input_var.set("hi there")
        chat._send_message()
        content = chat.chat_display.get("1.0", tk.END)
        assert "Alice" in content

    def test_handle_help_command(self, tk_root):
        chat = _make_chat(tk_root)
        chat._handle_command("/help")
        content = chat.chat_display.get("1.0", tk.END)
        assert "Commands" in content

    def test_handle_time_command(self, tk_root):
        chat = _make_chat(tk_root)
        chat._handle_command("/time")
        content = chat.chat_display.get("1.0", tk.END)
        assert "Current time" in content

    def test_handle_name_command(self, tk_root):
        chat = _make_chat(tk_root)
        chat._handle_command("/name NewName")
        assert chat.name_var.get() == "NewName"
        content = chat.chat_display.get("1.0", tk.END)
        assert "NewName" in content

    def test_handle_unknown_command(self, tk_root):
        chat = _make_chat(tk_root)
        chat._handle_command("/invalidcmd")
        content = chat.chat_display.get("1.0", tk.END)
        assert "Unknown command" in content

    def test_clear_command(self, tk_root):
        chat = _make_chat(tk_root)
        chat._add_message("user", "some text")
        chat._clear()
        content = chat.chat_display.get("1.0", tk.END).strip()
        assert "Chat cleared" in content

    def test_chat_display_is_readonly(self, tk_root):
        chat = _make_chat(tk_root)
        assert str(chat.chat_display.cget("state")) == "disabled"

    def test_welcome_messages_present(self, tk_root):
        chat = _make_chat(tk_root)
        content = chat.chat_display.get("1.0", tk.END)
        assert "Welcome to eChat" in content
