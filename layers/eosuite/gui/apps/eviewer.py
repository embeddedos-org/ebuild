# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eViewer — Color-coded hex viewer with offset navigation.
"""
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext


class EViewer(ttk.Frame):
    BYTES_PER_ROW = 16

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._data = b""
        self._build()

    def _build(self):
        c = self.app.theme.colors

        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="📂 Open File", style="Toolbar.TButton",
                   command=self._open_file).pack(side=tk.LEFT, padx=4, pady=2)
        self.info_label = ttk.Label(toolbar, text="No file loaded", style="Toolbar.TLabel")
        self.info_label.pack(side=tk.LEFT, padx=8)

        ttk.Label(toolbar, text="Go to offset:", style="Toolbar.TLabel").pack(side=tk.RIGHT, padx=(0, 4))
        self.goto_var = tk.StringVar()
        goto_entry = ttk.Entry(toolbar, textvariable=self.goto_var, width=10)
        goto_entry.pack(side=tk.RIGHT, padx=4)
        goto_entry.bind("<Return>", self._goto_offset)

        self.hex_view = scrolledtext.ScrolledText(
            self, font=("Consolas", 11), bg=c["terminal_bg"], fg=c["terminal_fg"],
            insertbackground=c["terminal_fg"], wrap=tk.NONE, state=tk.DISABLED,
            relief=tk.FLAT, borderwidth=0, padx=4, pady=4)
        self.hex_view.pack(fill=tk.BOTH, expand=True)

        self.hex_view.tag_configure("offset", foreground="#569cd6")
        self.hex_view.tag_configure("null", foreground="#555555")
        self.hex_view.tag_configure("printable", foreground="#4ec9b0")
        self.hex_view.tag_configure("high", foreground="#ce9178")
        self.hex_view.tag_configure("control", foreground="#d16969")
        self.hex_view.tag_configure("ascii", foreground="#dcdcaa")
        self.hex_view.tag_configure("separator", foreground="#444444")

    def _open_file(self):
        path = filedialog.askopenfilename(filetypes=[("All files", "*.*"), ("Binary files", "*.bin")])
        if path:
            try:
                with open(path, "rb") as f:
                    self._data = f.read()
                self.info_label.config(text=f"{path}  ({len(self._data):,} bytes)")
                self._render()
            except Exception as e:
                self.info_label.config(text=f"Error: {e}")

    def _render(self):
        self.hex_view.config(state=tk.NORMAL)
        self.hex_view.delete("1.0", tk.END)

        for offset in range(0, len(self._data), self.BYTES_PER_ROW):
            chunk = self._data[offset:offset + self.BYTES_PER_ROW]
            self.hex_view.insert(tk.END, f"{offset:08X}  ", "offset")

            for i, byte in enumerate(chunk):
                hex_str = f"{byte:02X} "
                if byte == 0:
                    tag = "null"
                elif 0x20 <= byte <= 0x7E:
                    tag = "printable"
                elif byte > 0x7F:
                    tag = "high"
                else:
                    tag = "control"
                self.hex_view.insert(tk.END, hex_str, tag)
                if i == 7:
                    self.hex_view.insert(tk.END, " ", "separator")

            remaining = self.BYTES_PER_ROW - len(chunk)
            if remaining > 0:
                pad = "   " * remaining
                if len(chunk) <= 8:
                    pad += " "
                self.hex_view.insert(tk.END, pad)

            self.hex_view.insert(tk.END, " │ ", "separator")
            ascii_str = "".join(chr(b) if 0x20 <= b <= 0x7E else "." for b in chunk)
            self.hex_view.insert(tk.END, ascii_str + "\n", "ascii")

        self.hex_view.config(state=tk.DISABLED)

    def _goto_offset(self, _event=None):
        try:
            offset = int(self.goto_var.get(), 16)
            line = offset // self.BYTES_PER_ROW + 1
            self.hex_view.see(f"{line}.0")
        except ValueError:
            pass
