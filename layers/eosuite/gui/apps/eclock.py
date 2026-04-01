# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eClock — Multi-city world clock with live time display.
Shows current time for configurable cities across timezones.
Uses only stdlib (datetime, math) — no pytz dependency.
"""
import math
import datetime
import tkinter as tk
from tkinter import ttk


TIMEZONE_DB = {
    "New York": ("EST/EDT", -5),
    "Los Angeles": ("PST/PDT", -8),
    "Chicago": ("CST/CDT", -6),
    "Denver": ("MST/MDT", -7),
    "Honolulu": ("HST", -10),
    "Anchorage": ("AKST", -9),
    "London": ("GMT/BST", 0),
    "Paris": ("CET/CEST", 1),
    "Berlin": ("CET/CEST", 1),
    "Madrid": ("CET/CEST", 1),
    "Rome": ("CET/CEST", 1),
    "Amsterdam": ("CET/CEST", 1),
    "Moscow": ("MSK", 3),
    "Istanbul": ("TRT", 3),
    "Dubai": ("GST", 4),
    "Mumbai": ("IST", 5.5),
    "Kolkata": ("IST", 5.5),
    "Bangkok": ("ICT", 7),
    "Singapore": ("SGT", 8),
    "Hong Kong": ("HKT", 8),
    "Beijing": ("CST", 8),
    "Shanghai": ("CST", 8),
    "Seoul": ("KST", 9),
    "Tokyo": ("JST", 9),
    "Sydney": ("AEST", 10),
    "Melbourne": ("AEST", 10),
    "Auckland": ("NZST", 12),
    "São Paulo": ("BRT", -3),
    "Buenos Aires": ("ART", -3),
    "Cairo": ("EET", 2),
    "Johannesburg": ("SAST", 2),
    "Nairobi": ("EAT", 3),
    "Reykjavik": ("GMT", 0),
    "Toronto": ("EST/EDT", -5),
    "Vancouver": ("PST/PDT", -8),
    "Mexico City": ("CST", -6),
    "Lima": ("PET", -5),
    "Jakarta": ("WIB", 7),
}

DEFAULT_CITIES = [
    "New York", "London", "Tokyo", "Sydney", "Mumbai",
    "Berlin", "São Paulo", "Los Angeles", "Dubai", "Singapore",
]


class EClock(ttk.Frame):
    """Multi-city world clock with live time display and analog clock."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._cities = list(DEFAULT_CITIES)
        self._after_id = None
        self._labels = {}
        self._selected_city = DEFAULT_CITIES[0]
        self._build()
        self._tick()

    def _build(self):
        c = self.app.theme.colors

        header = ttk.Frame(self, style="Toolbar.TFrame")
        header.pack(fill=tk.X)
        ttk.Label(header, text="🕐 eClock — World Clock",
                  style="Toolbar.TLabel",
                  font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=8, pady=4)

        ctrl = ttk.Frame(header)
        ctrl.pack(side=tk.RIGHT, padx=4, pady=2)
        self.add_var = tk.StringVar()
        available = sorted(TIMEZONE_DB.keys())
        self.add_combo = ttk.Combobox(ctrl, textvariable=self.add_var,
                                      values=available, width=16,
                                      state="readonly")
        self.add_combo.pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="➕ Add", style="Toolbar.TButton",
                   command=self._add_city).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="➖ Remove", style="Toolbar.TButton",
                   command=self._remove_city).pack(side=tk.LEFT, padx=2)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.clock_canvas = tk.Canvas(body, width=200, height=200,
                                      bg=c["bg"], highlightthickness=0)
        self.clock_canvas.pack(side=tk.RIGHT, padx=16, pady=16)

        cols = ("City", "Timezone", "Time", "Date")
        self.tree = ttk.Treeview(left, columns=cols, show="headings",
                                 selectmode="browse", height=12)
        for col in cols:
            self.tree.heading(col, text=col, anchor=tk.W)
        self.tree.column("City", width=140)
        self.tree.column("Timezone", width=90)
        self.tree.column("Time", width=100)
        self.tree.column("Date", width=120)

        scroll = ttk.Scrollbar(left, orient=tk.VERTICAL,
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _tick(self):
        self._update_times()
        self._draw_analog_clock()
        self._after_id = self.after(1000, self._tick)

    def _update_times(self):
        self.tree.delete(*self.tree.get_children())
        utc_now = datetime.datetime.utcnow()
        for city in self._cities:
            tz_label, offset = TIMEZONE_DB.get(city, ("?", 0))
            delta = datetime.timedelta(hours=offset)
            local = utc_now + delta
            time_str = local.strftime("%H:%M:%S")
            date_str = local.strftime("%a, %b %d")
            self.tree.insert(
                "", tk.END,
                values=(city, tz_label, time_str, date_str))

    def _draw_analog_clock(self):
        canvas = self.clock_canvas
        canvas.delete("all")
        w = canvas.winfo_width() or 200
        h = canvas.winfo_height() or 200
        cx, cy = w // 2, h // 2
        r = min(cx, cy) - 10

        c = self.app.theme.colors
        fg = c.get("fg", "#d4d4d4")
        accent = c.get("accent", "#2998ff")

        canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r, outline=fg, width=2)

        for i in range(12):
            angle = math.radians(i * 30 - 90)
            inner = r - 12
            outer = r - 2
            x1 = cx + inner * math.cos(angle)
            y1 = cy + inner * math.sin(angle)
            x2 = cx + outer * math.cos(angle)
            y2 = cy + outer * math.sin(angle)
            canvas.create_line(x1, y1, x2, y2, fill=fg, width=2)

        city = self._selected_city
        tz_label, offset = TIMEZONE_DB.get(city, ("?", 0))
        utc_now = datetime.datetime.utcnow()
        local = utc_now + datetime.timedelta(hours=offset)

        hour = local.hour % 12 + local.minute / 60.0
        minute = local.minute + local.second / 60.0
        second = local.second

        h_angle = math.radians(hour * 30 - 90)
        h_len = r * 0.5
        canvas.create_line(cx, cy,
                           cx + h_len * math.cos(h_angle),
                           cy + h_len * math.sin(h_angle),
                           fill=fg, width=4, capstyle=tk.ROUND)

        m_angle = math.radians(minute * 6 - 90)
        m_len = r * 0.7
        canvas.create_line(cx, cy,
                           cx + m_len * math.cos(m_angle),
                           cy + m_len * math.sin(m_angle),
                           fill=fg, width=2, capstyle=tk.ROUND)

        s_angle = math.radians(second * 6 - 90)
        s_len = r * 0.8
        canvas.create_line(cx, cy,
                           cx + s_len * math.cos(s_angle),
                           cy + s_len * math.sin(s_angle),
                           fill=accent, width=1)

        canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4,
                           fill=accent, outline="")

        canvas.create_text(cx, cy + r + 6, text=city,
                           font=("Segoe UI", 9, "bold"), fill=fg,
                           anchor=tk.S)

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if sel:
            item = self.tree.item(sel[0])
            self._selected_city = item["values"][0]

    def _add_city(self):
        city = self.add_var.get()
        if not city:
            return
        if city in self._cities:
            return
        if city not in TIMEZONE_DB:
            return
        self._cities.append(city)
        self._update_times()

    def _remove_city(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        city = item["values"][0]
        if city in self._cities and len(self._cities) > 1:
            self._cities.remove(city)
            if self._selected_city == city:
                self._selected_city = self._cities[0]
            self._update_times()

    def on_close(self):
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    @staticmethod
    def get_city_time(city):
        if city not in TIMEZONE_DB:
            return None
        _, offset = TIMEZONE_DB[city]
        utc_now = datetime.datetime.utcnow()
        local = utc_now + datetime.timedelta(hours=offset)
        return local

    @staticmethod
    def fmt_time(dt):
        return dt.strftime("%H:%M:%S")

    @staticmethod
    def fmt_date(dt):
        return dt.strftime("%a, %b %d")
