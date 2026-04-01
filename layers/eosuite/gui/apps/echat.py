# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eChat — Chat window with message display and input field.
"""
import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext


class EChat(ttk.Frame):
    """Simple chat interface with message display and input."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._username = "You"
        self._build()

    def _build(self):
        c = self.app.theme.colors

        # Header
        header = ttk.Frame(self, style="Toolbar.TFrame")
        header.pack(fill=tk.X)

        ttk.Label(header, text="💬 eChat", style="Toolbar.TLabel",
                  font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=8, pady=4)

        ttk.Label(header, text="Username:", style="Toolbar.TLabel").pack(
            side=tk.LEFT, padx=(16, 4))
        self.name_var = tk.StringVar(value="You")
        ttk.Entry(header, textvariable=self.name_var, width=15).pack(
            side=tk.LEFT, padx=4)

        ttk.Button(header, text="Clear Chat", style="Toolbar.TButton",
                   command=self._clear).pack(side=tk.RIGHT, padx=8)

        # Chat display
        self.chat_display = scrolledtext.ScrolledText(
            self, font=("Segoe UI", 11),
            bg=c["terminal_bg"], fg=c["terminal_fg"],
            wrap=tk.WORD, state=tk.DISABLED,
            relief=tk.FLAT, borderwidth=4, padx=8, pady=4)
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        # Color tags
        self.chat_display.tag_configure("timestamp", foreground="#569cd6")
        self.chat_display.tag_configure("username", foreground="#4ec9b0",
                                        font=("Segoe UI", 11, "bold"))
        self.chat_display.tag_configure("system", foreground="#888888",
                                        font=("Segoe UI", 10, "italic"))

        # Input area
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, padx=4, pady=4)

        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(
            input_frame, textvariable=self.input_var,
            font=("Segoe UI", 12))
        self.input_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 4))
        self.input_entry.bind("<Return>", self._send_message)
        self.input_entry.focus_set()

        ttk.Button(input_frame, text="Send",
                   command=self._send_message).pack(side=tk.RIGHT)

        # Welcome message
        self._add_system_message("Welcome to eChat! Type a message below.")
        self._add_system_message("This is a local chat interface. "
                                 "Connect to a server for network chat.")

    def _add_message(self, username: str, message: str):
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.chat_display.insert(tk.END, f"{username}: ", "username")
        self.chat_display.insert(tk.END, f"{message}\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def _add_system_message(self, message: str):
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.chat_display.insert(tk.END, f"⚙ {message}\n", "system")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def _send_message(self, _event=None):
        msg = self.input_var.get().strip()
        if not msg:
            return
        self.input_var.set("")
        username = self.name_var.get().strip() or "You"
        self._add_message(username, msg)

        # Echo bot response for demo
        if msg.lower().startswith("/"):
            self._handle_command(msg)
        else:
            self.after(500, lambda: self._add_message(
                "eBot", f"Echo: {msg}"))

    def _handle_command(self, cmd: str):
        parts = cmd.split()
        command = parts[0].lower()
        if command == "/help":
            self._add_system_message(
                "Commands: /help, /clear, /time, /name <new_name>")
        elif command == "/clear":
            self._clear()
        elif command == "/time":
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._add_system_message(f"Current time: {now}")
        elif command == "/name" and len(parts) > 1:
            new_name = " ".join(parts[1:])
            self.name_var.set(new_name)
            self._add_system_message(f"Username changed to: {new_name}")
        else:
            self._add_system_message(f"Unknown command: {command}")

    def _clear(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self._add_system_message("Chat cleared.")
