# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Dice — Dice roller with multiple dice, history, and statistics.
"""
import random
import tkinter as tk
from tkinter import ttk


DICE_FACES = {
    1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅",
}


class DiceRoller(ttk.Frame):
    """Dice roller with configurable dice count and roll history."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._history = []
        self._total_rolls = 0
        self._sum_total = 0
        self._build()

    def _build(self):
        c = self.app.theme.colors

        top = ttk.Frame(self, style="Toolbar.TFrame")
        top.pack(fill=tk.X)
        ttk.Label(top, text="🎲 Dice Roller", style="Toolbar.TLabel",
                  font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=8, pady=4)
        ttk.Button(top, text="Clear History", style="Toolbar.TButton",
                   command=self._clear).pack(side=tk.RIGHT, padx=4, pady=2)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        ctrl = ttk.Frame(body)
        ctrl.pack(pady=8)

        ttk.Label(ctrl, text="Number of dice:",
                  font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=4)
        self.dice_var = tk.IntVar(value=2)
        ttk.Spinbox(ctrl, from_=1, to=10, textvariable=self.dice_var,
                    width=4, font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=4)

        ttk.Label(ctrl, text="Sides:",
                  font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(16, 4))
        self.sides_var = tk.IntVar(value=6)
        ttk.Combobox(ctrl, textvariable=self.sides_var,
                     values=[4, 6, 8, 10, 12, 20, 100],
                     state="readonly", width=4).pack(side=tk.LEFT, padx=4)

        roll_btn = ttk.Button(body, text="🎲  Roll!",
                              command=self._roll)
        roll_btn.pack(pady=12)

        self.result_canvas = tk.Canvas(body, height=100, bg=c["bg"],
                                       highlightthickness=0)
        self.result_canvas.pack(fill=tk.X, pady=4)

        self.total_label = ttk.Label(body, text="",
                                     font=("Segoe UI", 16, "bold"))
        self.total_label.pack(pady=4)

        stats_frame = ttk.LabelFrame(body, text="Statistics", padding=8)
        stats_frame.pack(fill=tk.X, pady=8)
        self.stats_label = ttk.Label(stats_frame, text="No rolls yet",
                                     font=("Segoe UI", 10))
        self.stats_label.pack(anchor=tk.W)

        hist_frame = ttk.LabelFrame(body, text="Roll History", padding=8)
        hist_frame.pack(fill=tk.BOTH, expand=True, pady=4)
        self.history_text = tk.Text(hist_frame, height=8,
                                    font=("Consolas", 10),
                                    bg=c["terminal_bg"], fg=c["terminal_fg"],
                                    state=tk.DISABLED, relief=tk.FLAT)
        self.history_text.pack(fill=tk.BOTH, expand=True)

    def _roll(self):
        n = self.dice_var.get()
        sides = self.sides_var.get()
        results = [random.randint(1, sides) for _ in range(n)]
        total = sum(results)

        self._total_rolls += 1
        self._sum_total += total
        self._history.append((n, sides, results, total))

        self._draw_dice(results, sides)
        self.total_label.config(text=f"Total: {total}")

        avg = self._sum_total / self._total_rolls
        self.stats_label.config(
            text=f"Rolls: {self._total_rolls}  |  "
                 f"Sum: {self._sum_total}  |  "
                 f"Average: {avg:.1f}")

        self.history_text.config(state=tk.NORMAL)
        self.history_text.insert(
            "1.0",
            f"Roll #{self._total_rolls}: {n}d{sides} = "
            f"{results} = {total}\n")
        self.history_text.config(state=tk.DISABLED)

    def _draw_dice(self, results, sides):
        canvas = self.result_canvas
        canvas.delete("all")
        w = canvas.winfo_width() or 400
        n = len(results)
        size = min(60, (w - 20) // max(n, 1))
        total_w = n * (size + 8)
        start_x = (w - total_w) // 2

        for i, val in enumerate(results):
            x = start_x + i * (size + 8)
            y = 20
            canvas.create_rectangle(
                x, y, x + size, y + size,
                fill="#ffffff", outline="#333333", width=2)
            if sides == 6 and val in DICE_FACES:
                text = DICE_FACES[val]
                font = ("Segoe UI", size // 2)
            else:
                text = str(val)
                font = ("Segoe UI", size // 3, "bold")
            canvas.create_text(
                x + size // 2, y + size // 2,
                text=text, font=font, fill="#111111")

    def _clear(self):
        self._history.clear()
        self._total_rolls = 0
        self._sum_total = 0
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)
        self.history_text.config(state=tk.DISABLED)
        self.total_label.config(text="")
        self.stats_label.config(text="No rolls yet")
        self.result_canvas.delete("all")

    def on_close(self):
        pass
