# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eNote — Text editor with open/save/find/replace/word count.
"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext


class ENote(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._filepath = None
        self._build()

    def _build(self):
        c = self.app.theme.colors
        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(fill=tk.X)
        for text, cmd in [("📄 New", self._new), ("📂 Open", self._open),
                          ("💾 Save", self._save), ("💾 Save As", self._save_as),
                          ("🔍 Find", self._find), ("🔄 Replace", self._replace),
                          ("📊 Word Count", self._word_count)]:
            ttk.Button(toolbar, text=text, style="Toolbar.TButton",
                       command=cmd).pack(side=tk.LEFT, padx=2, pady=2)
        self.file_label = ttk.Label(toolbar, text="  Untitled", style="Toolbar.TLabel")
        self.file_label.pack(side=tk.RIGHT, padx=8)

        self.text = scrolledtext.ScrolledText(
            self, font=("Consolas", 12), bg=c["input_bg"], fg=c["input_fg"],
            insertbackground=c["input_fg"], wrap=tk.WORD, undo=True,
            relief=tk.FLAT, borderwidth=4, padx=8, pady=4)
        self.text.pack(fill=tk.BOTH, expand=True)

        self.status = ttk.Label(self, text="Ln 1, Col 1  |  0 chars")
        self.status.pack(fill=tk.X, side=tk.BOTTOM)
        self.text.bind("<KeyRelease>", self._update_status)

    def _update_status(self, _event=None):
        pos = self.text.index(tk.INSERT)
        line, col = pos.split(".")
        chars = len(self.text.get("1.0", tk.END)) - 1
        self.status.config(text="Ln %s, Col %d  |  %d chars" % (line, int(col)+1, chars))

    def _new(self):
        self.text.delete("1.0", tk.END)
        self._filepath = None
        self.file_label.config(text="  Untitled")

    def _open(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self.text.delete("1.0", tk.END)
                self.text.insert("1.0", f.read())
            self._filepath = path
            self.file_label.config(text="  " + os.path.basename(path))

    def _save(self):
        if self._filepath:
            with open(self._filepath, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", tk.END))
        else:
            self._save_as()

    def _save_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", tk.END))
            self._filepath = path
            self.file_label.config(text="  " + os.path.basename(path))

    def _find(self):
        dialog = tk.Toplevel(self)
        dialog.title("Find")
        dialog.geometry("300x80")
        dialog.transient(self)
        ttk.Label(dialog, text="Find:").pack(side=tk.LEFT, padx=4, pady=10)
        find_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=find_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=10)
        entry.focus_set()

        def search(_e=None):
            self.text.tag_remove("found", "1.0", tk.END)
            q = find_var.get()
            if not q:
                return
            idx = "1.0"
            while True:
                idx = self.text.search(q, idx, nocase=True, stopindex=tk.END)
                if not idx:
                    break
                end_idx = "%s+%dc" % (idx, len(q))
                self.text.tag_add("found", idx, end_idx)
                idx = end_idx
            self.text.tag_configure("found", background="#ffd700", foreground="#000000")

        ttk.Button(dialog, text="Find All", command=search).pack(side=tk.LEFT, padx=4)
        entry.bind("<Return>", search)

    def _replace(self):
        dialog = tk.Toplevel(self)
        dialog.title("Find & Replace")
        dialog.geometry("350x120")
        dialog.transient(self)
        ttk.Label(dialog, text="Find:").grid(row=0, column=0, padx=4, pady=4)
        find_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=find_var).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(dialog, text="Replace:").grid(row=1, column=0, padx=4, pady=4)
        repl_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=repl_var).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        dialog.grid_columnconfigure(1, weight=1)

        def do_replace():
            content = self.text.get("1.0", tk.END)
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", content.replace(find_var.get(), repl_var.get()))

        ttk.Button(dialog, text="Replace All", command=do_replace).grid(row=2, column=1, pady=8)

    def _word_count(self):
        content = self.text.get("1.0", tk.END).strip()
        words = len(content.split()) if content else 0
        lines = content.count("\n") + 1 if content else 0
        messagebox.showinfo("Word Count",
                            "Lines: %d\nWords: %d\nCharacters: %d" % (lines, words, len(content)))
