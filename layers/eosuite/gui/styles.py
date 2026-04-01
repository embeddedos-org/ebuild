# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite GUI Styles — Dark/Light theme definitions for ttk widgets.
"""
import tkinter as tk
from tkinter import ttk

DARK = {
    "bg": "#1e1e1e",
    "fg": "#d4d4d4",
    "accent": "#2998ff",
    "sidebar_bg": "#252526",
    "toolbar_bg": "#2d2d2d",
    "tab_bg": "#2d2d2d",
    "tab_active": "#1e1e1e",
    "input_bg": "#3c3c3c",
    "input_fg": "#d4d4d4",
    "border": "#3c3c3c",
    "hover": "#1a6ea8",
    "button_bg": "#258cd4",
    "button_fg": "#ffffff",
    "status_bg": "#1a8ef0",
    "status_fg": "#ffffff",
    "tree_bg": "#252526",
    "tree_fg": "#cccccc",
    "tree_select": "#1a5276",
    "menu_bg": "#2d2d2d",
    "menu_fg": "#cccccc",
    "terminal_bg": "#0c0c0c",
    "terminal_fg": "#cccccc",
}

LIGHT = {
    "bg": "#f3f3f3",
    "fg": "#1e1e1e",
    "accent": "#2998ff",
    "sidebar_bg": "#e8e8e8",
    "toolbar_bg": "#e0e0e0",
    "tab_bg": "#ececec",
    "tab_active": "#ffffff",
    "input_bg": "#ffffff",
    "input_fg": "#1e1e1e",
    "border": "#c8c8c8",
    "hover": "#c0def5",
    "button_bg": "#0078d4",
    "button_fg": "#ffffff",
    "status_bg": "#1a8ef0",
    "status_fg": "#ffffff",
    "tree_bg": "#ffffff",
    "tree_fg": "#1e1e1e",
    "tree_select": "#c0def5",
    "menu_bg": "#f0f0f0",
    "menu_fg": "#1e1e1e",
    "terminal_bg": "#ffffff",
    "terminal_fg": "#1e1e1e",
}


class ThemeManager:
    """Manages dark/light theme switching for the application."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.style = ttk.Style(root)
        self._current = "dark"
        self.colors = DARK.copy()
        self._configure_base_styles()

    @property
    def is_dark(self) -> bool:
        return self._current == "dark"

    def toggle(self):
        self.apply("light" if self._current == "dark" else "dark")

    def apply(self, theme: str):
        self._current = theme
        self.colors = (DARK if theme == "dark" else LIGHT).copy()
        self._configure_base_styles()
        self.root.event_generate("<<ThemeChanged>>")

    def _configure_base_styles(self):
        c = self.colors
        s = self.style

        s.theme_use("clam")

        s.configure(".", background=c["bg"], foreground=c["fg"],
                     borderwidth=0, focusthickness=0)

        s.configure("TFrame", background=c["bg"])
        s.configure("Sidebar.TFrame", background=c["sidebar_bg"])
        s.configure("Toolbar.TFrame", background=c["toolbar_bg"])
        s.configure("Status.TFrame", background=c["status_bg"])

        s.configure("TLabel", background=c["bg"], foreground=c["fg"])
        s.configure("Sidebar.TLabel", background=c["sidebar_bg"],
                     foreground=c["fg"])
        s.configure("Toolbar.TLabel", background=c["toolbar_bg"],
                     foreground=c["fg"])
        s.configure("Status.TLabel", background=c["status_bg"],
                     foreground=c["status_fg"])
        s.configure("Brand.TLabel", background=c["bg"], foreground=c["accent"],
                     font=("Segoe UI", 24, "bold"))
        s.configure("Subtitle.TLabel", background=c["bg"], foreground=c["fg"],
                     font=("Segoe UI", 11))

        s.configure("TButton", background=c["button_bg"],
                     foreground=c["button_fg"], padding=(12, 6),
                     font=("Segoe UI", 10))
        s.map("TButton",
              background=[("active", c["hover"]), ("pressed", c["accent"])],
              foreground=[("active", c["button_fg"])])

        s.configure("Toolbar.TButton", background=c["toolbar_bg"],
                     foreground=c["fg"], padding=(8, 4),
                     font=("Segoe UI", 9))
        s.map("Toolbar.TButton",
              background=[("active", c["hover"])],
              foreground=[("active", c["fg"])])

        s.configure("Sidebar.TButton", background=c["sidebar_bg"],
                     foreground=c["fg"], padding=(6, 3),
                     font=("Segoe UI", 9))
        s.map("Sidebar.TButton",
              background=[("active", c["hover"])],
              foreground=[("active", c["fg"])])

        s.configure("TNotebook", background=c["bg"], borderwidth=0)
        s.configure("TNotebook.Tab", background=c["tab_bg"],
                     foreground=c["fg"], padding=(14, 6),
                     font=("Segoe UI", 10))
        s.map("TNotebook.Tab",
              background=[("selected", c["tab_active"])],
              foreground=[("selected", c["fg"])])

        s.configure("Treeview", background=c["tree_bg"],
                     foreground=c["tree_fg"], fieldbackground=c["tree_bg"],
                     borderwidth=0, font=("Segoe UI", 10))
        s.map("Treeview",
              background=[("selected", c["tree_select"])],
              foreground=[("selected", c["fg"])])
        s.configure("Treeview.Heading", background=c["toolbar_bg"],
                     foreground=c["fg"], font=("Segoe UI", 10, "bold"))

        s.configure("TEntry", fieldbackground=c["input_bg"],
                     foreground=c["input_fg"], borderwidth=1, padding=(6, 4))

        s.configure("TSeparator", background=c["border"])
        s.configure("TPanedwindow", background=c["border"])
        s.configure("TScrollbar", background=c["toolbar_bg"],
                     troughcolor=c["bg"], borderwidth=0)
        s.configure("TProgressbar", background=c["accent"],
                     troughcolor=c["input_bg"])

        self.root.configure(bg=c["bg"])
