# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite ePlay — Media player with play/pause/stop controls.
"""
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog


class EPlay(ttk.Frame):
    """Simple media player with controls."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._filepath = None
        self._process = None
        self._playing = False
        self._build()

    def _build(self):
        c = self.app.theme.colors

        container = ttk.Frame(self)
        container.place(relx=0.5, rely=0.4, anchor=tk.CENTER)

        # Album art placeholder
        self.art_canvas = tk.Canvas(container, width=200, height=200,
                                    bg="#333333", highlightthickness=0)
        self.art_canvas.pack(pady=16)
        self.art_canvas.create_text(100, 90, text="🎵",
                                    font=("Segoe UI", 64), fill="#666666")
        self.art_canvas.create_text(100, 160, text="No file loaded",
                                    font=("Segoe UI", 10), fill="#888888")

        # File info
        self.title_label = ttk.Label(
            container, text="ePlay Media Player",
            font=("Segoe UI", 16, "bold"))
        self.title_label.pack(pady=(8, 2))

        self.file_label = ttk.Label(
            container, text="Open a media file to begin",
            font=("Segoe UI", 10), foreground="#888888")
        self.file_label.pack(pady=(0, 16))

        # Progress bar
        self.progress = ttk.Progressbar(container, length=400,
                                        mode="indeterminate")
        self.progress.pack(pady=8)

        # Controls
        controls = ttk.Frame(container)
        controls.pack(pady=16)

        control_btns = [
            ("⏮", self._prev),
            ("⏪", self._rewind),
            ("▶", self._play_pause),
            ("⏩", self._forward),
            ("⏭", self._next),
            ("⏹", self._stop),
        ]
        for text, cmd in control_btns:
            tk.Button(controls, text=text, font=("Segoe UI", 18),
                      bg=c["toolbar_bg"], fg=c["fg"], relief=tk.FLAT,
                      width=3, command=cmd).pack(side=tk.LEFT, padx=4)

        # Volume
        vol_frame = ttk.Frame(container)
        vol_frame.pack(pady=8)
        ttk.Label(vol_frame, text="🔊 Volume:").pack(side=tk.LEFT, padx=4)
        self.volume_var = tk.IntVar(value=75)
        ttk.Scale(vol_frame, from_=0, to=100, variable=self.volume_var,
                  orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT, padx=4)

        # Open file button
        ttk.Button(container, text="📂 Open Media File",
                   command=self._open_file).pack(pady=16)

        # Playlist
        ttk.Label(container, text="Playlist:",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, padx=20)
        self.playlist = tk.Listbox(container, font=("Segoe UI", 10),
                                   height=5, width=50)
        self.playlist.pack(padx=20, pady=4)
        self.playlist.bind("<Double-1>", self._play_selected)

    def _open_file(self):
        paths = filedialog.askopenfilenames(
            filetypes=[
                ("Media files", "*.mp3 *.wav *.ogg *.flac *.mp4 *.avi *.mkv"),
                ("Audio files", "*.mp3 *.wav *.ogg *.flac *.aac"),
                ("Video files", "*.mp4 *.avi *.mkv *.mov"),
                ("All files", "*.*")])
        if paths:
            for p in paths:
                self.playlist.insert(tk.END, os.path.basename(p))
            self._filepath = paths[0]
            self.title_label.config(text=os.path.basename(paths[0]))
            self.file_label.config(text=paths[0])

    def _play_pause(self):
        if not self._filepath:
            self._open_file()
            return

        if self._playing:
            self._playing = False
            self.progress.stop()
            self.app.set_status("ePlay: Paused")
        else:
            self._playing = True
            self.progress.start(20)
            self.app.set_status(f"ePlay: Playing {os.path.basename(self._filepath)}")
            # Launch system default player
            try:
                if sys.platform == "win32":
                    os.startfile(self._filepath)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", self._filepath])
                else:
                    subprocess.Popen(["xdg-open", self._filepath])
            except Exception as e:
                self.app.set_status(f"ePlay Error: {e}")

    def _stop(self):
        self._playing = False
        self.progress.stop()
        self.progress["value"] = 0
        self.app.set_status("ePlay: Stopped")

    def _rewind(self):
        self.app.set_status("ePlay: Rewind")

    def _forward(self):
        self.app.set_status("ePlay: Forward")

    def _prev(self):
        idx = self.playlist.curselection()
        if idx and idx[0] > 0:
            self.playlist.selection_clear(0, tk.END)
            self.playlist.selection_set(idx[0] - 1)

    def _next(self):
        idx = self.playlist.curselection()
        if idx and idx[0] < self.playlist.size() - 1:
            self.playlist.selection_clear(0, tk.END)
            self.playlist.selection_set(idx[0] + 1)

    def _play_selected(self, _event=None):
        idx = self.playlist.curselection()
        if idx:
            name = self.playlist.get(idx[0])
            self.title_label.config(text=name)
            self.app.set_status(f"ePlay: Selected {name}")
