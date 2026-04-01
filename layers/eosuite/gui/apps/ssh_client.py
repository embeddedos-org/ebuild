# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite SSH Client — Connection dialog and SSH session launcher.
"""
import tkinter as tk
from tkinter import ttk, messagebox


class SSHDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("New SSH Connection")
        self.geometry("450x380")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        c = self.app.theme.colors
        self.configure(bg=c["bg"])

        main = ttk.Frame(self, padding=20)
        main.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main, text="🔐 New SSH Connection", font=("Segoe UI", 14, "bold")).pack(pady=(0, 16))

        ttk.Label(main, text="Quick Connect (user@host:port):").pack(anchor=tk.W, pady=(0, 4))
        self.quick_var = tk.StringVar()
        ttk.Entry(main, textvariable=self.quick_var, font=("Consolas", 11)).pack(fill=tk.X, pady=(0, 12))

        ttk.Separator(main, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(main, text="— or fill in details —", foreground="#888888").pack(pady=4)

        fields = ttk.Frame(main)
        fields.pack(fill=tk.X, pady=4)
        self.host_var, self.user_var = tk.StringVar(), tk.StringVar()
        self.port_var, self.key_var = tk.StringVar(value="22"), tk.StringVar()
        for label, var in [("Host:", self.host_var), ("Username:", self.user_var),
                           ("Port:", self.port_var), ("Identity File:", self.key_var)]:
            row = ttk.Frame(fields)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=14).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var).pack(fill=tk.X, expand=True, side=tk.LEFT)

        name_row = ttk.Frame(fields)
        name_row.pack(fill=tk.X, pady=2)
        ttk.Label(name_row, text="Session Name:", width=14).pack(side=tk.LEFT)
        self.name_var = tk.StringVar()
        ttk.Entry(name_row, textvariable=self.name_var).pack(fill=tk.X, expand=True, side=tk.LEFT)

        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=(16, 0))
        ttk.Button(btn_frame, text="Connect", command=self._connect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Save & Connect", command=self._save_and_connect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=4)

    def _parse_quick(self):
        quick = self.quick_var.get().strip()
        if quick:
            user, host, port = "", quick, "22"
            if "@" in quick:
                user, host = quick.split("@", 1)
            if ":" in host:
                host, port = host.rsplit(":", 1)
            return user, host, port
        return self.user_var.get(), self.host_var.get(), self.port_var.get()

    def _build_command(self):
        user, host, port = self._parse_quick()
        if not host:
            messagebox.showwarning("Missing Host", "Please enter a host address.")
            return None
        cmd = "ssh"
        if port and port != "22":
            cmd += f" -p {port}"
        key = self.key_var.get().strip()
        if key:
            cmd += f" -i {key}"
        cmd += f" {user}@{host}" if user else f" {host}"
        return cmd

    def _get_name(self):
        name = self.name_var.get().strip()
        if not name:
            user, host, _ = self._parse_quick()
            name = f"{user}@{host}" if user else host
        return name

    def _connect(self):
        cmd = self._build_command()
        if cmd:
            self.app.connect_session(cmd, self._get_name())
            self.destroy()

    def _save_and_connect(self):
        cmd = self._build_command()
        if cmd:
            name = self._get_name()
            try:
                from gui.apps.session_manager import SessionManager
                SessionManager().add_session(name, "ssh", cmd)
                self.app.sidebar.add_ssh_session(name, cmd)
            except Exception:
                pass
            self.app.connect_session(cmd, name)
            self.destroy()
"""
EoSuite SSH Client — Connection dialog and SSH session launcher.
"""
import tkinter as tk
from tkinter import ttk, messagebox


class SSHDialog(tk.Toplevel):
    """Dialog for creating a new SSH connection."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("New SSH Connection")
        self.geometry("450x380")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._build()

    def _build(self):
        c = self.app.theme.colors
        self.configure(bg=c["bg"])

        main = ttk.Frame(self, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="🔐 New SSH Connection",
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 16))

        # Quick connect
        ttk.Label(main, text="Quick Connect (user@host:port):").pack(
            anchor=tk.W, pady=(0, 4))
        self.quick_var = tk.StringVar()
        quick_entry = ttk.Entry(main, textvariable=self.quick_var,
                                font=("Consolas", 11))
        quick_entry.pack(fill=tk.X, pady=(0, 12))
        quick_entry.focus_set()

        ttk.Separator(main, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(main, text="— or fill in details —",
                  foreground="#888888").pack(pady=4)

        # Detail fields
        fields_frame = ttk.Frame(main)
        fields_frame.pack(fill=tk.X, pady=4)

        self.host_var = tk.StringVar()
        self.user_var = tk.StringVar()
        self.port_var = tk.StringVar(value="22")
        self.key_var = tk.StringVar()

        for label, var in [("Host:", self.host_var), ("Username:", self.user_var),
                           ("Port:", self.port_var), ("Identity File:", self.key_var)]:
            row = ttk.Frame(fields_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=14).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var).pack(fill=tk.X, expand=True,
                                                  side=tk.LEFT)

        # Session name
        name_row = ttk.Frame(fields_frame)
        name_row.pack(fill=tk.X, pady=2)
        ttk.Label(name_row, text="Session Name:", width=14).pack(side=tk.LEFT)
        self.name_var = tk.StringVar()
        ttk.Entry(name_row, textvariable=self.name_var).pack(
            fill=tk.X, expand=True, side=tk.LEFT)

        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=(16, 0))
        ttk.Button(btn_frame, text="Connect", command=self._connect).pack(
            side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Save & Connect",
                   command=self._save_and_connect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel",
                   command=self.destroy).pack(side=tk.LEFT, padx=4)

    def _parse_quick(self):
        quick = self.quick_var.get().strip()
        if quick:
            # Parse user@host:port
            user, host, port = "", quick, "22"
            if "@" in quick:
                user, host = quick.split("@", 1)
            if ":" in host:
                host, port = host.rsplit(":", 1)
            return user, host, port
        return self.user_var.get(), self.host_var.get(), self.port_var.get()

    def _build_command(self):
        user, host, port = self._parse_quick()
        if not host:
            messagebox.showwarning("Missing Host", "Please enter a host address.")
            return None
        cmd = "ssh"
        if port and port != "22":
            cmd += f" -p {port}"
        key = self.key_var.get().strip()
        if key:
            cmd += f" -i {key}"
        if user:
            cmd += f" {user}@{host}"
        else:
            cmd += f" {host}"
        return cmd

    def _get_name(self):
        name = self.name_var.get().strip()
        if not name:
            user, host, port = self._parse_quick()
            name = f"{user}@{host}" if user else host
        return name

    def _connect(self):
        cmd = self._build_command()
        if cmd:
            self.app.connect_session(cmd, self._get_name())
            self.destroy()

    def _save_and_connect(self):
        cmd = self._build_command()
        if cmd:
            name = self._get_name()
            try:
                from gui.apps.session_manager import SessionManager
                mgr = SessionManager()
                mgr.add_session(name, "ssh", cmd)
                self.app.sidebar.add_ssh_session(name, cmd)
            except Exception:
                pass
            self.app.connect_session(cmd, name)
            self.destroy()
