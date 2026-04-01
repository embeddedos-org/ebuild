# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Minesweeper — Classic mine-clearing puzzle game.
"""
import random
import tkinter as tk
from tkinter import ttk

DIFFICULTIES = {
    "Easy": (9, 9, 10),
    "Medium": (16, 16, 40),
    "Hard": (30, 16, 99),
}

CELL_SIZE = 28
NUM_COLORS = {
    1: "#0000ff", 2: "#008000", 3: "#ff0000", 4: "#000080",
    5: "#800000", 6: "#008080", 7: "#000000", 8: "#808080",
}


class Minesweeper(ttk.Frame):
    """Classic Minesweeper game."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._width, self._height, self._mines_count = DIFFICULTIES["Easy"]
        self._grid = []
        self._revealed = []
        self._flagged = []
        self._game_over = False
        self._first_click = True
        self._mines_remaining = self._mines_count
        self._build()
        self._new_game()

    def _build(self):
        top = ttk.Frame(self, style="Toolbar.TFrame")
        top.pack(fill=tk.X)
        ttk.Label(top, text="💣 Minesweeper", style="Toolbar.TLabel",
                  font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=8, pady=4)

        self.diff_var = tk.StringVar(value="Easy")
        ttk.Combobox(top, textvariable=self.diff_var,
                     values=list(DIFFICULTIES.keys()),
                     state="readonly", width=8).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Button(top, text="New Game", style="Toolbar.TButton",
                   command=self._on_new_game).pack(side=tk.LEFT, padx=4, pady=2)

        self.mines_label = ttk.Label(top, text="Mines: 10",
                                     style="Toolbar.TLabel",
                                     font=("Segoe UI", 10, "bold"))
        self.mines_label.pack(side=tk.RIGHT, padx=8, pady=4)

        self.status_label = ttk.Label(top, text="",
                                      style="Toolbar.TLabel")
        self.status_label.pack(side=tk.RIGHT, padx=8, pady=4)

        self._canvas_frame = ttk.Frame(self)
        self._canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self._canvas_frame, bg="#c0c0c0",
                                highlightthickness=0)
        self.canvas.pack(padx=16, pady=16)
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<Button-3>", self._on_right_click)

    def _on_new_game(self):
        diff = self.diff_var.get()
        self._width, self._height, self._mines_count = DIFFICULTIES[diff]
        self._new_game()

    def _new_game(self):
        self._grid = [[0] * self._width for _ in range(self._height)]
        self._revealed = [[False] * self._width for _ in range(self._height)]
        self._flagged = [[False] * self._width for _ in range(self._height)]
        self._game_over = False
        self._first_click = True
        self._mines_remaining = self._mines_count
        cw = self._width * CELL_SIZE
        ch = self._height * CELL_SIZE
        self.canvas.config(width=cw, height=ch)
        self._update_mines_label()
        self.status_label.config(text="")
        self._draw()

    def _place_mines(self, safe_x, safe_y):
        safe = set()
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                safe.add((safe_x + dx, safe_y + dy))
        positions = []
        for r in range(self._height):
            for c in range(self._width):
                if (c, r) not in safe:
                    positions.append((c, r))
        mines = random.sample(positions, min(self._mines_count, len(positions)))
        for mx, my in mines:
            self._grid[my][mx] = -1
        for r in range(self._height):
            for c in range(self._width):
                if self._grid[r][c] == -1:
                    continue
                count = 0
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        nr, nc = r + dy, c + dx
                        if 0 <= nr < self._height and 0 <= nc < self._width:
                            if self._grid[nr][nc] == -1:
                                count += 1
                self._grid[r][c] = count

    def _on_left_click(self, event):
        if self._game_over:
            return
        c = event.x // CELL_SIZE
        r = event.y // CELL_SIZE
        if c < 0 or c >= self._width or r < 0 or r >= self._height:
            return
        if self._flagged[r][c]:
            return
        if self._first_click:
            self._place_mines(c, r)
            self._first_click = False
        if self._grid[r][c] == -1:
            self._game_over = True
            self._reveal_all()
            self.status_label.config(text="BOOM! Game Over")
        else:
            self._reveal(c, r)
            if self._check_win():
                self._game_over = True
                self.status_label.config(text="You Win!")
        self._draw()

    def _on_right_click(self, event):
        if self._game_over:
            return
        c = event.x // CELL_SIZE
        r = event.y // CELL_SIZE
        if c < 0 or c >= self._width or r < 0 or r >= self._height:
            return
        if self._revealed[r][c]:
            return
        self._flagged[r][c] = not self._flagged[r][c]
        self._mines_remaining += -1 if self._flagged[r][c] else 1
        self._update_mines_label()
        self._draw()

    def _reveal(self, x, y):
        if x < 0 or x >= self._width or y < 0 or y >= self._height:
            return
        if self._revealed[y][x] or self._flagged[y][x]:
            return
        self._revealed[y][x] = True
        if self._grid[y][x] == 0:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    self._reveal(x + dx, y + dy)

    def _reveal_all(self):
        for r in range(self._height):
            for c in range(self._width):
                self._revealed[r][c] = True

    def _check_win(self):
        for r in range(self._height):
            for c in range(self._width):
                if self._grid[r][c] != -1 and not self._revealed[r][c]:
                    return False
        return True

    def _update_mines_label(self):
        self.mines_label.config(text=f"Mines: {self._mines_remaining}")

    def _draw(self):
        self.canvas.delete("all")
        for r in range(self._height):
            for c in range(self._width):
                x1, y1 = c * CELL_SIZE, r * CELL_SIZE
                x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
                cx, cy = x1 + CELL_SIZE // 2, y1 + CELL_SIZE // 2

                if self._revealed[r][c]:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill="#e0e0e0", outline="#b0b0b0")
                    val = self._grid[r][c]
                    if val == -1:
                        self.canvas.create_text(
                            cx, cy, text="💣", font=("Segoe UI", 12))
                    elif val > 0:
                        color = NUM_COLORS.get(val, "#000000")
                        self.canvas.create_text(
                            cx, cy, text=str(val),
                            font=("Segoe UI", 12, "bold"), fill=color)
                else:
                    self.canvas.create_rectangle(
                        x1 + 1, y1 + 1, x2 - 1, y2 - 1,
                        fill="#a0a0a0", outline="#c0c0c0")
                    if self._flagged[r][c]:
                        self.canvas.create_text(
                            cx, cy, text="🚩", font=("Segoe UI", 12))

    def on_close(self):
        self._game_over = True
