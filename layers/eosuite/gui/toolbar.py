# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Toolbar — Icon toolbar with Unicode-symbol buttons.
"""
import tkinter as tk
from tkinter import ttk


class Toolbar(ttk.Frame):
    """Top icon toolbar mirroring MobaXterm layout."""

    BUTTONS = [
        ("🖥", "Session", "new_session"),
        ("🖧", "Servers", "servers"),
        ("🔧", "Tools", "tools_menu"),
        ("🎮", "Games", "games_menu"),
        ("👁", "View", "toggle_view"),
        ("⬓", "Split", "split_view"),
        ("⚙", "Settings", "open_settings"),
        ("❓", "Help", "open_help"),
        ("🌓", "Theme", "toggle_theme"),
        ("✕", "Exit", "exit_app"),
    ]

    def __init__(self, parent, app):
        super().__init__(parent, style="Toolbar.TFrame")
        self.app = app
        self._buttons = {}
        self._build()

    def _build(self):
        for icon, label, cmd_name in self.BUTTONS:
            btn = ttk.Button(
                self,
                text=f" {icon} {label}",
                style="Toolbar.TButton",
                command=lambda c=cmd_name: self._dispatch(c),
            )
            btn.pack(side=tk.LEFT, padx=2, pady=3)
            self._buttons[cmd_name] = btn

        # Spacer to push right-aligned items
        spacer = ttk.Frame(self, style="Toolbar.TFrame")
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _dispatch(self, command: str):
        handler = getattr(self.app, command, None)
        if handler:
            handler()

    def update_theme(self, colors: dict):
        pass  # Styles handle this via ThemeManager
