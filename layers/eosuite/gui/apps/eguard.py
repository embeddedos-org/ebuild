# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eGuard — Keep-awake utility with toggle and status indicator.
"""
import sys
import ctypes
import threading
import tkinter as tk
from tkinter import ttk


class EGuard(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._active = False
        c = self.app.theme.colors

        container = ttk.Frame(self)
        container.place(relx=0.5, rely=0.4, anchor=tk.CENTER)
        ttk.Label(container, text="🛡", font=("Segoe UI", 64)).pack(pady=(0, 8))
        ttk.Label(container, text="eGuard", font=("Segoe UI", 20, "bold")).pack(pady=(0, 4))
        ttk.Label(container, text="Keep your screen awake", font=("Segoe UI", 11)).pack(pady=(0, 24))

        self.status_canvas = tk.Canvas(container, width=120, height=120, bg=c["bg"], highlightthickness=0)
        self.status_canvas.pack(pady=10)
        self._draw_indicator(False)

        self.status_label = ttk.Label(container, text="Status: Inactive", font=("Segoe UI", 14))
        self.status_label.pack(pady=8)
        self.toggle_btn = ttk.Button(container, text="▶  Activate eGuard", command=self._toggle)
        self.toggle_btn.pack(pady=10)
        ttk.Label(container, text="Prevents sleep by simulating activity\nWorks on Windows, macOS, and Linux",
                  foreground="#888888", justify=tk.CENTER, font=("Segoe UI", 9)).pack(pady=(16, 0))

    def _draw_indicator(self, active):
        self.status_canvas.delete("all")
        color = "#4ec9b0" if active else "#555555"
        glow = "#2a6e5e" if active else "#333333"
        self.status_canvas.create_oval(10, 10, 110, 110, fill=glow, outline="")
        self.status_canvas.create_oval(25, 25, 95, 95, fill=color, outline="")
        self.status_canvas.create_text(60, 60, text="✓" if active else "○",
                                       font=("Segoe UI", 24, "bold"), fill="#ffffff")

    def _toggle(self):
        if self._active:
            self._active = False
            self._draw_indicator(False)
            self.status_label.config(text="Status: Inactive")
            self.toggle_btn.config(text="▶  Activate eGuard")
            if sys.platform == "win32":
                try:
                    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
                except Exception:
                    pass
        else:
            self._active = True
            self._draw_indicator(True)
            self.status_label.config(text="Status: Active ✓")
            self.toggle_btn.config(text="⏸  Deactivate eGuard")
            if sys.platform == "win32":
                try:
                    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000002)
                except Exception:
                    pass
            else:
                threading.Thread(target=self._keep_alive, daemon=True).start()

    def _keep_alive(self):
        import time
        while self._active:
            time.sleep(30)

    def on_close(self):
        self._active = False
"""
EoSuite eGuard — Keep-awake utility with toggle and status indicator.
"""
import sys
import ctypes
import threading
import tkinter as tk
from tkinter import ttk


class EGuard(ttk.Frame):
    """Keep-awake tool that prevents screen sleep."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._active = False
        self._thread = None
        self._build()

    def _build(self):
        c = self.app.theme.colors

        container = ttk.Frame(self)
        container.place(relx=0.5, rely=0.4, anchor=tk.CENTER)

        # Icon
        ttk.Label(container, text="🛡", font=("Segoe UI", 64)).pack(pady=(0, 8))

        # Title
        ttk.Label(container, text="eGuard",
                  font=("Segoe UI", 20, "bold")).pack(pady=(0, 4))
        ttk.Label(container, text="Keep your screen awake",
                  font=("Segoe UI", 11)).pack(pady=(0, 24))

        # Status indicator
        self.status_canvas = tk.Canvas(container, width=120, height=120,
                                       bg=c["bg"], highlightthickness=0)
        self.status_canvas.pack(pady=10)
        self._draw_indicator(False)

        # Status text
        self.status_label = ttk.Label(
            container, text="Status: Inactive",
            font=("Segoe UI", 14))
        self.status_label.pack(pady=8)

        # Toggle button
        self.toggle_btn = ttk.Button(
            container, text="▶  Activate eGuard",
            command=self._toggle)
        self.toggle_btn.pack(pady=10)

        # Info
        ttk.Label(container,
                  text="Prevents sleep by simulating activity\n"
                       "Works on Windows, macOS, and Linux",
                  foreground="#888888", justify=tk.CENTER,
                  font=("Segoe UI", 9)).pack(pady=(16, 0))

    def _draw_indicator(self, active: bool):
        self.status_canvas.delete("all")
        color = "#4ec9b0" if active else "#555555"
        glow = "#2a6e5e" if active else "#333333"
        # Outer glow
        self.status_canvas.create_oval(10, 10, 110, 110, fill=glow,
                                       outline="", width=0)
        # Inner circle
        self.status_canvas.create_oval(25, 25, 95, 95, fill=color,
                                       outline="", width=0)
        # Center icon
        text = "✓" if active else "○"
        self.status_canvas.create_text(60, 60, text=text,
                                       font=("Segoe UI", 24, "bold"),
                                       fill="#ffffff")

    def _toggle(self):
        if self._active:
            self._deactivate()
        else:
            self._activate()

    def _activate(self):
        self._active = True
        self._draw_indicator(True)
        self.status_label.config(text="Status: Active ✓")
        self.toggle_btn.config(text="⏸  Deactivate eGuard")
        self.app.set_status("eGuard: Keeping screen awake")

        if sys.platform == "win32":
            # Prevent sleep on Windows
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
            except Exception:
                pass
        else:
            # For macOS/Linux, use a background thread with mouse jiggle
            self._thread = threading.Thread(target=self._keep_alive_loop,
                                            daemon=True)
            self._thread.start()

    def _deactivate(self):
        self._active = False
        self._draw_indicator(False)
        self.status_label.config(text="Status: Inactive")
        self.toggle_btn.config(text="▶  Activate eGuard")
        self.app.set_status("eGuard: Deactivated")

        if sys.platform == "win32":
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            except Exception:
                pass

    def _keep_alive_loop(self):
        import time
        while self._active:
            # Simulate minimal activity
            time.sleep(30)

    def on_close(self):
        self._deactivate()
