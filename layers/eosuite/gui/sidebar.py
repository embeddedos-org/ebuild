# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Sidebar — Collapsible session tree with saved connections.
"""
import tkinter as tk
from tkinter import ttk


class Sidebar(ttk.Frame):
    """Left sidebar with collapsible session tree."""

    def __init__(self, parent, app):
        super().__init__(parent, style="Sidebar.TFrame", width=220)
        self.app = app
        self._visible = True
        self._build()

    def _build(self):
        header = ttk.Frame(self, style="Sidebar.TFrame")
        header.pack(fill=tk.X, padx=4, pady=(6, 2))
        ttk.Label(header, text="📁 Sessions", style="Sidebar.TLabel",
                  font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=4)
        ttk.Button(header, text="＋", style="Sidebar.TButton", width=3,
                   command=self._add_session).pack(side=tk.RIGHT)

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(self, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, padx=6, pady=4)
        search_entry.insert(0, "Filter sessions...")
        search_entry.bind("<FocusIn>", self._clear_placeholder)
        search_entry.bind("<FocusOut>", self._restore_placeholder)
        self.search_var.trace_add("write", self._on_filter)

        self.tree = ttk.Treeview(self, show="tree", selectmode="browse")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.cat_ssh = self.tree.insert("", tk.END, text="🔐 SSH Sessions", open=True)
        self.cat_serial = self.tree.insert("", tk.END, text="🔌 Serial Connections", open=True)
        self.cat_local = self.tree.insert("", tk.END, text="💻 Local Terminals", open=True)

        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>", self._on_double_click)

    def _clear_placeholder(self, _event):
        if self.search_var.get() == "Filter sessions...":
            self.search_var.set("")

    def _restore_placeholder(self, _event):
        if not self.search_var.get().strip():
            self.search_var.set("Filter sessions...")

    def _on_filter(self, *_args):
        query = self.search_var.get().lower()
        if query == "filter sessions...":
            return
        for cat in (self.cat_ssh, self.cat_serial, self.cat_local):
            for child in self.tree.get_children(cat):
                text = self.tree.item(child, "text").lower()
                if query and query not in text:
                    self.tree.detach(child)
                else:
                    try:
                        self.tree.move(child, cat, tk.END)
                    except tk.TclError:
                        pass

    def _on_double_click(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        if item in (self.cat_ssh, self.cat_serial, self.cat_local):
            return
        values = self.tree.item(item, "values")
        text = self.tree.item(item, "text")
        if values:
            self.app.connect_session(values[0], text)

    def _add_session(self):
        self.app.new_session()

    def add_ssh_session(self, name, connection_str):
        self.tree.insert(self.cat_ssh, tk.END, text=f"🔐 {name}", values=(connection_str,))

    def add_serial_session(self, name, connection_str):
        self.tree.insert(self.cat_serial, tk.END, text=f"🔌 {name}", values=(connection_str,))

    def add_local_session(self, name, connection_str="local"):
        self.tree.insert(self.cat_local, tk.END, text=f"💻 {name}", values=(connection_str,))

    def clear_sessions(self):
        for cat in (self.cat_ssh, self.cat_serial, self.cat_local):
            for child in self.tree.get_children(cat):
                self.tree.delete(child)

    def toggle(self):
        self._visible = not self._visible
        if self._visible:
            self.pack(side=tk.LEFT, fill=tk.Y)
        else:
            self.pack_forget()
