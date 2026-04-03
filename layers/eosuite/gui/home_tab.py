# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Home Tab — Dashboard shown on startup.
"""
import tkinter as tk
from tkinter import ttk


class HomeTab(ttk.Frame):
    """Home dashboard tab with quick-access buttons and recent sessions."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        # Outer container centered
        container = ttk.Frame(self)
        container.place(relx=0.5, rely=0.42, anchor=tk.CENTER)

        # Branding
        ttk.Label(container, text="⚡ EoSuite", style="Brand.TLabel").pack(
            pady=(0, 4)
        )
        ttk.Label(
            container,
            text="Multi-tool terminal suite  •  v1.1.0",
            style="Subtitle.TLabel",
        ).pack(pady=(0, 24))

        # Quick actions row
        actions = ttk.Frame(container)
        actions.pack(pady=8)

        btn_data = [
            ("🖥  Start Local Terminal", self.app.start_local_terminal),
            ("🔐  New SSH Connection", self.app.new_session),
            ("🔌  New Serial Connection", self.app.new_serial),
            ("📂  Recover Sessions", self.app.recover_sessions),
        ]

        for text, cmd in btn_data:
            btn = ttk.Button(actions, text=text, command=cmd)
            btn.pack(side=tk.LEFT, padx=6, pady=4)

        # Search bar
        search_frame = ttk.Frame(container)
        search_frame.pack(fill=tk.X, padx=40, pady=16)

        self.search_var = tk.StringVar()
        search = ttk.Entry(search_frame, textvariable=self.search_var,
                           font=("Segoe UI", 12))
        search.pack(fill=tk.X, ipady=6)
        search.insert(0, "🔍  Find existing session or server name...")
        search.bind("<FocusIn>", self._clear_search)
        search.bind("<FocusOut>", self._restore_search)
        search.bind("<Return>", self._do_search)

        # Recent sessions section
        ttk.Label(container, text="Recent Sessions",
                  font=("Segoe UI", 12, "bold")).pack(pady=(20, 8), anchor=tk.W)

        self.recent_frame = ttk.Frame(container)
        self.recent_frame.pack(fill=tk.X, padx=10)

        self._show_no_recent()

        # Tools quick-launch row
        ttk.Label(container, text="Quick Launch Tools",
                  font=("Segoe UI", 12, "bold")).pack(pady=(24, 8), anchor=tk.W)

        tools_frame = ttk.Frame(container)
        tools_frame.pack(fill=tk.X, padx=10)

        tool_items = [
            ("🧮", "eCal", "open_ecal"),
            ("⏱", "eTimer", "open_etimer"),
            ("📝", "eNote", "open_enote"),
            ("🔢", "eViewer", "open_eviewer"),
            ("🛡", "eGuard", "open_eguard"),
            ("🔄", "eConverter", "open_econverter"),
            ("🚇", "eTunnel", "open_etunnel"),
            ("🛡", "eVirusTower", "open_evirustower"),
            ("🎨", "ePaint", "open_epaint"),
            ("🐍", "Snake", "open_snake"),
            ("🕐", "eClock", "open_eclock"),
        ]

        for icon, label, cmd_name in tool_items:
            btn = ttk.Button(
                tools_frame,
                text=f"{icon} {label}",
                style="Toolbar.TButton",
                command=lambda c=cmd_name: self._dispatch_tool(c),
            )
            btn.pack(side=tk.LEFT, padx=4, pady=4)

    def _show_no_recent(self):
        for w in self.recent_frame.winfo_children():
            w.destroy()
        ttk.Label(self.recent_frame, text="No recent sessions",
                  foreground="#888888",
                  font=("Segoe UI", 10, "italic")).pack(pady=8)

    def load_recent_sessions(self, sessions: list):
        for w in self.recent_frame.winfo_children():
            w.destroy()

        if not sessions:
            self._show_no_recent()
            return

        for sess in sessions[:8]:
            name = sess.get("name", "Unnamed")
            stype = sess.get("type", "ssh")
            icon = "🔐" if stype == "ssh" else "🔌" if stype == "serial" else "💻"
            btn = ttk.Button(
                self.recent_frame,
                text=f"{icon} {name}",
                style="Toolbar.TButton",
                command=lambda s=sess: self.app.connect_session(
                    s.get("connection", ""), s.get("name", "")),
            )
            btn.pack(side=tk.LEFT, padx=4, pady=4)

    def _clear_search(self, _event):
        if "Find existing" in self.search_var.get():
            self.search_var.set("")

    def _restore_search(self, _event):
        if not self.search_var.get().strip():
            self.search_var.set("🔍  Find existing session or server name...")

    def _do_search(self, _event):
        query = self.search_var.get().strip()
        if query and "Find existing" not in query:
            self.app.search_sessions(query)

    def _dispatch_tool(self, cmd_name: str):
        handler = getattr(self.app, cmd_name, None)
        if handler:
            handler()
