# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Terminal Tab — Embedded terminal using subprocess.
"""
import os
import sys
import subprocess
import threading
import re
import tkinter as tk
from tkinter import ttk, scrolledtext


class TerminalTab(ttk.Frame):
    """Embedded terminal tab that runs a shell process."""

    ANSI_COLORS = {
        "30": "#000000", "31": "#cc0000", "32": "#4e9a06",
        "33": "#c4a000", "34": "#3465a4", "35": "#75507b",
        "36": "#06989a", "37": "#d3d7cf",
        "90": "#555753", "91": "#ef2929", "92": "#8ae234",
        "93": "#fce94f", "94": "#729fcf", "95": "#ad7fa8",
        "96": "#34e2e2", "97": "#eeeeec",
    }

    def __init__(self, parent, app, command=None):
        super().__init__(parent)
        self.app = app
        self.process = None
        self._running = False
        self._build()
        self._start_process(command)

    def _build(self):
        c = self.app.theme.colors

        self.output = scrolledtext.ScrolledText(
            self,
            bg=c["terminal_bg"],
            fg=c["terminal_fg"],
            insertbackground=c["terminal_fg"],
            font=("Consolas", 11),
            wrap=tk.WORD,
            state=tk.NORMAL,
            relief=tk.FLAT,
            borderwidth=0,
            padx=6,
            pady=4,
        )
        self.output.pack(fill=tk.BOTH, expand=True)

        for code, color in self.ANSI_COLORS.items():
            self.output.tag_configure(f"ansi_{code}", foreground=color)
        self.output.tag_configure("bold", font=("Consolas", 11, "bold"))

        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X)

        ttk.Label(input_frame, text=" ❯ ",
                  font=("Consolas", 11, "bold")).pack(side=tk.LEFT)

        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(
            input_frame, textvariable=self.input_var,
            font=("Consolas", 11))
        self.input_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 4))
        self.input_entry.bind("<Return>", self._on_enter)
        self.input_entry.bind("<Up>", self._on_history_up)
        self.input_entry.bind("<Down>", self._on_history_down)
        self.input_entry.focus_set()

        self._history = []
        self._history_idx = -1

    def _start_process(self, command=None):
        if command:
            self._spawn(command, shell=True)
        else:
            if sys.platform == "win32":
                self._spawn("cmd.exe", shell=False)
            else:
                shell = os.environ.get("SHELL", "/bin/bash")
                self._spawn(shell, shell=False)

    def _spawn(self, cmd, shell=False):
        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            if shell:
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,
                    bufsize=0,
                    creationflags=creation_flags,
                )
            else:
                self.process = subprocess.Popen(
                    [cmd] if isinstance(cmd, str) else cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=0,
                    creationflags=creation_flags,
                )
            self._running = True
            t = threading.Thread(target=self._read_output, daemon=True)
            t.start()
        except Exception as e:
            self._append_text(f"[Error starting process: {e}]\n")

    def _read_output(self):
        try:
            while self._running and self.process and self.process.poll() is None:
                data = self.process.stdout.read(1)
                if data:
                    text = data.decode("utf-8", errors="replace")
                    self.after(0, self._append_text, text)
            if self.process:
                remaining = self.process.stdout.read()
                if remaining:
                    text = remaining.decode("utf-8", errors="replace")
                    self.after(0, self._append_text, text)
            self.after(0, self._append_text, "\n[Process exited]\n")
        except Exception:
            pass

    def _append_text(self, text: str):
        ansi_re = re.compile(r'\x1b\[([0-9;]*)m')
        pos = 0
        self.output.config(state=tk.NORMAL)
        for match in ansi_re.finditer(text):
            before = text[pos:match.start()]
            if before:
                self.output.insert(tk.END, before)
            pos = match.end()
            codes = match.group(1).split(";")
            for code in codes:
                if code in self.ANSI_COLORS:
                    self.output.tag_add(f"ansi_{code}",
                                        f"{tk.END}-1c linestart",
                                        tk.END)
        remaining = text[pos:]
        if remaining:
            self.output.insert(tk.END, remaining)
        self.output.see(tk.END)

    def _on_enter(self, _event):
        cmd = self.input_var.get()
        self.input_var.set("")
        if cmd.strip():
            self._history.append(cmd)
            self._history_idx = len(self._history)
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write((cmd + "\n").encode("utf-8"))
                self.process.stdin.flush()
            except Exception as e:
                self._append_text(f"[Send error: {e}]\n")

    def _on_history_up(self, _event):
        if self._history and self._history_idx > 0:
            self._history_idx -= 1
            self.input_var.set(self._history[self._history_idx])

    def _on_history_down(self, _event):
        if self._history_idx < len(self._history) - 1:
            self._history_idx += 1
            self.input_var.set(self._history[self._history_idx])
        else:
            self._history_idx = len(self._history)
            self.input_var.set("")

    def on_close(self):
        self._running = False
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass
