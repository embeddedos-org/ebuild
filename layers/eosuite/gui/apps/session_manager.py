# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Session Manager — Save/load sessions from JSON config.
"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".eosuite")
SESSIONS_FILE = os.path.join(CONFIG_DIR, "sessions.json")


class SessionManager:
    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)

    def load_sessions(self):
        if not os.path.exists(SESSIONS_FILE):
            return []
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            return []

    def save_sessions(self, sessions):
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2)

    def add_session(self, name, stype, connection):
        sessions = self.load_sessions()
        sessions.append({"name": name, "type": stype, "connection": connection})
        self.save_sessions(sessions)

    def remove_session(self, name):
        sessions = [s for s in self.load_sessions() if s.get("name") != name]
        self.save_sessions(sessions)

    def search(self, query):
        q = query.lower()
        return [s for s in self.load_sessions()
                if q in s.get("name", "").lower() or q in s.get("connection", "").lower()]


class SessionManagerDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.mgr = SessionManager()
        self.title("Manage Sessions")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()
        self.configure(bg=app.theme.colors["bg"])

        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main, text="📁 Saved Sessions", font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        cols = ("Name", "Type", "Connection")
        self.tree = ttk.Treeview(main, columns=cols, show="headings", selectmode="browse")
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=4)

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_frame, text="Connect", command=self._connect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=4)
        self._refresh()

    def _refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for s in self.mgr.load_sessions():
            self.tree.insert("", tk.END, values=(s.get("name", ""), s.get("type", ""), s.get("connection", "")))

    def _connect(self):
        sel = self.tree.selection()
        if sel:
            values = self.tree.item(sel[0], "values")
            self.app.connect_session(values[2], values[0])
            self.destroy()

    def _delete(self):
        sel = self.tree.selection()
        if sel:
            values = self.tree.item(sel[0], "values")
            if messagebox.askyesno("Delete", f"Delete session '{values[0]}'?"):
                self.mgr.remove_session(values[0])
                self._refresh()
"""
EoSuite Session Manager — Save/load sessions from JSON config.
"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".eosuite")
SESSIONS_FILE = os.path.join(CONFIG_DIR, "sessions.json")


class SessionManager:
    """Handles session persistence to JSON file."""

    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)

    def load_sessions(self) -> list:
        if not os.path.exists(SESSIONS_FILE):
            return []
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            return []

    def save_sessions(self, sessions: list):
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2)

    def add_session(self, name: str, stype: str, connection: str):
        sessions = self.load_sessions()
        sessions.append({
            "name": name,
            "type": stype,
            "connection": connection,
        })
        self.save_sessions(sessions)

    def remove_session(self, name: str):
        sessions = self.load_sessions()
        sessions = [s for s in sessions if s.get("name") != name]
        self.save_sessions(sessions)

    def search(self, query: str) -> list:
        sessions = self.load_sessions()
        q = query.lower()
        return [s for s in sessions
                if q in s.get("name", "").lower()
                or q in s.get("connection", "").lower()]


class SessionManagerDialog(tk.Toplevel):
    """Dialog for managing saved sessions."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.mgr = SessionManager()
        self.title("Manage Sessions")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()
        self._build()
        self._refresh()

    def _build(self):
        c = self.app.theme.colors
        self.configure(bg=c["bg"])

        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="📁 Saved Sessions",
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        # Session list
        cols = ("Name", "Type", "Connection")
        self.tree = ttk.Treeview(main, columns=cols, show="headings",
                                 selectmode="browse")
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=4)

        scrollbar = ttk.Scrollbar(main, orient=tk.VERTICAL,
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(btn_frame, text="Connect",
                   command=self._connect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Delete",
                   command=self._delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Close",
                   command=self.destroy).pack(side=tk.RIGHT, padx=4)

    def _refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for s in self.mgr.load_sessions():
            self.tree.insert("", tk.END, values=(
                s.get("name", ""), s.get("type", ""), s.get("connection", "")))

    def _connect(self):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        self.app.connect_session(values[2], values[0])
        self.destroy()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if messagebox.askyesno("Delete", f"Delete session '{values[0]}'?"):
            self.mgr.remove_session(values[0])
            self._refresh()
