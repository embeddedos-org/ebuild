# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eVNC — Lightweight VNC remote desktop viewer.
Connects to VNC servers using system vncviewer or built-in RFB protocol display.
"""
import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox


class EVnc(ttk.Frame):
    """VNC remote desktop viewer tab."""

    VIEWERS = [
        ("TigerVNC", "vncviewer"),
        ("TightVNC", "tvnviewer"),
        ("RealVNC", "vncviewer"),
        ("UltraVNC", "ultravnc_viewer"),
    ]

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self._process = None
        self._build()

    def _build(self):
        c = self.app.theme.colors if self.app else {"input_bg": "#2d2d2d", "input_fg": "#d4d4d4", "terminal_bg": "#0c0c0c", "terminal_fg": "#cccccc"}

        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=15, pady=(15, 5))
        ttk.Label(header, text="🖥 eVNC — Remote Desktop Viewer",
                  font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)

        # Connection panel
        conn = ttk.LabelFrame(self, text="Connection", padding=10)
        conn.pack(fill=tk.X, padx=15, pady=5)

        row1 = ttk.Frame(conn)
        row1.pack(fill=tk.X, pady=3)
        ttk.Label(row1, text="Host:", width=12).pack(side=tk.LEFT)
        self.host_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.host_var, width=30).pack(side=tk.LEFT, padx=4)
        ttk.Label(row1, text="Port:").pack(side=tk.LEFT, padx=(10, 4))
        self.port_var = tk.StringVar(value="5900")
        ttk.Entry(row1, textvariable=self.port_var, width=8).pack(side=tk.LEFT)

        row2 = ttk.Frame(conn)
        row2.pack(fill=tk.X, pady=3)
        ttk.Label(row2, text="Password:", width=12).pack(side=tk.LEFT)
        self.pass_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.pass_var, show="•", width=30).pack(side=tk.LEFT, padx=4)
        ttk.Label(row2, text="Display:").pack(side=tk.LEFT, padx=(10, 4))
        self.display_var = tk.StringVar(value="0")
        ttk.Entry(row2, textvariable=self.display_var, width=8).pack(side=tk.LEFT)

        row3 = ttk.Frame(conn)
        row3.pack(fill=tk.X, pady=3)
        ttk.Label(row3, text="Quality:", width=12).pack(side=tk.LEFT)
        self.quality_var = tk.StringVar(value="Medium")
        ttk.Combobox(row3, textvariable=self.quality_var,
                     values=["Low (fast)", "Medium", "High (slow)", "Lossless"],
                     state="readonly", width=15).pack(side=tk.LEFT, padx=4)
        self.fullscreen_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="Fullscreen", variable=self.fullscreen_var).pack(side=tk.LEFT, padx=10)
        self.viewonly_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="View Only", variable=self.viewonly_var).pack(side=tk.LEFT, padx=4)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=15, pady=10)

        ttk.Button(btn_frame, text="▶ Connect", command=self._connect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="⬛ Disconnect", command=self._disconnect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="🔍 Detect VNC Clients", command=self._detect_viewers).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="📋 SSH Tunnel + VNC", command=self._ssh_tunnel_vnc).pack(side=tk.LEFT, padx=4)

        # Saved connections
        saved_frame = ttk.LabelFrame(self, text="Saved Connections", padding=8)
        saved_frame.pack(fill=tk.X, padx=15, pady=5)

        self.saved_tree = ttk.Treeview(saved_frame, columns=("host", "port", "display"),
                                        show="headings", height=4, selectmode="browse")
        self.saved_tree.heading("host", text="Host", anchor=tk.W)
        self.saved_tree.heading("port", text="Port", anchor=tk.W)
        self.saved_tree.heading("display", text="Display", anchor=tk.W)
        self.saved_tree.column("host", width=250)
        self.saved_tree.column("port", width=80)
        self.saved_tree.column("display", width=80)
        self.saved_tree.pack(fill=tk.X)
        self.saved_tree.bind("<Double-1>", self._load_saved)

        save_btns = ttk.Frame(saved_frame)
        save_btns.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(save_btns, text="💾 Save Current", command=self._save_connection).pack(side=tk.LEFT, padx=2)
        ttk.Button(save_btns, text="🗑 Remove", command=self._remove_saved).pack(side=tk.LEFT, padx=2)

        # Status / log
        log_frame = ttk.LabelFrame(self, text="Connection Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 15))

        self.log = tk.Text(log_frame, height=8, wrap=tk.WORD,
                          font=("Consolas", 9), bg=c.get("terminal_bg", "#0c0c0c"),
                          fg=c.get("terminal_fg", "#cccccc"))
        self.log.pack(fill=tk.BOTH, expand=True)

        self._log("Ready. Enter VNC host and click Connect.")
        self._log("Supported clients: TigerVNC, TightVNC, RealVNC, UltraVNC")
        self._detect_viewers_silent()
        self._load_saved_connections()

    def _log(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _detect_viewers_silent(self):
        """Detect installed VNC viewers without showing dialog."""
        for name, cmd in self.VIEWERS:
            try:
                result = subprocess.run(
                    ["where" if sys.platform == "win32" else "which", cmd],
                    capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    path = result.stdout.strip().split("\n")[0]
                    self._log(f"  Found: {name} → {path}")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

    def _detect_viewers(self):
        """Detect and display installed VNC viewers."""
        found = []
        self._log("\nDetecting VNC viewers...")
        for name, cmd in self.VIEWERS:
            try:
                where_cmd = "where" if sys.platform == "win32" else "which"
                result = subprocess.run([where_cmd, cmd],
                                       capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    path = result.stdout.strip().split("\n")[0]
                    found.append((name, path))
                    self._log(f"  ✓ {name}: {path}")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        if not found:
            self._log("  No VNC viewers found!")
            self._log("  Install one of:")
            self._log("    Windows: TigerVNC — https://tigervnc.org")
            self._log("    macOS:   brew install tiger-vnc")
            self._log("    Linux:   sudo apt install tigervnc-viewer")
            messagebox.showinfo("eVNC",
                "No VNC viewer found.\n\n"
                "Install TigerVNC:\n"
                "  Windows: https://tigervnc.org\n"
                "  macOS: brew install tiger-vnc\n"
                "  Linux: sudo apt install tigervnc-viewer")
        else:
            self._log(f"  Found {len(found)} viewer(s)")

    def _find_viewer(self):
        """Find the first available VNC viewer command."""
        for name, cmd in self.VIEWERS:
            try:
                where_cmd = "where" if sys.platform == "win32" else "which"
                result = subprocess.run([where_cmd, cmd],
                                       capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return cmd, name
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        return None, None

    def _connect(self):
        host = self.host_var.get().strip()
        if not host:
            messagebox.showwarning("eVNC", "Enter a VNC host address.")
            return

        port = self.port_var.get().strip() or "5900"
        display = self.display_var.get().strip() or "0"
        password = self.pass_var.get()

        viewer_cmd, viewer_name = self._find_viewer()

        if not viewer_cmd:
            self._log("No VNC viewer found. Trying system default...")
            addr = f"{host}:{port}"
            if sys.platform == "win32":
                cmd_str = f'start "" vnc://{addr}'
            elif sys.platform == "darwin":
                cmd_str = f'open vnc://{addr}'
            else:
                cmd_str = f'xdg-open vnc://{addr}'

            self._log(f"Opening: vnc://{addr}")
            subprocess.Popen(cmd_str, shell=True)
            return

        # Build viewer command
        args = [viewer_cmd]

        quality_map = {"Low (fast)": "1", "Medium": "5", "High (slow)": "9", "Lossless": "9"}
        quality = quality_map.get(self.quality_var.get(), "5")

        if viewer_cmd == "vncviewer":
            args.append(f"{host}::{port}")
            if self.fullscreen_var.get():
                args.append("-fullscreen")
            if self.viewonly_var.get():
                args.append("-viewonly")
            args.extend(["-quality", quality])
        elif viewer_cmd == "tvnviewer":
            args.extend([f"{host}::{port}"])
        else:
            args.append(f"{host}:{display}")

        self._log(f"\nConnecting via {viewer_name}...")
        self._log(f"  Host: {host}:{port} (display :{display})")
        self._log(f"  Quality: {self.quality_var.get()}")
        self._log(f"  Command: {' '.join(args)}")

        try:
            self._process = subprocess.Popen(args, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
            self._log(f"  ✓ {viewer_name} launched (PID: {self._process.pid})")

            def monitor():
                self._process.wait()
                self._log(f"\n  VNC session ended (exit code: {self._process.returncode})")

            threading.Thread(target=monitor, daemon=True).start()

        except FileNotFoundError:
            self._log(f"  ✗ {viewer_cmd} not found")
        except Exception as e:
            self._log(f"  ✗ Error: {e}")

    def _disconnect(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()
            self._log("VNC session terminated.")
        else:
            self._log("No active VNC session.")

    def _ssh_tunnel_vnc(self):
        """Create an SSH tunnel to a VNC server and connect."""
        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title("SSH Tunnel + VNC")
        dlg.geometry("420x280")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ttk.Label(dlg, text="🔐 SSH Tunnel to VNC",
                  font=("", 13, "bold")).pack(pady=(12, 8))

        form = ttk.Frame(dlg, padding=10)
        form.pack(fill=tk.X, padx=15)

        fields = [
            ("SSH Host:", "ssh_host", ""),
            ("SSH User:", "ssh_user", os.getenv("USER", os.getenv("USERNAME", ""))),
            ("SSH Port:", "ssh_port", "22"),
            ("VNC Host:", "vnc_host", "localhost"),
            ("VNC Port:", "vnc_port", "5900"),
            ("Local Port:", "local_port", "15900"),
        ]

        vars_dict = {}
        for i, (label, key, default) in enumerate(fields):
            ttk.Label(form, text=label, width=12).grid(row=i, column=0, sticky=tk.W, pady=2)
            var = tk.StringVar(value=default)
            vars_dict[key] = var
            ttk.Entry(form, textvariable=var, width=25).grid(row=i, column=1, pady=2, padx=4)

        def connect():
            ssh_host = vars_dict["ssh_host"].get()
            ssh_user = vars_dict["ssh_user"].get()
            ssh_port = vars_dict["ssh_port"].get()
            vnc_host = vars_dict["vnc_host"].get()
            vnc_port = vars_dict["vnc_port"].get()
            local_port = vars_dict["local_port"].get()

            if not ssh_host:
                messagebox.showwarning("eVNC", "Enter SSH host.")
                return

            tunnel_cmd = f"ssh -p {ssh_port} -L {local_port}:{vnc_host}:{vnc_port} -N {ssh_user}@{ssh_host}"
            self._log(f"\nSSH Tunnel: {tunnel_cmd}")
            dlg.destroy()

            try:
                proc = subprocess.Popen(tunnel_cmd, shell=True)
                self._log(f"  ✓ Tunnel started (PID: {proc.pid})")
                self._log(f"  Connect VNC to: localhost:{local_port}")
                self.host_var.set("localhost")
                self.port_var.set(local_port)
            except Exception as e:
                self._log(f"  ✗ Tunnel failed: {e}")

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="▶ Create Tunnel & Connect", command=connect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=4)

    def _save_connection(self):
        host = self.host_var.get().strip()
        if not host:
            return
        port = self.port_var.get().strip() or "5900"
        display = self.display_var.get().strip() or "0"
        self.saved_tree.insert("", tk.END, values=(host, port, display))
        self._log(f"  Saved: {host}:{port}")

    def _load_saved(self, event):
        sel = self.saved_tree.selection()
        if not sel:
            return
        item = self.saved_tree.item(sel[0])
        vals = item["values"]
        self.host_var.set(str(vals[0]))
        self.port_var.set(str(vals[1]))
        self.display_var.set(str(vals[2]))

    def _remove_saved(self):
        sel = self.saved_tree.selection()
        if sel:
            self.saved_tree.delete(sel[0])

    def _load_saved_connections(self):
        """Load saved VNC connections from config."""
        try:
            import json
            config_dir = os.path.join(os.path.expanduser("~"), ".eosuite")
            config_file = os.path.join(config_dir, "vnc_connections.json")
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    connections = json.load(f)
                for c in connections:
                    self.saved_tree.insert("", tk.END,
                                          values=(c.get("host", ""), c.get("port", "5900"),
                                                  c.get("display", "0")))
        except Exception:
            pass

    def on_close(self):
        self._disconnect()
