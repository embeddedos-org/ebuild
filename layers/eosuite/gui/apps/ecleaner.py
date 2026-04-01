# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eCleaner — Cleanup tool with checkboxes and scan/clean buttons.
"""
import os
import sys
import tempfile
import shutil
import tkinter as tk
from tkinter import ttk, messagebox


class ECleaner(ttk.Frame):
    CATEGORIES = [
        ("🗑 Temporary Files", "temp_files", "System and user temp directories"),
        ("📦 Python Cache", "python_cache", "__pycache__ directories in current project"),
        ("📊 Log Files", "log_files", "*.log files in common locations"),
        ("📋 Clipboard History", "clipboard", "Clear clipboard data"),
        ("🌐 Browser Cache", "browser_cache", "Cached browser data"),
        ("🗂 Empty Recycle Bin", "recycle_bin", "Clear deleted files"),
    ]

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._scan_results = {}
        c = self.app.theme.colors

        container = ttk.Frame(self, padding=20)
        container.pack(fill=tk.BOTH, expand=True)
        ttk.Label(container, text="🧹 eCleaner", font=("Segoe UI", 18, "bold")).pack(pady=(0, 4))
        ttk.Label(container, text="Free up disk space by removing junk files", font=("Segoe UI", 11)).pack(pady=(0, 16))

        self._checks = {}
        checks_frame = ttk.Frame(container)
        checks_frame.pack(fill=tk.X, padx=20)
        for label, key, desc in self.CATEGORIES:
            var = tk.BooleanVar(value=True)
            self._checks[key] = var
            row = ttk.Frame(checks_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Checkbutton(row, text=label, variable=var).pack(side=tk.LEFT)
            ttk.Label(row, text=f"  — {desc}", foreground="#888888", font=("Segoe UI", 9)).pack(side=tk.LEFT)

        self.results_text = tk.Text(container, height=8, font=("Consolas", 10), bg=c["terminal_bg"],
                                    fg=c["terminal_fg"], state=tk.DISABLED, relief=tk.FLAT, borderwidth=4)
        self.results_text.pack(fill=tk.X, padx=20, pady=16)

        btn_frame = ttk.Frame(container)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="🔍 Scan", command=self._scan).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="🧹 Clean", command=self._clean).pack(side=tk.LEFT, padx=6)

        self.total_label = ttk.Label(container, text="Select categories and click Scan", font=("Segoe UI", 12))
        self.total_label.pack(pady=8)

    def _log(self, text):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.insert(tk.END, text + "\n")
        self.results_text.see(tk.END)
        self.results_text.config(state=tk.DISABLED)

    def _scan(self):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)
        self.results_text.config(state=tk.DISABLED)
        self._scan_results = {}
        total = 0
        if self._checks["temp_files"].get():
            size = self._scan_dir(tempfile.gettempdir())
            self._scan_results["temp_files"] = size
            total += size
            self._log(f"Temp files: {self._fmt(size)}")
        if self._checks["python_cache"].get():
            size = self._scan_pycache()
            self._scan_results["python_cache"] = size
            total += size
            self._log(f"Python cache: {self._fmt(size)}")
        if self._checks["log_files"].get():
            size = self._scan_logs()
            self._scan_results["log_files"] = size
            total += size
            self._log(f"Log files: {self._fmt(size)}")
        for key in ("clipboard", "browser_cache", "recycle_bin"):
            if self._checks[key].get():
                self._log(f"{key}: (not available on this platform)")
        self.total_label.config(text=f"Total reclaimable: {self._fmt(total)}")

    def _clean(self):
        if not self._scan_results:
            messagebox.showinfo("Info", "Run a scan first.")
            return
        if not messagebox.askyesno("Confirm", "Delete selected items?"):
            return
        cleaned = 0
        if self._scan_results.get("temp_files"):
            cleaned += self._clean_dir(tempfile.gettempdir())
            self._log("Cleaned temp files ✓")
        if self._scan_results.get("python_cache"):
            cleaned += self._clean_pycache()
            self._log("Cleaned Python cache ✓")
        self.total_label.config(text=f"Cleaned: {self._fmt(cleaned)}")

    def _scan_dir(self, path):
        total = 0
        try:
            for root, _, files in os.walk(path):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
        except OSError:
            pass
        return total

    def _clean_dir(self, path):
        cleaned = 0
        try:
            for item in os.listdir(path):
                fp = os.path.join(path, item)
                try:
                    if os.path.isfile(fp):
                        cleaned += os.path.getsize(fp)
                        os.remove(fp)
                    elif os.path.isdir(fp):
                        cleaned += self._scan_dir(fp)
                        shutil.rmtree(fp, ignore_errors=True)
                except OSError:
                    pass
        except OSError:
            pass
        return cleaned

    def _scan_pycache(self):
        total = 0
        start = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for root, dirs, _ in os.walk(start):
            if "__pycache__" in dirs:
                total += self._scan_dir(os.path.join(root, "__pycache__"))
        return total

    def _clean_pycache(self):
        cleaned = 0
        start = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for root, dirs, _ in os.walk(start):
            if "__pycache__" in dirs:
                d = os.path.join(root, "__pycache__")
                cleaned += self._scan_dir(d)
                shutil.rmtree(d, ignore_errors=True)
        return cleaned

    def _scan_logs(self):
        total = 0
        for d in [tempfile.gettempdir()]:
            try:
                for f in os.listdir(d):
                    if f.endswith(".log"):
                        try:
                            total += os.path.getsize(os.path.join(d, f))
                        except OSError:
                            pass
            except OSError:
                pass
        return total

    @staticmethod
    def _fmt(size):
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
"""
EoSuite eCleaner — Cleanup tool with checkboxes and scan/clean buttons.
"""
import os
import sys
import tempfile
import shutil
import tkinter as tk
from tkinter import ttk, messagebox


class ECleaner(ttk.Frame):
    """System cleanup tool with scan and clean functionality."""

    CATEGORIES = [
        ("🗑 Temporary Files", "temp_files",
         "System and user temp directories"),
        ("📋 Clipboard History", "clipboard",
         "Clear clipboard data"),
        ("🌐 Browser Cache", "browser_cache",
         "Cached browser data (common locations)"),
        ("📝 Recent Documents", "recent_docs",
         "Recent document history"),
        ("🗂 Empty Recycle Bin", "recycle_bin",
         "Clear deleted files"),
        ("📦 Python Cache", "python_cache",
         "__pycache__ directories in current project"),
        ("📊 Log Files", "log_files",
         "*.log files in common locations"),
    ]

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._scan_results = {}
        self._build()

    def _build(self):
        c = self.app.theme.colors

        container = ttk.Frame(self, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="🧹 eCleaner",
                  font=("Segoe UI", 18, "bold")).pack(pady=(0, 4))
        ttk.Label(container, text="Free up disk space by removing junk files",
                  font=("Segoe UI", 11)).pack(pady=(0, 16))

        # Checkboxes
        self._checks = {}
        checks_frame = ttk.Frame(container)
        checks_frame.pack(fill=tk.X, padx=20)

        for label, key, desc in self.CATEGORIES:
            var = tk.BooleanVar(value=True)
            self._checks[key] = var
            row = ttk.Frame(checks_frame)
            row.pack(fill=tk.X, pady=2)
            cb = ttk.Checkbutton(row, text=label, variable=var)
            cb.pack(side=tk.LEFT)
            ttk.Label(row, text=f"  — {desc}", foreground="#888888",
                      font=("Segoe UI", 9)).pack(side=tk.LEFT)

        # Scan results
        self.results_text = tk.Text(
            container, height=8, font=("Consolas", 10),
            bg=c["terminal_bg"], fg=c["terminal_fg"],
            state=tk.DISABLED, relief=tk.FLAT, borderwidth=4)
        self.results_text.pack(fill=tk.X, padx=20, pady=16)

        # Buttons
        btn_frame = ttk.Frame(container)
        btn_frame.pack(pady=8)

        ttk.Button(btn_frame, text="🔍 Scan",
                   command=self._scan).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="🧹 Clean",
                   command=self._clean).pack(side=tk.LEFT, padx=6)

        # Total label
        self.total_label = ttk.Label(
            container, text="Select categories and click Scan",
            font=("Segoe UI", 12))
        self.total_label.pack(pady=8)

    def _log(self, text: str):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.insert(tk.END, text + "\n")
        self.results_text.see(tk.END)
        self.results_text.config(state=tk.DISABLED)

    def _scan(self):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)
        self.results_text.config(state=tk.DISABLED)
        self._scan_results = {}
        total_size = 0

        if self._checks["temp_files"].get():
            size = self._scan_dir(tempfile.gettempdir())
            self._scan_results["temp_files"] = size
            total_size += size
            self._log(f"Temp files: {self._fmt_size(size)}")

        if self._checks["python_cache"].get():
            size = self._scan_pycache()
            self._scan_results["python_cache"] = size
            total_size += size
            self._log(f"Python cache: {self._fmt_size(size)}")

        if self._checks["log_files"].get():
            size = self._scan_logs()
            self._scan_results["log_files"] = size
            total_size += size
            self._log(f"Log files: {self._fmt_size(size)}")

        for key in ("clipboard", "browser_cache", "recent_docs", "recycle_bin"):
            if self._checks[key].get():
                self._log(f"{key}: (scan not available on this platform)")
                self._scan_results[key] = 0

        self.total_label.config(
            text=f"Total reclaimable: {self._fmt_size(total_size)}")
        self.app.set_status(f"eCleaner scan complete: {self._fmt_size(total_size)}")

    def _clean(self):
        if not self._scan_results:
            messagebox.showinfo("Info", "Run a scan first.")
            return

        if not messagebox.askyesno("Confirm", "Delete selected items?"):
            return

        cleaned = 0
        if self._checks["temp_files"].get() and self._scan_results.get("temp_files", 0):
            cleaned += self._clean_dir(tempfile.gettempdir())
            self._log("Cleaned temp files ✓")

        if self._checks["python_cache"].get() and self._scan_results.get("python_cache", 0):
            cleaned += self._clean_pycache()
            self._log("Cleaned Python cache ✓")

        if self._checks["log_files"].get() and self._scan_results.get("log_files", 0):
            cleaned += self._clean_logs()
            self._log("Cleaned log files ✓")

        self.total_label.config(
            text=f"Cleaned: {self._fmt_size(cleaned)}")
        self.app.set_status(f"eCleaner: Freed {self._fmt_size(cleaned)}")

    def _scan_dir(self, path: str) -> int:
        total = 0
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
        except OSError:
            pass
        return total

    def _clean_dir(self, path: str) -> int:
        cleaned = 0
        try:
            for item in os.listdir(path):
                fp = os.path.join(path, item)
                try:
                    if os.path.isfile(fp):
                        size = os.path.getsize(fp)
                        os.remove(fp)
                        cleaned += size
                    elif os.path.isdir(fp):
                        size = self._scan_dir(fp)
                        shutil.rmtree(fp, ignore_errors=True)
                        cleaned += size
                except OSError:
                    pass
        except OSError:
            pass
        return cleaned

    def _scan_pycache(self) -> int:
        total = 0
        start = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for root, dirs, files in os.walk(start):
            if "__pycache__" in dirs:
                cache_dir = os.path.join(root, "__pycache__")
                total += self._scan_dir(cache_dir)
        return total

    def _clean_pycache(self) -> int:
        cleaned = 0
        start = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for root, dirs, files in os.walk(start):
            if "__pycache__" in dirs:
                cache_dir = os.path.join(root, "__pycache__")
                cleaned += self._scan_dir(cache_dir)
                shutil.rmtree(cache_dir, ignore_errors=True)
        return cleaned

    def _scan_logs(self) -> int:
        total = 0
        search_dirs = [tempfile.gettempdir()]
        if sys.platform == "win32":
            search_dirs.append(os.path.expandvars(r"%LOCALAPPDATA%\Temp"))
        for d in search_dirs:
            try:
                for f in os.listdir(d):
                    if f.endswith(".log"):
                        try:
                            total += os.path.getsize(os.path.join(d, f))
                        except OSError:
                            pass
            except OSError:
                pass
        return total

    def _clean_logs(self) -> int:
        cleaned = 0
        search_dirs = [tempfile.gettempdir()]
        for d in search_dirs:
            try:
                for f in os.listdir(d):
                    if f.endswith(".log"):
                        fp = os.path.join(d, f)
                        try:
                            cleaned += os.path.getsize(fp)
                            os.remove(fp)
                        except OSError:
                            pass
            except OSError:
                pass
        return cleaned

    @staticmethod
    def _fmt_size(size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
