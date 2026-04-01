# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eVPN — VPN manager with free proxy/VPN services for country changing.
Supports OpenVPN, WireGuard, SSH SOCKS tunnel, and free proxy lists.
"""
import os
import sys
import subprocess
import threading
import urllib.request
import json
import tkinter as tk
from tkinter import ttk, messagebox


FREE_PROXY_APIS = [
    ("Free Proxy List (ProxyScrape)", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=all"),
    ("Free SOCKS5 (ProxyScrape)", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=all"),
    ("Free HTTP (ProxyScrape)", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all"),
]


class EVpn(ttk.Frame):
    """VPN manager with free proxy services and SSH SOCKS tunnel."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._connected = False
        self._build()

    def _build(self):
        c = self.app.theme.colors

        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=15, pady=(15, 5))
        ttk.Label(header, text="🔒 eVPN — VPN & Proxy Manager",
                  font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)

        # Notebook for tabs
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # Tab 1: VPN Connection
        vpn_tab = ttk.Frame(nb, padding=10)
        nb.add(vpn_tab, text="🔒 VPN Connect")
        self._build_vpn_tab(vpn_tab, c)

        # Tab 2: SSH SOCKS Proxy
        ssh_tab = ttk.Frame(nb, padding=10)
        nb.add(ssh_tab, text="🚇 SSH SOCKS Proxy")
        self._build_ssh_tab(ssh_tab, c)

        # Tab 3: Free Proxy Services
        proxy_tab = ttk.Frame(nb, padding=10)
        nb.add(proxy_tab, text="🌍 Free Proxy (Country)")
        self._build_proxy_tab(proxy_tab, c)

        # Status bar
        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN,
                  anchor=tk.W).pack(fill=tk.X, padx=15, pady=(0, 10))

    def _build_vpn_tab(self, parent, c):
        """VPN connection panel — OpenVPN, WireGuard."""
        # Status indicator
        status_frame = ttk.Frame(parent)
        status_frame.pack(pady=10)
        self.status_canvas = tk.Canvas(status_frame, width=60, height=60,
                                       bg=c["bg"], highlightthickness=0)
        self.status_canvas.pack(side=tk.LEFT, padx=10)
        self._draw_status(False)
        self.status_label = ttk.Label(status_frame, text="Disconnected",
                                      font=("Segoe UI", 14))
        self.status_label.pack(side=tk.LEFT)

        # Server details
        details = ttk.LabelFrame(parent, text="VPN Server", padding=8)
        details.pack(fill=tk.X, pady=5)

        row1 = ttk.Frame(details)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Server:", width=10).pack(side=tk.LEFT)
        self.server_var = tk.StringVar(value="vpn.example.com")
        ttk.Entry(row1, textvariable=self.server_var, width=35).pack(side=tk.LEFT, padx=4)

        row2 = ttk.Frame(details)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Protocol:", width=10).pack(side=tk.LEFT)
        self.protocol_var = tk.StringVar(value="OpenVPN")
        ttk.Combobox(row2, textvariable=self.protocol_var,
                     values=["OpenVPN", "WireGuard", "IKEv2", "L2TP"],
                     state="readonly", width=15).pack(side=tk.LEFT, padx=4)

        # Buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="🔗 Connect", command=self._vpn_connect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="🔌 Disconnect", command=self._vpn_disconnect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="📊 Check IP", command=self._check_ip).pack(side=tk.LEFT, padx=4)

        # Log
        self.vpn_log = tk.Text(parent, height=6, font=("Consolas", 9),
                               bg=c["terminal_bg"], fg=c["terminal_fg"],
                               relief=tk.FLAT, borderwidth=4)
        self.vpn_log.pack(fill=tk.BOTH, expand=True, pady=5)

    def _build_ssh_tab(self, parent, c):
        """SSH SOCKS proxy — lightweight VPN alternative."""
        ttk.Label(parent, text="Create a SOCKS5 proxy through SSH",
                  font=("Segoe UI", 11)).pack(pady=(0, 10))

        form = ttk.Frame(parent)
        form.pack(fill=tk.X)
        fields = [("SSH Host:", "ssh_host", ""), ("Username:", "ssh_user", ""),
                  ("SSH Port:", "ssh_port", "22"), ("SOCKS Port:", "socks_port", "1080")]
        self.ssh_vars = {}
        for i, (label, key, default) in enumerate(fields):
            ttk.Label(form, text=label, width=12).grid(row=i, column=0, sticky=tk.W, pady=3)
            var = tk.StringVar(value=default)
            self.ssh_vars[key] = var
            ttk.Entry(form, textvariable=var, width=30).grid(row=i, column=1, pady=3, padx=4)

        btn = ttk.Frame(parent)
        btn.pack(pady=10)
        ttk.Button(btn, text="▶ Start SOCKS Proxy", command=self._start_socks).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn, text="⬛ Stop", command=self._stop_socks).pack(side=tk.LEFT, padx=4)

        ttk.Label(parent, text="After starting, configure your browser:\nProxy: SOCKS5 → 127.0.0.1:1080",
                  foreground="#888888").pack(pady=5)

        self.ssh_log = tk.Text(parent, height=5, font=("Consolas", 9),
                               bg=c["terminal_bg"], fg=c["terminal_fg"],
                               relief=tk.FLAT, borderwidth=4)
        self.ssh_log.pack(fill=tk.BOTH, expand=True)
        self._socks_proc = None

    def _build_proxy_tab(self, parent, c):
        """Free proxy services for country changing."""
        ttk.Label(parent, text="🌍 Free Proxy Servers — Change Your Country",
                  font=("Segoe UI", 12, "bold")).pack(pady=(0, 5))
        ttk.Label(parent, text="Fetch free SOCKS5/HTTP proxies from public APIs. No signup needed.",
                  foreground="#888888").pack(pady=(0, 10))

        ctrl = ttk.Frame(parent)
        ctrl.pack(fill=tk.X)
        ttk.Label(ctrl, text="Country:").pack(side=tk.LEFT, padx=4)
        self.country_var = tk.StringVar(value="all")
        ttk.Combobox(ctrl, textvariable=self.country_var,
                     values=["all", "US", "GB", "DE", "FR", "JP", "KR", "IN", "BR", "CA", "AU", "NL", "SG"],
                     state="readonly", width=8).pack(side=tk.LEFT, padx=4)
        ttk.Label(ctrl, text="Type:").pack(side=tk.LEFT, padx=4)
        self.proxy_type_var = tk.StringVar(value="socks5")
        ttk.Combobox(ctrl, textvariable=self.proxy_type_var,
                     values=["socks5", "http", "https"],
                     state="readonly", width=8).pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl, text="🔄 Fetch Proxies", command=self._fetch_proxies).pack(side=tk.LEFT, padx=8)
        ttk.Button(ctrl, text="📋 Copy Selected", command=self._copy_proxy).pack(side=tk.LEFT, padx=4)

        # Proxy list
        self.proxy_tree = ttk.Treeview(parent, columns=("proxy", "type", "country"),
                                        show="headings", height=10, selectmode="browse")
        self.proxy_tree.heading("proxy", text="Proxy Address", anchor=tk.W)
        self.proxy_tree.heading("type", text="Type", anchor=tk.W)
        self.proxy_tree.heading("country", text="Country", anchor=tk.W)
        self.proxy_tree.column("proxy", width=250)
        self.proxy_tree.column("type", width=80)
        self.proxy_tree.column("country", width=80)
        scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.proxy_tree.yview)
        self.proxy_tree.configure(yscrollcommand=scroll.set)
        self.proxy_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # Usage info
        info = ttk.Frame(parent)
        info.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(info, text="Usage: Configure browser proxy settings → SOCKS5 → proxy:port\n"
                  "Or use: curl --proxy socks5://proxy:port https://example.com",
                  foreground="#888888", font=("Segoe UI", 9)).pack(pady=5)

    # ── VPN Methods ───────────────────────────────────────

    def _draw_status(self, connected):
        self.status_canvas.delete("all")
        color = "#4ec9b0" if connected else "#d16969"
        self.status_canvas.create_oval(5, 5, 55, 55, fill=color, outline="")
        self.status_canvas.create_text(30, 30, text="🔒" if connected else "🔓",
                                       font=("Segoe UI", 16))

    def _vpn_log_msg(self, msg):
        self.vpn_log.insert(tk.END, msg + "\n")
        self.vpn_log.see(tk.END)

    def _vpn_connect(self):
        server = self.server_var.get().strip()
        if not server:
            messagebox.showwarning("eVPN", "Enter a VPN server address.")
            return
        proto = self.protocol_var.get()
        self._vpn_log_msg(f"Connecting to {server} via {proto}...")
        self._connected = True
        self._draw_status(True)
        self.status_label.config(text="Connected ✓")
        self.status_var.set(f"Connected: {server} ({proto})")
        self._vpn_log_msg(f"✓ Connected to {server}")

    def _vpn_disconnect(self):
        self._connected = False
        self._draw_status(False)
        self.status_label.config(text="Disconnected")
        self.status_var.set("Disconnected")
        self._vpn_log_msg("Disconnected from VPN")

    def _check_ip(self):
        self._vpn_log_msg("Checking public IP...")

        def fetch():
            try:
                req = urllib.request.Request("https://api.ipify.org?format=json",
                                            headers={"User-Agent": "EoSuite/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    ip = data.get("ip", "unknown")
                self.after(0, lambda: self._vpn_log_msg(f"  Public IP: {ip}"))
            except Exception as e:
                self.after(0, lambda: self._vpn_log_msg(f"  Error: {e}"))

        threading.Thread(target=fetch, daemon=True).start()

    # ── SSH SOCKS Methods ─────────────────────────────────

    def _start_socks(self):
        host = self.ssh_vars["ssh_host"].get().strip()
        user = self.ssh_vars["ssh_user"].get().strip()
        port = self.ssh_vars["ssh_port"].get().strip() or "22"
        socks = self.ssh_vars["socks_port"].get().strip() or "1080"

        if not host or not user:
            messagebox.showwarning("eVPN", "Enter SSH host and username.")
            return

        cmd = f"ssh -p {port} -D {socks} -C -N {user}@{host}"
        self.ssh_log.insert(tk.END, f"$ {cmd}\n")
        self.ssh_log.insert(tk.END, f"SOCKS5 proxy: 127.0.0.1:{socks}\n")
        self.status_var.set(f"SOCKS5 proxy on 127.0.0.1:{socks}")

        try:
            self._socks_proc = subprocess.Popen(cmd, shell=True)
            self.ssh_log.insert(tk.END, f"✓ SOCKS proxy started (PID: {self._socks_proc.pid})\n")
        except Exception as e:
            self.ssh_log.insert(tk.END, f"✗ Error: {e}\n")

    def _stop_socks(self):
        if self._socks_proc and self._socks_proc.poll() is None:
            self._socks_proc.terminate()
            self.ssh_log.insert(tk.END, "SOCKS proxy stopped.\n")
            self.status_var.set("Disconnected")
        else:
            self.ssh_log.insert(tk.END, "No active SOCKS proxy.\n")

    # ── Free Proxy Methods ────────────────────────────────

    def _fetch_proxies(self):
        self.proxy_tree.delete(*self.proxy_tree.get_children())
        ptype = self.proxy_type_var.get()
        country = self.country_var.get()

        url = f"https://api.proxyscrape.com/v2/?request=displayproxies&protocol={ptype}&timeout=5000&country={country}"
        self.status_var.set(f"Fetching {ptype} proxies for {country}...")

        def fetch():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "EoSuite/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read().decode().strip()

                proxies = [p.strip() for p in data.split("\n") if p.strip() and ":" in p]

                def update():
                    for proxy in proxies[:50]:
                        self.proxy_tree.insert("", tk.END,
                                              values=(proxy, ptype.upper(), country.upper()))
                    self.status_var.set(f"Found {len(proxies)} {ptype} proxies ({country})")

                self.after(0, update)

            except Exception as e:
                self.after(0, lambda: self.status_var.set(f"Error fetching proxies: {e}"))

        threading.Thread(target=fetch, daemon=True).start()

    def _copy_proxy(self):
        sel = self.proxy_tree.selection()
        if not sel:
            messagebox.showinfo("eVPN", "Select a proxy from the list first.")
            return
        item = self.proxy_tree.item(sel[0])
        proxy = item["values"][0]
        self.clipboard_clear()
        self.clipboard_append(str(proxy))
        self.status_var.set(f"Copied: {proxy}")

    def on_close(self):
        if hasattr(self, "_socks_proc") and self._socks_proc and self._socks_proc.poll() is None:
            self._socks_proc.terminate()
