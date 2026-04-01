# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite ePDF — PDF viewer with text display and basic controls.
"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext


class EPdf(ttk.Frame):
    """PDF viewer with text extraction and basic operations."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._filepath = None
        self._pages = []
        self._current_page = 0
        self._build()

    def _build(self):
        c = self.app.theme.colors

        # Toolbar
        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(fill=tk.X)

        btns = [
            ("📂 Open PDF", self._open),
            ("◀ Prev", self._prev_page),
            ("▶ Next", self._next_page),
            ("🔍 Find", self._find),
            ("💾 Save Text", self._save_text),
            ("📋 Merge", self._merge),
        ]
        for text, cmd in btns:
            ttk.Button(toolbar, text=text, style="Toolbar.TButton",
                       command=cmd).pack(side=tk.LEFT, padx=2, pady=2)

        self.page_label = ttk.Label(toolbar, text="No file",
                                    style="Toolbar.TLabel")
        self.page_label.pack(side=tk.RIGHT, padx=8)

        self.file_label = ttk.Label(toolbar, text="",
                                    style="Toolbar.TLabel")
        self.file_label.pack(side=tk.RIGHT, padx=8)

        # Text display
        self.text_view = scrolledtext.ScrolledText(
            self, font=("Consolas", 11),
            bg=c["input_bg"], fg=c["input_fg"],
            insertbackground=c["input_fg"],
            wrap=tk.WORD, state=tk.DISABLED,
            relief=tk.FLAT, borderwidth=4, padx=8, pady=4)
        self.text_view.pack(fill=tk.BOTH, expand=True)

    def _open(self):
        path = filedialog.askopenfilename(
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not path:
            return

        self._filepath = path
        self.file_label.config(text=os.path.basename(path))

        # Try to extract text from PDF
        text = self._extract_text(path)
        if text:
            # Split into pages (simple heuristic: form feeds or page markers)
            self._pages = text.split("\f") if "\f" in text else [text]
            self._current_page = 0
            self._show_page()
        else:
            self.text_view.config(state=tk.NORMAL)
            self.text_view.delete("1.0", tk.END)
            self.text_view.insert("1.0",
                                  "Could not extract text from PDF.\n\n"
                                  "ePDF uses a built-in text extractor that works\n"
                                  "with simple PDF files. For complex PDFs, install\n"
                                  "the 'pypdf' package: pip install pypdf\n\n"
                                  f"File: {path}\n"
                                  f"Size: {os.path.getsize(path):,} bytes")
            self.text_view.config(state=tk.DISABLED)

    def _extract_text(self, path: str) -> str:
        # Try pypdf first (if available)
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\f".join(pages) if pages else ""
        except ImportError:
            pass
        except Exception:
            pass

        # Try PyMuPDF / fitz
        try:
            import fitz
            doc = fitz.open(path)
            pages = []
            for page in doc:
                text = page.get_text()
                if text.strip():
                    pages.append(text)
            doc.close()
            return "\f".join(pages) if pages else ""
        except ImportError:
            pass
        except Exception:
            pass

        # Try system pdftotext command
        try:
            import subprocess
            result = subprocess.run(
                ["pdftotext", "-layout", path, "-"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass

        # Try system mutool command
        try:
            import subprocess
            result = subprocess.run(
                ["mutool", "draw", "-F", "text", path],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass

        # Last resort: extract only readable text runs (skip PDF structure)
        try:
            with open(path, "rb") as f:
                data = f.read()

            import re
            text_parts = []

            # Find text between BT...ET (text objects in PDF)
            bt_et = re.findall(rb'BT\s*(.*?)\s*ET', data, re.DOTALL)
            for block in bt_et:
                # Extract strings inside parentheses: (text here)
                strings = re.findall(rb'\(([^)]*)\)', block)
                for s in strings:
                    try:
                        decoded = s.decode('latin-1', errors='ignore')
                        cleaned = decoded.strip()
                        if len(cleaned) > 1 and not all(c in '\\/<>[]{}' for c in cleaned):
                            text_parts.append(cleaned)
                    except Exception:
                        pass

                # Extract hex strings: <hex>
                hex_strings = re.findall(rb'<([0-9a-fA-F]+)>', block)
                for h in hex_strings:
                    try:
                        decoded = bytes.fromhex(h.decode()).decode('utf-16-be', errors='ignore')
                        cleaned = decoded.strip()
                        if len(cleaned) > 1:
                            text_parts.append(cleaned)
                    except Exception:
                        pass

            if text_parts:
                return " ".join(text_parts)

            # If no BT/ET blocks found, return empty (don't dump raw binary)
            return ""
        except Exception:
            return ""

    def _show_page(self):
        if not self._pages:
            return
        self.text_view.config(state=tk.NORMAL)
        self.text_view.delete("1.0", tk.END)
        self.text_view.insert("1.0", self._pages[self._current_page])
        self.text_view.config(state=tk.DISABLED)
        self.page_label.config(
            text=f"Page {self._current_page + 1}/{len(self._pages)}")

    def _prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._show_page()

    def _next_page(self):
        if self._current_page < len(self._pages) - 1:
            self._current_page += 1
            self._show_page()

    def _find(self):
        dialog = tk.Toplevel(self)
        dialog.title("Find in PDF")
        dialog.geometry("300x80")
        dialog.transient(self)

        ttk.Label(dialog, text="Find:").pack(side=tk.LEFT, padx=4, pady=10)
        find_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=find_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=10)
        entry.focus_set()

        def search(_event=None):
            self.text_view.tag_remove("found", "1.0", tk.END)
            query = find_var.get()
            if not query:
                return
            idx = "1.0"
            while True:
                idx = self.text_view.search(query, idx, nocase=True,
                                            stopindex=tk.END)
                if not idx:
                    break
                end = f"{idx}+{len(query)}c"
                self.text_view.tag_add("found", idx, end)
                idx = end
            self.text_view.tag_configure("found", background="#ffd700",
                                        foreground="#000000")

        ttk.Button(dialog, text="Find", command=search).pack(
            side=tk.LEFT, padx=4)
        entry.bind("<Return>", search)

    def _save_text(self):
        if not self._pages:
            messagebox.showinfo("Info", "No PDF loaded.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(self._pages))
            self.app.set_status(f"Text saved: {path}")

    def _merge(self):
        messagebox.showinfo(
            "Merge PDFs",
            "PDF merging requires the 'pypdf' package.\n\n"
            "Install with: pip install pypdf\n\n"
            "Once installed, select multiple PDF files to merge.")
