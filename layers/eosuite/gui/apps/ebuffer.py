# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eBuffer — Clipboard manager with slot list and copy/paste buttons.
"""
import tkinter as tk
from tkinter import ttk, messagebox


class EBuffer(ttk.Frame):
    MAX_SLOTS = 20

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._slots = []
        c = self.app.theme.colors

        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(fill=tk.X)
        ttk.Label(toolbar, text="📋 eBuffer — Clipboard Manager", style="Toolbar.TLabel",
                  font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=8, pady=4)
        ttk.Button(toolbar, text="Clear All", style="Toolbar.TButton", command=self._clear_all).pack(side=tk.RIGHT, padx=4, pady=2)
        ttk.Button(toolbar, text="📥 Capture", style="Toolbar.TButton", command=self._capture).pack(side=tk.RIGHT, padx=4, pady=2)

        self.slot_frame = ttk.Frame(self)
        self.slot_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._canvas = tk.Canvas(self.slot_frame, bg=c["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.slot_frame, orient=tk.VERTICAL, command=self._canvas.yview)
        self.inner_frame = ttk.Frame(self._canvas)
        self.inner_frame.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        preview_frame = ttk.Frame(self)
        preview_frame.pack(fill=tk.X, padx=4, pady=4)
        ttk.Label(preview_frame, text="Preview:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.preview_text = tk.Text(preview_frame, height=4, font=("Consolas", 10), bg=c["input_bg"],
                                    fg=c["input_fg"], state=tk.DISABLED, relief=tk.FLAT, borderwidth=4)
        self.preview_text.pack(fill=tk.X)

        self._refresh_slots()
        self._poll_clipboard()

    def _capture(self):
        try:
            content = self.clipboard_get()
            if content and (not self._slots or content != self._slots[0]):
                self._slots.insert(0, content)
                if len(self._slots) > self.MAX_SLOTS:
                    self._slots.pop()
                self._refresh_slots()
        except tk.TclError:
            pass

    def _poll_clipboard(self):
        self._capture()
        self.after(2000, self._poll_clipboard)

    def _refresh_slots(self):
        for w in self.inner_frame.winfo_children():
            w.destroy()
        if not self._slots:
            ttk.Label(self.inner_frame, text="No clipboard items yet.", foreground="#888888",
                      font=("Segoe UI", 10, "italic")).pack(pady=20)
            return
        for i, content in enumerate(self._slots):
            preview = content[:80].replace("\n", " ⏎ ")
            row = ttk.Frame(self.inner_frame)
            row.pack(fill=tk.X, padx=4, pady=2)
            ttk.Label(row, text=f"#{i+1}", width=4, font=("Consolas", 10, "bold")).pack(side=tk.LEFT)
            ttk.Label(row, text=preview, font=("Segoe UI", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            ttk.Button(row, text="📋", width=3, style="Toolbar.TButton",
                       command=lambda c=content: self._copy_slot(c)).pack(side=tk.RIGHT, padx=2)
            ttk.Button(row, text="👁", width=3, style="Toolbar.TButton",
                       command=lambda c=content: self._preview_slot(c)).pack(side=tk.RIGHT, padx=2)
            ttk.Button(row, text="✕", width=3, style="Toolbar.TButton",
                       command=lambda idx=i: self._delete_slot(idx)).pack(side=tk.RIGHT, padx=2)

    def _copy_slot(self, content):
        self.clipboard_clear()
        self.clipboard_append(content)

    def _preview_slot(self, content):
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", content)
        self.preview_text.config(state=tk.DISABLED)

    def _delete_slot(self, idx):
        if 0 <= idx < len(self._slots):
            self._slots.pop(idx)
            self._refresh_slots()

    def _clear_all(self):
        if messagebox.askyesno("Clear All", "Clear all clipboard slots?"):
            self._slots.clear()
            self._refresh_slots()
"""
EoSuite eBuffer — Clipboard manager with slot list and copy/paste buttons.
"""
import tkinter as tk
from tkinter import ttk, messagebox


class EBuffer(ttk.Frame):
    """Clipboard manager with multiple slots."""

    MAX_SLOTS = 20

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._slots = []
        self._build()
        self._poll_clipboard()

    def _build(self):
        c = self.app.theme.colors

        # Toolbar
        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="📋 eBuffer — Clipboard Manager",
                  style="Toolbar.TLabel",
                  font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=8, pady=4)

        ttk.Button(toolbar, text="Clear All", style="Toolbar.TButton",
                   command=self._clear_all).pack(side=tk.RIGHT, padx=4, pady=2)
        ttk.Button(toolbar, text="📥 Capture Now", style="Toolbar.TButton",
                   command=self._capture).pack(side=tk.RIGHT, padx=4, pady=2)

        # Slot list
        self.slot_frame = ttk.Frame(self)
        self.slot_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Scrollable area
        canvas = tk.Canvas(self.slot_frame, bg=c["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.slot_frame, orient=tk.VERTICAL,
                                  command=canvas.yview)
        self.inner_frame = ttk.Frame(canvas)

        self.inner_frame.bind("<Configure>",
                              lambda e: canvas.configure(
                                  scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Preview area
        preview_frame = ttk.Frame(self)
        preview_frame.pack(fill=tk.X, padx=4, pady=4)

        ttk.Label(preview_frame, text="Preview:",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.preview_text = tk.Text(
            preview_frame, height=4, font=("Consolas", 10),
            bg=c["input_bg"], fg=c["input_fg"],
            state=tk.DISABLED, relief=tk.FLAT, borderwidth=4)
        self.preview_text.pack(fill=tk.X)

        self._refresh_slots()

    def _capture(self):
        try:
            content = self.clipboard_get()
            if content and (not self._slots or content != self._slots[0]):
                self._slots.insert(0, content)
                if len(self._slots) > self.MAX_SLOTS:
                    self._slots.pop()
                self._refresh_slots()
        except tk.TclError:
            pass

    def _poll_clipboard(self):
        self._capture()
        self.after(2000, self._poll_clipboard)

    def _refresh_slots(self):
        for w in self.inner_frame.winfo_children():
            w.destroy()

        if not self._slots:
            ttk.Label(self.inner_frame,
                      text="No clipboard items yet. Copy something!",
                      foreground="#888888",
                      font=("Segoe UI", 10, "italic")).pack(pady=20)
            return

        for i, content in enumerate(self._slots):
            preview = content[:80].replace("\n", " ⏎ ")
            row = ttk.Frame(self.inner_frame)
            row.pack(fill=tk.X, padx=4, pady=2)

            ttk.Label(row, text=f"#{i+1}", width=4,
                      font=("Consolas", 10, "bold")).pack(side=tk.LEFT)
            ttk.Label(row, text=preview,
                      font=("Segoe UI", 10)).pack(
                side=tk.LEFT, fill=tk.X, expand=True, padx=4)

            ttk.Button(row, text="📋", width=3,
                       style="Toolbar.TButton",
                       command=lambda c=content: self._copy_slot(c)).pack(
                side=tk.RIGHT, padx=2)
            ttk.Button(row, text="👁", width=3,
                       style="Toolbar.TButton",
                       command=lambda c=content: self._preview_slot(c)).pack(
                side=tk.RIGHT, padx=2)
            ttk.Button(row, text="✕", width=3,
                       style="Toolbar.TButton",
                       command=lambda idx=i: self._delete_slot(idx)).pack(
                side=tk.RIGHT, padx=2)

    def _copy_slot(self, content: str):
        self.clipboard_clear()
        self.clipboard_append(content)
        self.app.set_status("Copied to clipboard")

    def _preview_slot(self, content: str):
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", content)
        self.preview_text.config(state=tk.DISABLED)

    def _delete_slot(self, idx: int):
        if 0 <= idx < len(self._slots):
            self._slots.pop(idx)
            self._refresh_slots()

    def _clear_all(self):
        if messagebox.askyesno("Clear All", "Clear all clipboard slots?"):
            self._slots.clear()
            self._refresh_slots()
