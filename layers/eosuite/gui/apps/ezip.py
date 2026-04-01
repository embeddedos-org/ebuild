# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eZip — Archive manager with file list and extract/compress buttons.
"""
import os
import zipfile
import tarfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class EZip(ttk.Frame):
    """Archive manager supporting zip and tar files."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._archive_path = None
        self._build()

    def _build(self):
        # Toolbar
        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(fill=tk.X)

        btns = [
            ("📂 Open Archive", self._open_archive),
            ("📦 Create Zip", self._create_zip),
            ("📤 Extract All", self._extract_all),
            ("➕ Add Files", self._add_files),
        ]
        for text, cmd in btns:
            ttk.Button(toolbar, text=text, style="Toolbar.TButton",
                       command=cmd).pack(side=tk.LEFT, padx=2, pady=2)

        self.info_label = ttk.Label(toolbar, text="No archive loaded",
                                    style="Toolbar.TLabel")
        self.info_label.pack(side=tk.RIGHT, padx=8)

        # File list
        cols = ("Name", "Size", "Compressed", "Type")
        self.tree = ttk.Treeview(self, columns=cols, show="headings",
                                 selectmode="extended")
        for col in cols:
            self.tree.heading(col, text=col)
        self.tree.column("Name", width=300)
        self.tree.column("Size", width=100)
        self.tree.column("Compressed", width=100)
        self.tree.column("Type", width=80)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL,
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

    def _open_archive(self):
        path = filedialog.askopenfilename(
            filetypes=[("Archives", "*.zip *.tar *.tar.gz *.tgz *.tar.bz2"),
                       ("Zip files", "*.zip"),
                       ("Tar files", "*.tar *.tar.gz *.tgz"),
                       ("All files", "*.*")])
        if not path:
            return

        self._archive_path = path
        self.tree.delete(*self.tree.get_children())

        try:
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path, "r") as zf:
                    for info in zf.infolist():
                        self.tree.insert("", tk.END, values=(
                            info.filename,
                            f"{info.file_size:,}",
                            f"{info.compress_size:,}",
                            "Dir" if info.is_dir() else "File"))
                self.info_label.config(text=f"ZIP: {os.path.basename(path)}")
            elif tarfile.is_tarfile(path):
                with tarfile.open(path, "r:*") as tf:
                    for member in tf.getmembers():
                        self.tree.insert("", tk.END, values=(
                            member.name,
                            f"{member.size:,}",
                            "—",
                            "Dir" if member.isdir() else "File"))
                self.info_label.config(text=f"TAR: {os.path.basename(path)}")
            else:
                messagebox.showwarning("Error", "Unsupported archive format.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _extract_all(self):
        if not self._archive_path:
            messagebox.showinfo("Info", "Open an archive first.")
            return
        dest = filedialog.askdirectory(title="Extract to")
        if not dest:
            return
        try:
            if zipfile.is_zipfile(self._archive_path):
                with zipfile.ZipFile(self._archive_path, "r") as zf:
                    zf.extractall(dest)
            elif tarfile.is_tarfile(self._archive_path):
                with tarfile.open(self._archive_path, "r:*") as tf:
                    tf.extractall(dest)
            messagebox.showinfo("Done", f"Extracted to {dest}")
            self.app.set_status(f"Extracted to {dest}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _create_zip(self):
        files = filedialog.askopenfilenames(title="Select files to compress")
        if not files:
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("Zip files", "*.zip")])
        if not dest:
            return
        try:
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    zf.write(f, os.path.basename(f))
            messagebox.showinfo("Done", f"Created {dest}")
            self.app.set_status(f"Created archive: {dest}")
            # Reload
            self._archive_path = dest
            self._open_archive_file(dest)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _open_archive_file(self, path):
        self._archive_path = path
        self.tree.delete(*self.tree.get_children())
        try:
            with zipfile.ZipFile(path, "r") as zf:
                for info in zf.infolist():
                    self.tree.insert("", tk.END, values=(
                        info.filename,
                        f"{info.file_size:,}",
                        f"{info.compress_size:,}",
                        "Dir" if info.is_dir() else "File"))
            self.info_label.config(text=f"ZIP: {os.path.basename(path)}")
        except Exception:
            pass

    def _add_files(self):
        if not self._archive_path or not zipfile.is_zipfile(self._archive_path):
            messagebox.showinfo("Info", "Open a ZIP archive first.")
            return
        files = filedialog.askopenfilenames(title="Select files to add")
        if not files:
            return
        try:
            with zipfile.ZipFile(self._archive_path, "a") as zf:
                for f in files:
                    zf.write(f, os.path.basename(f))
            self._open_archive_file(self._archive_path)
            self.app.set_status("Files added to archive")
        except Exception as e:
            messagebox.showerror("Error", str(e))
