# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eTimer — Stopwatch + countdown with large display and lap times.
"""
import time
import tkinter as tk
from tkinter import ttk


class ETimer(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._sw_running = False
        self._sw_start = 0
        self._sw_elapsed = 0
        self._cd_running = False
        self._cd_remaining = 0
        self._build()

    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        sw = ttk.Frame(nb)
        nb.add(sw, text="⏱ Stopwatch")
        self._build_stopwatch(sw)

        cd = ttk.Frame(nb)
        nb.add(cd, text="⏳ Countdown")
        self._build_countdown(cd)

    def _build_stopwatch(self, parent):
        self.sw_display = ttk.Label(parent, text="00:00:00.000",
                                    font=("Consolas", 48), anchor=tk.CENTER)
        self.sw_display.pack(pady=40)

        bf = ttk.Frame(parent)
        bf.pack()
        ttk.Button(bf, text="▶ Start", command=self._sw_start_cmd).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text="⏸ Stop", command=self._sw_stop).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text="↺ Reset", command=self._sw_reset).pack(side=tk.LEFT, padx=6)

        self.lap_list = tk.Listbox(parent, font=("Consolas", 11), height=6)
        self.lap_list.pack(fill=tk.X, padx=40, pady=20)
        ttk.Button(parent, text="Lap", command=self._sw_lap).pack()

    def _build_countdown(self, parent):
        inp = ttk.Frame(parent)
        inp.pack(pady=20)
        ttk.Label(inp, text="Minutes:", font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=4)
        self.cd_min = tk.StringVar(value="5")
        ttk.Entry(inp, textvariable=self.cd_min, width=6, font=("Consolas", 14)).pack(side=tk.LEFT, padx=4)
        ttk.Label(inp, text="Seconds:", font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=4)
        self.cd_sec = tk.StringVar(value="0")
        ttk.Entry(inp, textvariable=self.cd_sec, width=6, font=("Consolas", 14)).pack(side=tk.LEFT, padx=4)

        self.cd_display = ttk.Label(parent, text="05:00", font=("Consolas", 56), anchor=tk.CENTER)
        self.cd_display.pack(pady=20)

        self.cd_progress = ttk.Progressbar(parent, length=400, mode="determinate")
        self.cd_progress.pack(pady=10)

        bf = ttk.Frame(parent)
        bf.pack(pady=10)
        ttk.Button(bf, text="▶ Start", command=self._cd_start).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text="⏸ Pause", command=self._cd_pause).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text="↺ Reset", command=self._cd_reset).pack(side=tk.LEFT, padx=6)

    def _sw_start_cmd(self):
        if not self._sw_running:
            self._sw_running = True
            self._sw_start = time.time() - self._sw_elapsed
            self._sw_tick()

    def _sw_stop(self):
        self._sw_running = False

    def _sw_reset(self):
        self._sw_running = False
        self._sw_elapsed = 0
        self.sw_display.config(text="00:00:00.000")
        self.lap_list.delete(0, tk.END)

    def _sw_tick(self):
        if self._sw_running:
            self._sw_elapsed = time.time() - self._sw_start
            self.sw_display.config(text=self._fmt(self._sw_elapsed))
            self.after(33, self._sw_tick)

    def _sw_lap(self):
        if self._sw_elapsed > 0:
            n = self.lap_list.size() + 1
            self.lap_list.insert(tk.END, f"  Lap {n:>3}:  {self._fmt(self._sw_elapsed)}")

    def _cd_start(self):
        if not self._cd_running:
            if self._cd_remaining <= 0:
                try:
                    self._cd_remaining = int(self.cd_min.get()) * 60 + int(self.cd_sec.get())
                    self._cd_total = self._cd_remaining
                except ValueError:
                    return
            self._cd_running = True
            self._cd_tick()

    def _cd_pause(self):
        self._cd_running = False

    def _cd_reset(self):
        self._cd_running = False
        self._cd_remaining = 0
        self.cd_display.config(text="05:00")
        self.cd_progress["value"] = 0

    def _cd_tick(self):
        if self._cd_running and self._cd_remaining > 0:
            self._cd_remaining -= 1
            m, s = divmod(self._cd_remaining, 60)
            self.cd_display.config(text=f"{m:02d}:{s:02d}")
            if hasattr(self, "_cd_total") and self._cd_total > 0:
                self.cd_progress["value"] = (self._cd_total - self._cd_remaining) / self._cd_total * 100
            self.after(1000, self._cd_tick)
        elif self._cd_remaining <= 0:
            self._cd_running = False
            self.cd_display.config(text="00:00")
            self.cd_progress["value"] = 100
            self.bell()

    @staticmethod
    def _fmt(secs):
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        s = int(secs % 60)
        ms = int((secs % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
