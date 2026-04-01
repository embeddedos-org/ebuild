# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
eFTP — FileZilla-style FTP/SFTP file transfer client.
Dual-pane layout: local files (left) ↔ remote files (right).
"""
import os
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class EFTP(ttk.Frame):
    """FileZilla-style FTP/SFTP client tab."""

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self.remote_host = ""
        self.remote_user = ""
        self.remote_port = 22
        self.local_path = os.path.expanduser("~")
        self.remote_path = "/"
        self._build()

    def _build(self):
        # Connection bar
        conn_frame = ttk.LabelFrame(self, text="Connection", padding=5)
        conn_frame.pack(fill=tk.X, padx=5, pady=(5, 2))

        ttk.Label(conn_frame, text="Host:").pack(side=tk.LEFT, padx=2)
        self.host_var = tk.StringVar()
        ttk.Entry(conn_frame, textvariable=self.host_var, width=20).pack(side=tk.LEFT, padx=2)

        ttk.Label(conn_frame, text="User:").pack(side=tk.LEFT, padx=2)
        self.user_var = tk.StringVar()
        ttk.Entry(conn_frame, textvariable=self.user_var, width=12).pack(side=tk.LEFT, padx=2)

        ttk.Label(conn_frame, text="Port:").pack(side=tk.LEFT, padx=2)
        self.port_var = tk.StringVar(value="22")
        ttk.Entry(conn_frame, textvariable=self.port_var, width=5).pack(side=tk.LEFT, padx=2)

        ttk.Label(conn_frame, text="Password:").pack(side=tk.LEFT, padx=2)
        self.pass_var = tk.StringVar()
        ttk.Entry(conn_frame, textvariable=self.pass_var, width=12, show="•").pack(side=tk.LEFT, padx=2)

        ttk.Label(conn_frame, text="Protocol:").pack(side=tk.LEFT, padx=2)
        self.proto_var = tk.StringVar(value="SFTP")
        ttk.Combobox(conn_frame, textvariable=self.proto_var,
                     values=["SFTP", "FTP", "SCP"], width=6, state="readonly").pack(side=tk.LEFT, padx=2)

        ttk.Button(conn_frame, text="⚡ Connect", command=self._connect).pack(side=tk.LEFT, padx=5)
        ttk.Button(conn_frame, text="✕ Disconnect", command=self._disconnect).pack(side=tk.LEFT, padx=2)

        self.conn_status = ttk.Label(conn_frame, text="● Disconnected", foreground="red")
        self.conn_status.pack(side=tk.RIGHT, padx=5)

        # Log area (collapsible)
        self.log_frame = ttk.LabelFrame(self, text="Transfer Log", padding=2)
        self.log_frame.pack(fill=tk.X, padx=5, pady=2)
        self.log_text = tk.Text(self.log_frame, height=3, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill=tk.X)
        self._log("Ready. Enter host and click Connect.")

        # Dual pane: local | remote
        pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left pane: local files
        left = ttk.Frame(pane)
        pane.add(left, weight=1)

        left_header = ttk.Frame(left)
        left_header.pack(fill=tk.X)
        ttk.Label(left_header, text="📁 Local Files", font=("", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_header, text="📂", width=3, command=self._browse_local).pack(side=tk.RIGHT, padx=2)
        ttk.Button(left_header, text="⬆", width=3, command=self._local_up).pack(side=tk.RIGHT, padx=2)

        self.local_path_var = tk.StringVar(value=self.local_path)
        ttk.Entry(left, textvariable=self.local_path_var).pack(fill=tk.X, padx=5, pady=2)
        self.local_path_var.trace_add("write", lambda *a: None)

        self.local_tree = ttk.Treeview(left, columns=("size", "modified"), show="tree headings", selectmode="extended")
        self.local_tree.heading("#0", text="Name", anchor=tk.W)
        self.local_tree.heading("size", text="Size", anchor=tk.E)
        self.local_tree.heading("modified", text="Modified", anchor=tk.W)
        self.local_tree.column("#0", width=200)
        self.local_tree.column("size", width=80, anchor=tk.E)
        self.local_tree.column("modified", width=140)

        local_scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.local_tree.yview)
        self.local_tree.configure(yscrollcommand=local_scroll.set)
        self.local_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        local_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.local_tree.bind("<Double-1>", self._local_dblclick)

        # Center transfer buttons
        center = ttk.Frame(pane, width=60)
        pane.add(center, weight=0)

        spacer_top = ttk.Frame(center)
        spacer_top.pack(expand=True)
        ttk.Button(center, text="  ▶▶  \nUpload", command=self._upload, width=8).pack(pady=5)
        ttk.Button(center, text="  ◀◀  \nDownload", command=self._download, width=8).pack(pady=5)
        ttk.Button(center, text="🗑\nDelete", command=self._delete_selected, width=8).pack(pady=5)
        ttk.Button(center, text="📁\nNew Dir", command=self._mkdir_remote, width=8).pack(pady=5)
        spacer_bot = ttk.Frame(center)
        spacer_bot.pack(expand=True)

        # Right pane: remote files
        right = ttk.Frame(pane)
        pane.add(right, weight=1)

        right_header = ttk.Frame(right)
        right_header.pack(fill=tk.X)
        ttk.Label(right_header, text="🌐 Remote Files", font=("", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_header, text="🔄", width=3, command=self._refresh_remote).pack(side=tk.RIGHT, padx=2)
        ttk.Button(right_header, text="⬆", width=3, command=self._remote_up).pack(side=tk.RIGHT, padx=2)

        self.remote_path_var = tk.StringVar(value="/")
        ttk.Entry(right, textvariable=self.remote_path_var).pack(fill=tk.X, padx=5, pady=2)

        self.remote_tree = ttk.Treeview(right, columns=("size", "perms"), show="tree headings", selectmode="extended")
        self.remote_tree.heading("#0", text="Name", anchor=tk.W)
        self.remote_tree.heading("size", text="Size", anchor=tk.E)
        self.remote_tree.heading("perms", text="Permissions", anchor=tk.W)
        self.remote_tree.column("#0", width=200)
        self.remote_tree.column("size", width=80, anchor=tk.E)
        self.remote_tree.column("perms", width=100)

        remote_scroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.remote_tree.yview)
        self.remote_tree.configure(yscrollcommand=remote_scroll.set)
        self.remote_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        remote_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.remote_tree.bind("<Double-1>", self._remote_dblclick)

        # Status bar
        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, padx=5, pady=(0, 5))

        # Load local files
        self._refresh_local()

    def _log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def _format_size(self, size):
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def _refresh_local(self):
        self.local_tree.delete(*self.local_tree.get_children())
        path = self.local_path_var.get()
        if not os.path.isdir(path):
            return

        try:
            entries = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            for name in entries:
                full = os.path.join(path, name)
                try:
                    stat = os.stat(full)
                    is_dir = os.path.isdir(full)
                    icon = "📁" if is_dir else "📄"
                    size = "" if is_dir else self._format_size(stat.st_size)
                    import time
                    modified = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
                    self.local_tree.insert("", tk.END, text=f"{icon} {name}", values=(size, modified),
                                          tags=("dir",) if is_dir else ("file",))
                except (PermissionError, OSError):
                    self.local_tree.insert("", tk.END, text=f"⚠ {name}", values=("", ""))
        except PermissionError:
            self._log(f"Permission denied: {path}")

    def _local_dblclick(self, event):
        sel = self.local_tree.selection()
        if not sel:
            return
        item = self.local_tree.item(sel[0])
        name = item["text"].split(" ", 1)[-1] if " " in item["text"] else item["text"]
        new_path = os.path.join(self.local_path_var.get(), name)
        if os.path.isdir(new_path):
            self.local_path_var.set(os.path.normpath(new_path))
            self._refresh_local()

    def _local_up(self):
        current = self.local_path_var.get()
        parent = os.path.dirname(current)
        if parent and parent != current:
            self.local_path_var.set(parent)
            self._refresh_local()

    def _browse_local(self):
        path = filedialog.askdirectory(initialdir=self.local_path_var.get())
        if path:
            self.local_path_var.set(path)
            self._refresh_local()

    def _connect(self):
        host = self.host_var.get().strip()
        user = self.user_var.get().strip()
        port = self.port_var.get().strip()

        if not host:
            messagebox.showwarning("eFTP", "Enter a host address.")
            return

        self.remote_host = host
        self.remote_user = user or os.getlogin()
        self.remote_port = int(port) if port.isdigit() else 22

        self.conn_status.config(text="● Connecting...", foreground="orange")
        self._log(f"Connecting to {self.remote_user}@{self.remote_host}:{self.remote_port}...")
        self.status_var.set(f"Connecting to {self.remote_host}...")
        self.update_idletasks()

        self.remote_path_var.set("/home/" + self.remote_user)
        self._refresh_remote()

    def _disconnect(self):
        self.remote_tree.delete(*self.remote_tree.get_children())
        self.conn_status.config(text="● Disconnected", foreground="red")
        self.status_var.set("Disconnected")
        self._log("Disconnected.")

    def _refresh_remote(self):
        self.remote_tree.delete(*self.remote_tree.get_children())
        rpath = self.remote_path_var.get()

        if not self.remote_host:
            self._log("Not connected.")
            return

        cmd = f'ssh -p {self.remote_port} {self.remote_user}@{self.remote_host} "ls -la {rpath}" 2>&1'
        self._log(f"$ {cmd}")

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            output = result.stdout.strip()

            if result.returncode != 0:
                self.conn_status.config(text="● Error", foreground="red")
                self._log(f"Error: {result.stderr.strip()}")
                self.status_var.set("Connection failed")
                return

            self.conn_status.config(text=f"● Connected ({self.remote_host})", foreground="green")
            self.status_var.set(f"Connected: {self.remote_user}@{self.remote_host}")

            for line in output.split("\n"):
                parts = line.split(None, 8)
                if len(parts) < 9 or parts[0] == "total":
                    continue
                perms = parts[0]
                size = parts[4]
                name = parts[8]
                if name in (".", ".."):
                    continue

                is_dir = perms.startswith("d")
                icon = "📁" if is_dir else "📄"
                display_size = "" if is_dir else self._format_size(int(size)) if size.isdigit() else size

                self.remote_tree.insert("", tk.END, text=f"{icon} {name}",
                                        values=(display_size, perms),
                                        tags=("dir",) if is_dir else ("file",))

        except subprocess.TimeoutExpired:
            self._log("Connection timed out.")
            self.conn_status.config(text="● Timeout", foreground="red")
        except Exception as e:
            self._log(f"Error: {e}")
            self.conn_status.config(text="● Error", foreground="red")

    def _remote_dblclick(self, event):
        sel = self.remote_tree.selection()
        if not sel:
            return
        item = self.remote_tree.item(sel[0])
        name = item["text"].split(" ", 1)[-1]
        tags = item.get("tags", ())
        if "dir" in tags:
            rpath = self.remote_path_var.get().rstrip("/") + "/" + name
            self.remote_path_var.set(rpath)
            self._refresh_remote()

    def _remote_up(self):
        rpath = self.remote_path_var.get()
        parent = "/".join(rpath.rstrip("/").split("/")[:-1]) or "/"
        self.remote_path_var.set(parent)
        self._refresh_remote()

    def _get_selected_names(self, tree):
        names = []
        for sel in tree.selection():
            item = tree.item(sel)
            name = item["text"].split(" ", 1)[-1] if " " in item["text"] else item["text"]
            names.append(name)
        return names

    def _upload(self):
        names = self._get_selected_names(self.local_tree)
        if not names:
            messagebox.showinfo("eFTP", "Select local files to upload.")
            return
        if not self.remote_host:
            messagebox.showwarning("eFTP", "Connect to a server first.")
            return

        rpath = self.remote_path_var.get()
        lpath = self.local_path_var.get()

        for name in names:
            local_file = os.path.join(lpath, name)
            remote_dest = f"{self.remote_user}@{self.remote_host}:{rpath}/{name}"
            cmd = f'scp -P {self.remote_port} "{local_file}" "{remote_dest}" 2>&1'
            self._log(f"Uploading: {name}")
            self.status_var.set(f"Uploading: {name}...")
            self.update_idletasks()

            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    self._log(f"  ✓ {name} uploaded")
                else:
                    self._log(f"  ✗ {name}: {result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                self._log(f"  ✗ {name}: timeout")

        self._refresh_remote()
        self.status_var.set("Upload complete")

    def _download(self):
        names = self._get_selected_names(self.remote_tree)
        if not names:
            messagebox.showinfo("eFTP", "Select remote files to download.")
            return

        rpath = self.remote_path_var.get()
        lpath = self.local_path_var.get()

        for name in names:
            remote_file = f"{self.remote_user}@{self.remote_host}:{rpath}/{name}"
            local_dest = os.path.join(lpath, name)
            cmd = f'scp -P {self.remote_port} "{remote_file}" "{local_dest}" 2>&1'
            self._log(f"Downloading: {name}")
            self.status_var.set(f"Downloading: {name}...")
            self.update_idletasks()

            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    self._log(f"  ✓ {name} downloaded")
                else:
                    self._log(f"  ✗ {name}: {result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                self._log(f"  ✗ {name}: timeout")

        self._refresh_local()
        self.status_var.set("Download complete")

    def _delete_selected(self):
        names = self._get_selected_names(self.remote_tree)
        if not names:
            messagebox.showinfo("eFTP", "Select remote files to delete.")
            return
        if not messagebox.askyesno("eFTP", f"Delete {len(names)} remote file(s)?"):
            return

        rpath = self.remote_path_var.get()
        for name in names:
            cmd = f'ssh -p {self.remote_port} {self.remote_user}@{self.remote_host} "rm -rf {rpath}/{name}" 2>&1'
            self._log(f"Deleting: {name}")
            subprocess.run(cmd, shell=True, capture_output=True, timeout=15)

        self._refresh_remote()

    def _mkdir_remote(self):
        if not self.remote_host:
            return
        from tkinter.simpledialog import askstring
        name = askstring("New Directory", "Directory name:")
        if not name:
            return
        rpath = self.remote_path_var.get()
        cmd = f'ssh -p {self.remote_port} {self.remote_user}@{self.remote_host} "mkdir -p {rpath}/{name}" 2>&1'
        self._log(f"Creating directory: {name}")
        subprocess.run(cmd, shell=True, capture_output=True, timeout=15)
        self._refresh_remote()

    def on_close(self):
        pass