"""
EoSuite eNote — Text editor with open/save/find/replace/word count.
"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext


class ENote(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._filepath = None
        self._build()

    def _build(self):
        c = self.app.theme.colors
        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(fill=tk.X)
        for text, cmd in [("📄 New", self._new), ("📂 Open", self._open),
                          ("💾 Save", self._save), ("💾 Save As", self._save_as),
                          ("🔍 Find", self._find), ("🔄 Replace", self._replace),
                          ("📊 Word Count", self._word_count)]:
            ttk.Button(toolbar, text=text, style="Toolbar.TButton",
                       command=cmd).pack(side=tk.LEFT, padx=2, pady=2)
        self.file_label = ttk.Label(toolbar, text="  Untitled", style="Toolbar.TLabel")
        self.file_label.pack(side=tk.RIGHT, padx=8)

        self.text = scrolledtext.ScrolledText(
            self, font=("Consolas", 12), bg=c["input_bg"], fg=c["input_fg"],
            insertbackground=c["input_fg"], wrap=tk.WORD, undo=True,
            relief=tk.FLAT, borderwidth=4, padx=8, pady=4)
        self.text.pack(fill=tk.BOTH, expand=True)

        self.status = ttk.Label(self, text="Ln 1, Col 1  |  0 chars")
        self.status.pack(fill=tk.X, side=tk.BOTTOM)
        self.text.bind("<KeyRelease>", self._update_status)

    def _update_status(self, _event=None):
        pos = self.text.index(tk.INSERT)
        line, col = pos.split(".")
        chars = len(self.text.get("1.0", tk.END)) - 1
        self.status.config(text=f"Ln {line}, Col {int(col)+1}  |  {chars} chars")

    def _new(self):
        self.text.delete("1.0", tk.END)
        self._filepath = None
        self.file_label.config(text="  Untitled")

    def _open(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self.text.delete("1.0", tk.END)
                self.text.insert("1.0", f.read())
            self._filepath = path
            self.file_label.config(text=f"  {os.path.basename(path)}")

    def _save(self):
        if self._filepath:
            with open(self._filepath, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", tk.END))
        else:
            self._save_as()

    def _save_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", tk.END))
            self._filepath = path
            self.file_label.config(text=f"  {os.path.basename(path)}")

    def _find(self):
        dialog = tk.Toplevel(self)
        dialog.title("Find")
        dialog.geometry("300x80")
        dialog.transient(self)
        ttk.Label(dialog, text="Find:").pack(side=tk.LEFT, padx=4, pady=10)
        find_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=find_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=10)
        entry.focus_set()

        def search(_e=None):
            self.text.tag_remove("found", "1.0", tk.END)
            q = find_var.get()
            if not q:
                return
            idx = "1.0"
            while True:
                idx = self.text.search(q, idx, nocase=True, stopindex=tk.END)
                if not idx:
                    break
                end = f"{idx}+{len(q)}c"
                self.text.tag_add("found", idx, end)
                idx = end
            self.text.tag_configure("found", background="#ffd700", foreground="#000000")

        ttk.Button(dialog, text="Find All", command=search).pack(side=tk.LEFT, padx=4)
        entry.bind("<Return>", search)

    def _replace(self):
        dialog = tk.Toplevel(self)
        dialog.title("Find & Replace")
        dialog.geometry("350x120")
        dialog.transient(self)
        ttk.Label(dialog, text="Find:").grid(row=0, column=0, padx=4, pady=4)
        find_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=find_var).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(dialog, text="Replace:").grid(row=1, column=0, padx=4, pady=4)
        repl_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=repl_var).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        dialog.grid_columnconfigure(1, weight=1)

        def do_replace():
            content = self.text.get("1.0", tk.END)
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", content.replace(find_var.get(), repl_var.get()))

        ttk.Button(dialog, text="Replace All", command=do_replace).grid(row=2, column=1, pady=8)

    def _word_count(self):
        content = self.text.get("1.0", tk.END).strip()
        words = len(content.split()) if content else 0
        messagebox.showinfo("Word Count",
                            f"Lines: {content.count(chr(10)) + 1 if content else 0}\n"
                            f"Words: {words}\nCharacters: {len(content)}")
