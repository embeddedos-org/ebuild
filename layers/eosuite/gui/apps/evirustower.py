# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
eVirusTower — Lightweight malware scanner with hash + pattern detection.
"""
import os
import hashlib
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ── Malware signature database ────────────────────────────────────────

KNOWN_MALWARE_HASHES = {
    "44d88612fea8a8f36de82e1278abb02f": "EICAR Test File",
    "e1105070ba828007508566e28a2b8d4c": "EICAR (modified)",
    "a7f5138c9e24e05160e1b4eb5c504f11": "Trojan.Generic.A",
    "d41d8cd98f00b204e9800998ecf8427e": "Zero-byte file (suspicious)",
}

SUSPICIOUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".com", ".scr", ".pif", ".vbs", ".vbe",
    ".js", ".jse", ".wsf", ".wsh", ".ps1", ".msi", ".dll", ".cpl",
    ".hta", ".inf", ".reg", ".lnk",
}

SUSPICIOUS_PATTERNS = [
    (b"cmd.exe /c del", "Destructive Command"),
    (b"cmd.exe /c format", "Disk Format Command"),
    (b"cmd.exe /c rd /s", "Recursive Delete Command"),
    (b'CreateObject("WScript.Shell")', "WScript Shell Access"),
    (b"CreateObject(\"Scripting.FileSystemObject\")", "FSO Script Access"),
    (b"powershell -enc", "PowerShell Encoded Command"),
    (b"powershell -e ", "PowerShell Encoded Command"),
    (b"Invoke-Expression", "PowerShell Invoke-Expression"),
    (b"IEX(", "PowerShell IEX Call"),
    (b"Net.WebClient", "Network Download Attempt"),
    (b"DownloadString(", "Remote Code Download"),
    (b"DownloadFile(", "Remote File Download"),
    (b"Start-Process", "Process Execution"),
    (b"\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup",
     "Startup Folder Access"),
    (b"HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
     "Registry Autostart"),
]

MAX_SCAN_SIZE = 50_000_000  # 50 MB


# ── GUI Scanner Widget ────────────────────────────────────────────────

class EVirusTower(ttk.Frame):
    """Lightweight malware scanner GUI tab."""

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self._scanning = False
        self._threats = []
        self._files_scanned = 0
        self._scan_thread = None
        self._build()

    def _build(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(header, text="🛡 eVirusTower", font=("", 14, "bold")).pack(side=tk.LEFT)

        # Scan controls
        ctrl = ttk.LabelFrame(self, text="Scan", padding=8)
        ctrl.pack(fill=tk.X, padx=10, pady=5)

        self.path_var = tk.StringVar(value=os.path.expanduser("~"))
        ttk.Entry(ctrl, textvariable=self.path_var, width=50).pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        ttk.Button(ctrl, text="📂 Browse", command=self._browse).pack(side=tk.LEFT, padx=2)
        self.scan_btn = ttk.Button(ctrl, text="▶ Scan", command=self._start_scan)
        self.scan_btn.pack(side=tk.LEFT, padx=2)
        self.stop_btn = ttk.Button(ctrl, text="⬛ Stop", command=self._stop_scan, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=2)

        # Stats
        stats = ttk.Frame(self)
        stats.pack(fill=tk.X, padx=10, pady=5)

        self.stat_files = ttk.Label(stats, text="Files: 0", font=("", 10))
        self.stat_files.pack(side=tk.LEFT, padx=10)
        self.stat_threats = ttk.Label(stats, text="Threats: 0", font=("", 10))
        self.stat_threats.pack(side=tk.LEFT, padx=10)
        self.scan_status = ttk.Label(stats, text="Ready", font=("", 10))
        self.scan_status.pack(side=tk.LEFT, padx=10)

        # Progress
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=10, pady=2)

        # Threats list
        threat_frame = ttk.LabelFrame(self, text="Detected Threats", padding=5)
        threat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.threat_tree = ttk.Treeview(threat_frame, columns=("threat", "file"),
                                         show="headings", selectmode="browse")
        self.threat_tree.heading("threat", text="Threat", anchor=tk.W)
        self.threat_tree.heading("file", text="File Path", anchor=tk.W)
        self.threat_tree.column("threat", width=200)
        self.threat_tree.column("file", width=400)
        scroll = ttk.Scrollbar(threat_frame, orient=tk.VERTICAL, command=self.threat_tree.yview)
        self.threat_tree.configure(yscrollcommand=scroll.set)
        self.threat_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Log
        log_frame = ttk.LabelFrame(self, text="Scan Log", padding=5)
        log_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        self.log = tk.Text(log_frame, height=5, wrap=tk.WORD, font=("Consolas", 9))
        self.log.pack(fill=tk.X)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text="📋 Export Report", command=self._export_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑 Clear Results", command=self._clear).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🌐 Remote Scan (Client)", command=self._remote_scan_dialog).pack(side=tk.LEFT, padx=2)

    def _browse(self):
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)

    def _log_msg(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _update_stats(self):
        self.stat_files.config(text=f"Files: {self._files_scanned}")
        self.stat_threats.config(text=f"Threats: {len(self._threats)}")

    def _start_scan(self):
        path = self.path_var.get()
        if not os.path.exists(path):
            messagebox.showwarning("eVirusTower", "Path does not exist.")
            return

        self._scanning = True
        self._threats = []
        self._files_scanned = 0
        self.threat_tree.delete(*self.threat_tree.get_children())

        self.scan_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress.start(10)
        self.scan_status.config(text="Scanning...")
        self._log_msg(f"Scan started: {path}")

        self._scan_thread = threading.Thread(target=self._scan_worker, args=(path,), daemon=True)
        self._scan_thread.start()
        self._poll_scan()

    def _stop_scan(self):
        self._scanning = False
        self._log_msg("Scan stopped by user.")

    def _poll_scan(self):
        if self._scan_thread and self._scan_thread.is_alive():
            self._update_stats()
            self.after(200, self._poll_scan)
        else:
            self._scan_complete()

    def _scan_worker(self, path):
        if os.path.isfile(path):
            self._check_file(path)
        else:
            for root, dirs, files in os.walk(path):
                if not self._scanning:
                    break
                for fname in files:
                    if not self._scanning:
                        break
                    fpath = os.path.join(root, fname)
                    self._check_file(fpath)

    def _check_file(self, filepath):
        self._files_scanned += 1
        try:
            size = os.path.getsize(filepath)
            if size > MAX_SCAN_SIZE or size == 0:
                return

            _, ext = os.path.splitext(filepath)

            with open(filepath, "rb") as f:
                data = f.read()

            # Hash check
            md5 = hashlib.md5(data).hexdigest()
            if md5 in KNOWN_MALWARE_HASHES:
                threat_name = KNOWN_MALWARE_HASHES[md5]
                self._threats.append({"file": filepath, "threat": threat_name})
                self._log_msg(f"⚠ THREAT: {threat_name} — {filepath}")
                return

            # Pattern check
            for pattern, name in SUSPICIOUS_PATTERNS:
                if pattern in data:
                    self._threats.append({"file": filepath, "threat": name})
                    self._log_msg(f"⚠ SUSPICIOUS: {name} — {filepath}")
                    return

        except (PermissionError, OSError):
            pass

    def _scan_complete(self):
        self._scanning = False
        self.progress.stop()
        self.scan_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self._update_stats()

        # Populate threat tree
        for t in self._threats:
            self.threat_tree.insert("", tk.END, values=(t["threat"], t["file"]))

        if self._threats:
            self.scan_status.config(text=f"⚠ {len(self._threats)} threat(s) found!")
            self._log_msg(f"Scan complete: {self._files_scanned} files, {len(self._threats)} threats")
        else:
            self.scan_status.config(text="✓ All clean — no threats detected")
            self._log_msg(f"Scan complete: {self._files_scanned} files, all clean")

    def _export_report(self):
        if not self._files_scanned:
            messagebox.showinfo("eVirusTower", "No scan results to export.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                             filetypes=[("Text", "*.txt")])
        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            f.write("eVirusTower Scan Report\n" + "=" * 50 + "\n")
            f.write(f"Files scanned: {self._files_scanned}\n")
            f.write(f"Threats: {len(self._threats)}\n\n")
            for t in self._threats:
                f.write(f"THREAT: {t['threat']}\n  File: {t['file']}\n\n")

        self._log_msg(f"Report saved: {path}")

    def _clear(self):
        self._threats = []
        self._files_scanned = 0
        self.threat_tree.delete(*self.threat_tree.get_children())
        self.log.delete("1.0", tk.END)
        self._update_stats()
        self.scan_status.config(text="Ready")

    def _connect_server(self):
        addr = self.server_var.get().strip()
        self._log_msg(f'Connecting to eVirusTowerServer: {addr}...')
        self.conn_status.config(text='\u25cf Connecting...', foreground='orange')
        import threading
        def try_connect():
            import socket
            try:
                host, port = addr.split(':') if ':' in addr else (addr, '9877')
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect((host, int(port)))
                s.close()
                self.after(0, lambda: self.conn_status.config(text='\u25cf Connected', foreground='green'))
                self.after(0, lambda: self._log_msg(f'Connected to {addr}'))
            except Exception as e:
                self.after(0, lambda: self.conn_status.config(text='\u25cf Failed', foreground='red'))
                self.after(0, lambda: self._log_msg(f'Server connection failed: {e}'))
        threading.Thread(target=try_connect, daemon=True).start()

    def on_close(self):
        self._scanning = False

    # ── Remote Client Mode ────────────────────────────────────────

    def _remote_scan_dialog(self):
        """Dialog to configure and run a remote scan via SSH."""
        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title("eVirusTower — Remote Scan (Client Mode)")
        dlg.geometry("500x350")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ttk.Label(dlg, text="🌐 Remote Scan via SSH", font=("", 14, "bold")).pack(pady=(15, 5))
        ttk.Label(dlg, text="Scan files on a remote machine over SSH.",
                  foreground="#888888").pack(pady=(0, 15))

        form = ttk.Frame(dlg, padding=10)
        form.pack(fill=tk.X, padx=20)

        ttk.Label(form, text="Host:").grid(row=0, column=0, sticky=tk.W, pady=4)
        host_var = tk.StringVar()
        ttk.Entry(form, textvariable=host_var, width=35).grid(row=0, column=1, pady=4, padx=(8, 0))

        ttk.Label(form, text="User:").grid(row=1, column=0, sticky=tk.W, pady=4)
        user_var = tk.StringVar(value=os.getenv("USER", os.getenv("USERNAME", "")))
        ttk.Entry(form, textvariable=user_var, width=35).grid(row=1, column=1, pady=4, padx=(8, 0))

        ttk.Label(form, text="Port:").grid(row=2, column=0, sticky=tk.W, pady=4)
        port_var = tk.StringVar(value="22")
        ttk.Entry(form, textvariable=port_var, width=35).grid(row=2, column=1, pady=4, padx=(8, 0))

        ttk.Label(form, text="Remote Path:").grid(row=3, column=0, sticky=tk.W, pady=4)
        path_var = tk.StringVar(value="/home")
        ttk.Entry(form, textvariable=path_var, width=35).grid(row=3, column=1, pady=4, padx=(8, 0))

        ttk.Label(form, text="Max Depth:").grid(row=4, column=0, sticky=tk.W, pady=4)
        depth_var = tk.StringVar(value="3")
        ttk.Entry(form, textvariable=depth_var, width=35).grid(row=4, column=1, pady=4, padx=(8, 0))

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=15)

        def start():
            host = host_var.get().strip()
            user = user_var.get().strip()
            port = port_var.get().strip() or "22"
            rpath = path_var.get().strip() or "/home"
            depth = depth_var.get().strip() or "3"
            if not host:
                messagebox.showwarning("eVirusTower", "Enter a host address.")
                return
            dlg.destroy()
            self._run_remote_scan(host, user, port, rpath, depth)

        ttk.Button(btn_frame, text="▶ Start Remote Scan", command=start).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=4)

    def _run_remote_scan(self, host, user, port, rpath, depth):
        """Run a scan on a remote machine by listing files via SSH and checking patterns."""
        import subprocess

        self._scanning = True
        self._threats = []
        self._files_scanned = 0
        self.threat_tree.delete(*self.threat_tree.get_children())
        self.scan_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress.start(10)
        self.scan_status.config(text=f"Remote scanning {user}@{host}:{rpath}...")
        self._log_msg(f"Remote scan: {user}@{host}:{rpath} (depth={depth})")

        def worker():
            try:
                # List remote files
                cmd = f'ssh -p {port} -o ConnectTimeout=10 -o StrictHostKeyChecking=no {user}@{host} "find {rpath} -maxdepth {depth} -type f -size -50M 2>/dev/null"'
                self._log_msg(f"$ {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

                if result.returncode != 0:
                    self._log_msg(f"SSH error: {result.stderr.strip()}")
                    return

                files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
                self._log_msg(f"Found {len(files)} files to check")

                for fpath in files:
                    if not self._scanning:
                        break
                    self._files_scanned += 1

                    # Check extension
                    _, ext = os.path.splitext(fpath)
                    if ext.lower() in SUSPICIOUS_EXTENSIONS:
                        self._threats.append({"file": f"[REMOTE] {fpath}", "threat": f"Suspicious extension: {ext}"})
                        self._log_msg(f"⚠ SUSPICIOUS EXT: {ext} — {fpath}")
                        continue

                    # For small text files, check content patterns
                    if ext.lower() in (".bat", ".cmd", ".vbs", ".ps1", ".sh", ".py"):
                        cat_cmd = f'ssh -p {port} {user}@{host} "cat \'{fpath}\'" 2>/dev/null'
                        try:
                            cat_result = subprocess.run(cat_cmd, shell=True, capture_output=True, timeout=10)
                            if cat_result.returncode == 0:
                                data = cat_result.stdout
                                # Hash check
                                md5 = hashlib.md5(data).hexdigest()
                                if md5 in KNOWN_MALWARE_HASHES:
                                    self._threats.append({"file": f"[REMOTE] {fpath}", "threat": KNOWN_MALWARE_HASHES[md5]})
                                    self._log_msg(f"⚠ HASH MATCH: {KNOWN_MALWARE_HASHES[md5]} — {fpath}")
                                    continue
                                # Pattern check
                                for pattern, name in SUSPICIOUS_PATTERNS:
                                    if pattern in data:
                                        self._threats.append({"file": f"[REMOTE] {fpath}", "threat": name})
                                        self._log_msg(f"⚠ PATTERN: {name} — {fpath}")
                                        break
                        except (subprocess.TimeoutExpired, Exception):
                            pass

            except subprocess.TimeoutExpired:
                self._log_msg("Remote scan timed out.")
            except Exception as e:
                self._log_msg(f"Error: {e}")

        self._scan_thread = threading.Thread(target=worker, daemon=True)
        self._scan_thread.start()
        self._poll_scan()
