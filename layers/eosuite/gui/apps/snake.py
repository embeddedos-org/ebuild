# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Snake — Classic snake game using tkinter Canvas.
"""
import random
import tkinter as tk
from tkinter import ttk


class SnakeGame(ttk.Frame):
    CELL_SIZE, GRID_WIDTH, GRID_HEIGHT = 20, 30, 20
    COLORS = {"head": "#4ec9b0", "body": "#3ca898", "food": "#d16969",
              "grid": "#1a1a1a", "border": "#333333", "text": "#d4d4d4"}

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._direction = self._next_direction = "Right"
        self._snake = [(5, 10), (4, 10), (3, 10)]
        self._food = None
        self._score = self._high_score = 0
        self._speed = 120
        self._running = False
        self._game_over = False
        self._timer_id = None
        self._build()

    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=4, pady=4)
        ttk.Label(header, text="🐍 Snake", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=8)
        self.score_label = ttk.Label(header, text="Score: 0  |  High: 0", font=("Consolas", 12))
        self.score_label.pack(side=tk.LEFT, padx=16)

        ttk.Label(header, text="Speed:").pack(side=tk.RIGHT, padx=(0, 4))
        self.speed_var = tk.IntVar(value=5)
        ttk.Scale(header, from_=1, to=10, variable=self.speed_var,
                  orient=tk.HORIZONTAL, length=100).pack(side=tk.RIGHT, padx=4)
        self.speed_var.trace_add("write", self._update_speed)

        btn_frame = ttk.Frame(header)
        btn_frame.pack(side=tk.RIGHT, padx=8)
        ttk.Button(btn_frame, text="▶ Start", command=self._start_game).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="⏸ Pause", command=self._toggle_pause).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="↺ Reset", command=self._reset_game).pack(side=tk.LEFT, padx=2)

        cw = self.GRID_WIDTH * self.CELL_SIZE
        ch = self.GRID_HEIGHT * self.CELL_SIZE
        self.canvas = tk.Canvas(self, width=cw, height=ch, bg=self.COLORS["grid"],
                                highlightthickness=1, highlightbackground=self.COLORS["border"])
        self.canvas.pack(padx=10, pady=(4, 10))

        for x in range(0, cw, self.CELL_SIZE):
            self.canvas.create_line(x, 0, x, ch, fill="#222222", width=1)
        for y in range(0, ch, self.CELL_SIZE):
            self.canvas.create_line(0, y, cw, y, fill="#222222", width=1)

        self.canvas.bind("<KeyPress>", self._on_key)
        self.canvas.focus_set()
        self.bind("<KeyPress>", self._on_key)
        self.bind("<FocusIn>", lambda e: self.canvas.focus_set())

        ttk.Label(self, text="Arrow keys or WASD to move  |  Space to pause",
                  foreground="#888888", font=("Segoe UI", 9)).pack(pady=(0, 4))
        self._draw_start_screen()

    def _draw_start_screen(self):
        w = self.GRID_WIDTH * self.CELL_SIZE
        h = self.GRID_HEIGHT * self.CELL_SIZE
        self.canvas.create_text(w // 2, h // 2 - 20, text="🐍 SNAKE",
                                font=("Segoe UI", 32, "bold"), fill=self.COLORS["head"], tags="overlay")
        self.canvas.create_text(w // 2, h // 2 + 20, text="Press Start or Space to begin",
                                font=("Segoe UI", 14), fill=self.COLORS["text"], tags="overlay")

    def _start_game(self):
        if self._game_over:
            self._reset_game()
        self.canvas.delete("overlay")
        self._running = True
        self._game_over = False
        self._place_food()
        self._draw()
        self._tick()
        self.canvas.focus_set()

    def _toggle_pause(self):
        if self._game_over:
            return
        self._running = not self._running
        if self._running:
            self._tick()
        elif self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None

    def _reset_game(self):
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        self._snake = [(5, 10), (4, 10), (3, 10)]
        self._direction = self._next_direction = "Right"
        self._food = None
        self._score = 0
        self._running = False
        self._game_over = False
        self._update_score_display()
        self.canvas.delete("snake", "food", "overlay", "gameover")
        self._draw_start_screen()

    def _place_food(self):
        while True:
            x = random.randint(0, self.GRID_WIDTH - 1)
            y = random.randint(0, self.GRID_HEIGHT - 1)
            if (x, y) not in self._snake:
                self._food = (x, y)
                break

    def _update_speed(self, *_args):
        self._speed = max(40, 200 - self.speed_var.get() * 18)

    def _on_key(self, event):
        key = event.keysym
        dmap = {"Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right",
                "w": "Up", "s": "Down", "a": "Left", "d": "Right",
                "W": "Up", "S": "Down", "A": "Left", "D": "Right"}
        opp = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}
        if key in dmap:
            new_dir = dmap[key]
            if new_dir != opp.get(self._direction):
                self._next_direction = new_dir
        elif key == "space":
            if self._game_over:
                self._reset_game()
                self._start_game()
            elif not self._running and not self._game_over:
                self._start_game()
            else:
                self._toggle_pause()

    def _tick(self):
        if not self._running:
            return
        self._direction = self._next_direction
        hx, hy = self._snake[0]
        if self._direction == "Up":
            hy -= 1
        elif self._direction == "Down":
            hy += 1
        elif self._direction == "Left":
            hx -= 1
        elif self._direction == "Right":
            hx += 1

        if (hx < 0 or hx >= self.GRID_WIDTH or hy < 0 or hy >= self.GRID_HEIGHT
                or (hx, hy) in self._snake):
            self._end_game()
            return

        self._snake.insert(0, (hx, hy))
        if (hx, hy) == self._food:
            self._score += 10
            if self._score > self._high_score:
                self._high_score = self._score
            self._update_score_display()
            self._place_food()
        else:
            self._snake.pop()

        self._draw()
        self._timer_id = self.after(self._speed, self._tick)

    def _draw(self):
        self.canvas.delete("snake", "food")
        if self._food:
            fx, fy = self._food
            cs = self.CELL_SIZE
            self.canvas.create_oval(fx * cs + 2, fy * cs + 2, (fx + 1) * cs - 2,
                                    (fy + 1) * cs - 2, fill=self.COLORS["food"], outline="", tags="food")
        for i, (sx, sy) in enumerate(self._snake):
            color = self.COLORS["head"] if i == 0 else self.COLORS["body"]
            r = 1 if i == 0 else 2
            cs = self.CELL_SIZE
            self.canvas.create_rectangle(sx * cs + r, sy * cs + r, (sx + 1) * cs - r,
                                         (sy + 1) * cs - r, fill=color, outline="", tags="snake")

    def _end_game(self):
        self._running = False
        self._game_over = True
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        w = self.GRID_WIDTH * self.CELL_SIZE
        h = self.GRID_HEIGHT * self.CELL_SIZE
        self.canvas.create_rectangle(w // 2 - 120, h // 2 - 40, w // 2 + 120, h // 2 + 40,
                                     fill="#1e1e1e", outline=self.COLORS["border"], width=2, tags="gameover")
        self.canvas.create_text(w // 2, h // 2 - 12, text="GAME OVER",
                                font=("Segoe UI", 18, "bold"), fill="#d16969", tags="gameover")
        self.canvas.create_text(w // 2, h // 2 + 16,
                                text=f"Score: {self._score}  |  Press Space to restart",
                                font=("Segoe UI", 10), fill=self.COLORS["text"], tags="gameover")

    def _update_score_display(self):
        self.score_label.config(text=f"Score: {self._score}  |  High: {self._high_score}")

    def on_close(self):
        self._running = False
        if self._timer_id:
            self.after_cancel(self._timer_id)
"""
EoSuite Snake — Classic snake game using tkinter Canvas.
"""
import random
import tkinter as tk
from tkinter import ttk


class SnakeGame(ttk.Frame):
    """Full graphical snake game with colored cells, score, and speed control."""

    CELL_SIZE = 20
    GRID_WIDTH = 30
    GRID_HEIGHT = 20

    COLORS = {
        "head": "#4ec9b0",
        "body": "#3ca898",
        "food": "#d16969",
        "grid": "#1a1a1a",
        "border": "#333333",
        "text": "#d4d4d4",
    }

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._direction = "Right"
        self._next_direction = "Right"
        self._snake = [(5, 10), (4, 10), (3, 10)]
        self._food = None
        self._score = 0
        self._high_score = 0
        self._speed = 120
        self._running = False
        self._game_over = False
        self._timer_id = None
        self._build()

    def _build(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=4, pady=4)

        ttk.Label(header, text="🐍 Snake",
                  font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=8)

        self.score_label = ttk.Label(
            header, text="Score: 0  |  High: 0",
            font=("Consolas", 12))
        self.score_label.pack(side=tk.LEFT, padx=16)

        # Speed control
        ttk.Label(header, text="Speed:").pack(side=tk.RIGHT, padx=(0, 4))
        self.speed_var = tk.IntVar(value=5)
        speed_scale = ttk.Scale(header, from_=1, to=10,
                                variable=self.speed_var,
                                orient=tk.HORIZONTAL, length=100)
        speed_scale.pack(side=tk.RIGHT, padx=4)
        self.speed_var.trace_add("write", self._update_speed)

        # Buttons
        btn_frame = ttk.Frame(header)
        btn_frame.pack(side=tk.RIGHT, padx=8)

        ttk.Button(btn_frame, text="▶ Start",
                   command=self._start_game).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="⏸ Pause",
                   command=self._toggle_pause).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="↺ Reset",
                   command=self._reset_game).pack(side=tk.LEFT, padx=2)

        # Canvas
        canvas_width = self.GRID_WIDTH * self.CELL_SIZE
        canvas_height = self.GRID_HEIGHT * self.CELL_SIZE
        self.canvas = tk.Canvas(
            self, width=canvas_width, height=canvas_height,
            bg=self.COLORS["grid"], highlightthickness=1,
            highlightbackground=self.COLORS["border"])
        self.canvas.pack(padx=10, pady=(4, 10))

        # Draw grid lines
        for x in range(0, canvas_width, self.CELL_SIZE):
            self.canvas.create_line(x, 0, x, canvas_height,
                                    fill="#222222", width=1)
        for y in range(0, canvas_height, self.CELL_SIZE):
            self.canvas.create_line(0, y, canvas_width, y,
                                    fill="#222222", width=1)

        # Keyboard bindings
        self.canvas.bind("<KeyPress>", self._on_key)
        self.canvas.focus_set()

        # Also bind on parent for key capture
        self.bind("<KeyPress>", self._on_key)
        self.bind("<FocusIn>", lambda e: self.canvas.focus_set())

        # Instructions
        ttk.Label(self, text="Arrow keys or WASD to move  |  Space to pause",
                  foreground="#888888",
                  font=("Segoe UI", 9)).pack(pady=(0, 4))

        self._draw_start_screen()

    def _draw_start_screen(self):
        w = self.GRID_WIDTH * self.CELL_SIZE
        h = self.GRID_HEIGHT * self.CELL_SIZE
        self.canvas.create_text(
            w // 2, h // 2 - 20,
            text="🐍 SNAKE",
            font=("Segoe UI", 32, "bold"),
            fill=self.COLORS["head"],
            tags="overlay")
        self.canvas.create_text(
            w // 2, h // 2 + 20,
            text="Press Start or Space to begin",
            font=("Segoe UI", 14),
            fill=self.COLORS["text"],
            tags="overlay")

    def _start_game(self):
        if self._game_over:
            self._reset_game()
        self.canvas.delete("overlay")
        self._running = True
        self._game_over = False
        self._place_food()
        self._draw()
        self._tick()
        self.canvas.focus_set()

    def _toggle_pause(self):
        if self._game_over:
            return
        self._running = not self._running
        if self._running:
            self._tick()
        elif self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None

    def _reset_game(self):
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        self._snake = [(5, 10), (4, 10), (3, 10)]
        self._direction = "Right"
        self._next_direction = "Right"
        self._food = None
        self._score = 0
        self._running = False
        self._game_over = False
        self._update_score_display()
        self.canvas.delete("snake", "food", "overlay", "gameover")
        self._draw_start_screen()

    def _place_food(self):
        while True:
            x = random.randint(0, self.GRID_WIDTH - 1)
            y = random.randint(0, self.GRID_HEIGHT - 1)
            if (x, y) not in self._snake:
                self._food = (x, y)
                break

    def _update_speed(self, *_args):
        speed = self.speed_var.get()
        self._speed = max(40, 200 - speed * 18)

    def _on_key(self, event):
        key = event.keysym
        direction_map = {
            "Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right",
            "w": "Up", "s": "Down", "a": "Left", "d": "Right",
            "W": "Up", "S": "Down", "A": "Left", "D": "Right",
        }

        opposites = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}

        if key in direction_map:
            new_dir = direction_map[key]
            if new_dir != opposites.get(self._direction):
                self._next_direction = new_dir
        elif key == "space":
            if self._game_over:
                self._reset_game()
                self._start_game()
            elif not self._running and not self._game_over:
                self._start_game()
            else:
                self._toggle_pause()

    def _tick(self):
        if not self._running:
            return

        self._direction = self._next_direction
        head_x, head_y = self._snake[0]

        if self._direction == "Up":
            head_y -= 1
        elif self._direction == "Down":
            head_y += 1
        elif self._direction == "Left":
            head_x -= 1
        elif self._direction == "Right":
            head_x += 1

        # Check collisions
        if (head_x < 0 or head_x >= self.GRID_WIDTH or
                head_y < 0 or head_y >= self.GRID_HEIGHT or
                (head_x, head_y) in self._snake):
            self._end_game()
            return

        self._snake.insert(0, (head_x, head_y))

        # Check food
        if (head_x, head_y) == self._food:
            self._score += 10
            if self._score > self._high_score:
                self._high_score = self._score
            self._update_score_display()
            self._place_food()
        else:
            self._snake.pop()

        self._draw()
        self._timer_id = self.after(self._speed, self._tick)

    def _draw(self):
        self.canvas.delete("snake", "food")

        # Draw food
        if self._food:
            fx, fy = self._food
            self.canvas.create_oval(
                fx * self.CELL_SIZE + 2, fy * self.CELL_SIZE + 2,
                (fx + 1) * self.CELL_SIZE - 2, (fy + 1) * self.CELL_SIZE - 2,
                fill=self.COLORS["food"], outline="", tags="food")

        # Draw snake
        for i, (sx, sy) in enumerate(self._snake):
            color = self.COLORS["head"] if i == 0 else self.COLORS["body"]
            r = 1 if i == 0 else 2
            self.canvas.create_rectangle(
                sx * self.CELL_SIZE + r, sy * self.CELL_SIZE + r,
                (sx + 1) * self.CELL_SIZE - r, (sy + 1) * self.CELL_SIZE - r,
                fill=color, outline="", tags="snake")

    def _end_game(self):
        self._running = False
        self._game_over = True
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None

        w = self.GRID_WIDTH * self.CELL_SIZE
        h = self.GRID_HEIGHT * self.CELL_SIZE
        self.canvas.create_rectangle(
            w // 2 - 120, h // 2 - 40, w // 2 + 120, h // 2 + 40,
            fill="#1e1e1e", outline=self.COLORS["border"],
            width=2, tags="gameover")
        self.canvas.create_text(
            w // 2, h // 2 - 12,
            text=f"GAME OVER",
            font=("Segoe UI", 18, "bold"),
            fill="#d16969", tags="gameover")
        self.canvas.create_text(
            w // 2, h // 2 + 16,
            text=f"Score: {self._score}  |  Press Space to restart",
            font=("Segoe UI", 10),
            fill=self.COLORS["text"], tags="gameover")

        self.app.set_status(f"Snake: Game Over — Score: {self._score}")

    def _update_score_display(self):
        self.score_label.config(
            text=f"Score: {self._score}  |  High: {self._high_score}")

    def on_close(self):
        self._running = False
        if self._timer_id:
            self.after_cancel(self._timer_id)
