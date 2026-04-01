# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Tetris — Classic falling block puzzle game.
"""
import random
import tkinter as tk
from tkinter import ttk


SHAPES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[0, 1, 0], [1, 1, 1]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "Z": [[1, 1, 0], [0, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
}

COLORS = {
    "I": "#00f0f0", "O": "#f0f000", "T": "#a000f0",
    "S": "#00f000", "Z": "#f00000", "J": "#0000f0", "L": "#f0a000",
}

GRID_WIDTH = 10
GRID_HEIGHT = 20
CELL_SIZE = 28


class Tetris(ttk.Frame):
    """Classic Tetris game."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._score = 0
        self._level = 1
        self._lines = 0
        self._high_score = 0
        self._running = False
        self._game_over = False
        self._after_id = None
        self._grid = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self._current = None
        self._current_x = 0
        self._current_y = 0
        self._current_type = ""
        self._build()

    def _build(self):
        top = ttk.Frame(self, style="Toolbar.TFrame")
        top.pack(fill=tk.X)
        ttk.Label(top, text="🧱 Tetris", style="Toolbar.TLabel",
                  font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=8, pady=4)
        ttk.Button(top, text="New Game", style="Toolbar.TButton",
                   command=self._start_game).pack(side=tk.RIGHT, padx=4, pady=2)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)

        cw = GRID_WIDTH * CELL_SIZE
        ch = GRID_HEIGHT * CELL_SIZE
        self.canvas = tk.Canvas(body, width=cw, height=ch,
                                bg="#111111", highlightthickness=1,
                                highlightbackground="#333333")
        self.canvas.pack(side=tk.LEFT, padx=16, pady=16)

        info = ttk.Frame(body)
        info.pack(side=tk.LEFT, fill=tk.Y, padx=16, pady=16)

        self.score_label = ttk.Label(info, text="Score: 0",
                                     font=("Segoe UI", 14, "bold"))
        self.score_label.pack(anchor=tk.W, pady=4)
        self.level_label = ttk.Label(info, text="Level: 1",
                                     font=("Segoe UI", 12))
        self.level_label.pack(anchor=tk.W, pady=4)
        self.lines_label = ttk.Label(info, text="Lines: 0",
                                     font=("Segoe UI", 12))
        self.lines_label.pack(anchor=tk.W, pady=4)
        self.high_label = ttk.Label(info, text="High: 0",
                                    font=("Segoe UI", 12))
        self.high_label.pack(anchor=tk.W, pady=4)

        ttk.Label(info, text="\nControls:",
                  font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, pady=(16, 4))
        for line in ["← → Move", "↑ Rotate", "↓ Soft Drop",
                     "Space Hard Drop", "P Pause"]:
            ttk.Label(info, text=line,
                      font=("Segoe UI", 10)).pack(anchor=tk.W)

        self.canvas.bind("<Key>", self._on_key)
        self.canvas.focus_set()
        self.bind("<Visibility>", lambda e: self.canvas.focus_set())
        self._draw_empty()

    def _draw_empty(self):
        self.canvas.delete("all")
        cx = (GRID_WIDTH * CELL_SIZE) // 2
        cy = (GRID_HEIGHT * CELL_SIZE) // 2
        self.canvas.create_text(cx, cy, text="Press New Game",
                                font=("Segoe UI", 16), fill="#555555")

    def _start_game(self):
        self._grid = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self._score = 0
        self._level = 1
        self._lines = 0
        self._running = True
        self._game_over = False
        self._spawn_piece()
        self._update_labels()
        self._tick()
        self.canvas.focus_set()

    def _spawn_piece(self):
        self._current_type = random.choice(list(SHAPES.keys()))
        self._current = [row[:] for row in SHAPES[self._current_type]]
        self._current_x = GRID_WIDTH // 2 - len(self._current[0]) // 2
        self._current_y = 0
        if not self._valid_pos(self._current, self._current_x, self._current_y):
            self._game_over = True
            self._running = False
            if self._score > self._high_score:
                self._high_score = self._score
            self._update_labels()
            self._draw()
            self.canvas.create_text(
                (GRID_WIDTH * CELL_SIZE) // 2,
                (GRID_HEIGHT * CELL_SIZE) // 2,
                text="GAME OVER", font=("Segoe UI", 20, "bold"),
                fill="#ff4444")

    def _valid_pos(self, shape, ox, oy):
        for r, row in enumerate(shape):
            for c, val in enumerate(row):
                if val:
                    nx, ny = ox + c, oy + r
                    if nx < 0 or nx >= GRID_WIDTH or ny >= GRID_HEIGHT:
                        return False
                    if ny >= 0 and self._grid[ny][nx] is not None:
                        return False
        return True

    def _lock_piece(self):
        for r, row in enumerate(self._current):
            for c, val in enumerate(row):
                if val:
                    gy = self._current_y + r
                    gx = self._current_x + c
                    if 0 <= gy < GRID_HEIGHT and 0 <= gx < GRID_WIDTH:
                        self._grid[gy][gx] = self._current_type
        cleared = self._clear_lines()
        self._lines += cleared
        points = [0, 100, 300, 500, 800]
        self._score += points[min(cleared, 4)] * self._level
        self._level = self._lines // 10 + 1
        self._update_labels()
        self._spawn_piece()

    def _clear_lines(self):
        cleared = 0
        new_grid = []
        for row in self._grid:
            if all(cell is not None for cell in row):
                cleared += 1
            else:
                new_grid.append(row)
        for _ in range(cleared):
            new_grid.insert(0, [None] * GRID_WIDTH)
        self._grid = new_grid
        return cleared

    def _rotate(self):
        rotated = list(zip(*reversed(self._current)))
        rotated = [list(row) for row in rotated]
        if self._valid_pos(rotated, self._current_x, self._current_y):
            self._current = rotated

    def _tick(self):
        if not self._running:
            return
        if self._valid_pos(self._current, self._current_x, self._current_y + 1):
            self._current_y += 1
        else:
            self._lock_piece()
        self._draw()
        speed = max(100, 500 - (self._level - 1) * 40)
        self._after_id = self.after(speed, self._tick)

    def _on_key(self, event):
        if not self._running:
            return
        key = event.keysym
        if key in ("Left", "a"):
            if self._valid_pos(self._current, self._current_x - 1, self._current_y):
                self._current_x -= 1
        elif key in ("Right", "d"):
            if self._valid_pos(self._current, self._current_x + 1, self._current_y):
                self._current_x += 1
        elif key in ("Down", "s"):
            if self._valid_pos(self._current, self._current_x, self._current_y + 1):
                self._current_y += 1
                self._score += 1
        elif key in ("Up", "w"):
            self._rotate()
        elif key == "space":
            while self._valid_pos(self._current, self._current_x, self._current_y + 1):
                self._current_y += 1
                self._score += 2
            self._lock_piece()
        elif key == "p":
            self._running = not self._running
            if self._running:
                self._tick()
        self._draw()
        self._update_labels()

    def _draw(self):
        self.canvas.delete("all")
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                x1, y1 = c * CELL_SIZE, r * CELL_SIZE
                x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
                cell = self._grid[r][c]
                if cell:
                    self.canvas.create_rectangle(
                        x1 + 1, y1 + 1, x2 - 1, y2 - 1,
                        fill=COLORS[cell], outline="#222222")
                else:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill="", outline="#1a1a1a")
        if self._current:
            color = COLORS[self._current_type]
            for r, row in enumerate(self._current):
                for c, val in enumerate(row):
                    if val:
                        gx = self._current_x + c
                        gy = self._current_y + r
                        if gy >= 0:
                            x1, y1 = gx * CELL_SIZE, gy * CELL_SIZE
                            x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
                            self.canvas.create_rectangle(
                                x1 + 1, y1 + 1, x2 - 1, y2 - 1,
                                fill=color, outline="#444444")

    def _update_labels(self):
        self.score_label.config(text=f"Score: {self._score}")
        self.level_label.config(text=f"Level: {self._level}")
        self.lines_label.config(text=f"Lines: {self._lines}")
        self.high_label.config(text=f"High: {self._high_score}")

    def on_close(self):
        self._running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
