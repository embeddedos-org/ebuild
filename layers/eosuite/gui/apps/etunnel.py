# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eTunnel — SSH tunneling and port forwarding manager.
Supports Local (-L), Remote (-R), and Dynamic (-D) SSH tunnels.
"""
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox


class ETunnel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._tunnels = []
        self._build()

    def _build(self):
        c = self.app.theme.colors

        container = ttk.Frame(self, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="🚇 eTunnel", font=("Segoe UI", 18, "bold")).pack(pady=(0, 4))
        ttk.Label(container, text="SSH Tunneling & Port Forwarding Manager",
                  font=("Segoe UI", 11)).pack(pady=(0, 20))

        # Tunnel type
        type_frame = ttk.Frame(container)
        type_frame.pack(fill=tk.X, padx=20, pady=4)
        ttk.Label(type_frame, text="Tunnel Type:", width=16).pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value="Local (-L)")
        ttk.Combobox(type_frame, textvariable=self.type_var,
                     values=["Local (-L)", "Remote (-R)", "Dynamic SOCKS (-D)"],
                     state="readonly", width=25).pack(side=tk.LEFT, padx=4)

        # SSH Host
        host_frame = ttk.Frame(container)
        host_frame.pack(fill=tk.X, padx=20, pady=4)
        ttk.Label(host_frame, text="SSH Host:", width=16).pack(side=tk.LEFT)
        self.host_var = tk.StringVar()
        ttk.Entry(host_frame, textvariable=self.host_var, font=("Consolas", 11)).pack(
            fill=tk.X, expand=True, side=tk.LEFT, padx=4)

        # SSH User
        user_frame = ttk.Frame(container)
        user_frame.pack(fill=tk.X, padx=20, pady=4)
        ttk.Label(user_frame, text="SSH User:", width=16).pack(side=tk.LEFT)
        self.user_var = tk.StringVar()
        ttk.Entry(user_frame, textvariable=self.user_var).pack(
            fill=tk.X, expand=True, side=tk.LEFT, padx=4)

        # Local Port
        lport_frame = ttk.Frame(container)
        lport_frame.pack(fill=tk.X, padx=20, pady=4)
        ttk.Label(lport_frame, text="Local Port:", width=16).pack(side=tk.LEFT)
        self.local_port_var = tk.StringVar(value="8080")
        ttk.Entry(lport_frame, textvariable=self.local_port_var, width=8).pack(side=tk.LEFT, padx=4)

        # Remote Host:Port
        rhost_frame = ttk.Frame(container)
        rhost_frame.pack(fill=tk.X, padx=20, pady=4)
        ttk.Label(rhost_frame, text="Remote Host:Port:", width=16).pack(side=tk.LEFT)
        self.remote_var = tk.StringVar(value="localhost:80")
        ttk.Entry(rhost_frame, textvariable=self.remote_var).pack(
            fill=tk.X, expand=True, side=tk.LEFT, padx=4)

        # SSH Port
        sport_frame = ttk.Frame(container)
        sport_frame.pack(fill=tk.X, padx=20, pady=4)
        ttk.Label(sport_frame, text="SSH Port:", width=16).pack(side=tk.LEFT)
        self.ssh_port_var = tk.StringVar(value="22")
        ttk.Entry(sport_frame, textvariable=self.ssh_port_var, width=8).pack(side=tk.LEFT, padx=4)

        # Buttons
        btn_frame = ttk.Frame(container)
        btn_frame.pack(pady=16)
        ttk.Button(btn_frame, text="🚀 Start Tunnel", command=self._start_tunnel).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="⏹ Stop All", command=self._stop_all).pack(side=tk.LEFT, padx=6)

        # Command preview
        ttk.Label(container, text="SSH Command Preview:", font=("Segoe UI", 10, "bold")).pack(
            anchor=tk.W, padx=20, pady=(8, 2))
        self.preview_var = tk.StringVar()
        ttk.Entry(container, textvariable=self.preview_var, state="readonly",
                  font=("Consolas", 10)).pack(fill=tk.X, padx=20, pady=(0, 8))

        # Bind changes to update preview
        for var in (self.type_var, self.host_var, self.user_var,
                    self.local_port_var, self.remote_var, self.ssh_port_var):
            var.trace_add("write", self._update_preview)
        self._update_preview()

        # Active tunnels list
        ttk.Label(container, text="Active Tunnels:", font=("Segoe UI", 10, "bold")).pack(
            anchor=tk.W, padx=20, pady=(8, 2))
        cols = ("Type", "Local", "Remote", "SSH Host", "Status")
        self.tree = ttk.Treeview(container, columns=cols, show="headings", height=5)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(fill=tk.X, padx=20, pady=4)

        # Log area
        self.log_text = tk.Text(container, height=4, font=("Consolas", 10),
                                bg=c["terminal_bg"], fg=c["terminal_fg"],
                                state=tk.DISABLED, relief=tk.FLAT, borderwidth=4)
        self.log_text.pack(fill=tk.X, padx=20, pady=4)

    def _update_preview(self, *_args):
        ttype = self.type_var.get()
        user = self.user_var.get().strip()
        host = self.host_var.get().strip()
        lport = self.local_port_var.get().strip()
        remote = self.remote_var.get().strip()
        sport = self.ssh_port_var.get().strip()

        target = ("%s@%s" % (user, host)) if user else host
        port_flag = (" -p %s" % sport) if sport and sport != "22" else ""

        if "Local" in ttype:
            cmd = "ssh -N -L %s:%s%s %s" % (lport, remote, port_flag, target)
        elif "Remote" in ttype:
            cmd = "ssh -N -R %s:%s%s %s" % (lport, remote, port_flag, target)
        else:
            cmd = "ssh -N -D %s%s %s" % (lport, port_flag, target)

        self.preview_var.set(cmd)

    def _start_tunnel(self):
        host = self.host_var.get().strip()
        if not host:
            messagebox.showwarning("Missing Host", "Enter an SSH host.")
            return

        cmd = self.preview_var.get()
        self._log("Starting: %s" % cmd)

        try:
            kwargs = dict(stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT)
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            proc = subprocess.Popen(cmd, shell=True, **kwargs)

            ttype = self.type_var.get().split("(")[0].strip()
            info = {
                "process": proc,
                "type": ttype,
                "local": self.local_port_var.get(),
                "remote": self.remote_var.get(),
                "host": host,
            }
            self._tunnels.append(info)
            self.tree.insert("", tk.END, values=(
                ttype, info["local"], info["remote"], host, "Running"))
            self._log("Tunnel started on port %s" % info["local"])
            self.app.set_status("eTunnel: %s forwarding on port %s" % (ttype, info["local"]))

            threading.Thread(target=self._monitor, args=(proc, info), daemon=True).start()
        except Exception as e:
            self._log("Error: %s" % str(e))

    def _monitor(self, proc, info):
        proc.wait()
        self.after(0, lambda: self._log("Tunnel to %s closed" % info["host"]))

    def _stop_all(self):
        for t in self._tunnels:
            try:
                t["process"].terminate()
            except Exception:
                pass
        self._tunnels.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._log("All tunnels stopped")

    def _log(self, text):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def on_close(self):
        self._stop_all()
