# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Chess — Two-player chess board with legal move validation.
"""
import tkinter as tk
from tkinter import ttk

PIECES = {
    "K": "♔", "Q": "♕", "R": "♖", "B": "♗", "N": "♘", "P": "♙",
    "k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟",
}

INITIAL_BOARD = [
    ["r", "n", "b", "q", "k", "b", "n", "r"],
    ["p", "p", "p", "p", "p", "p", "p", "p"],
    ["", "", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "", ""],
    ["P", "P", "P", "P", "P", "P", "P", "P"],
    ["R", "N", "B", "Q", "K", "B", "N", "R"],
]

CELL_SIZE = 60


class Chess(ttk.Frame):
    """Two-player chess game with move validation."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._board = []
        self._turn = "white"
        self._selected = None
        self._valid_moves = []
        self._move_history = []
        self._captured_white = []
        self._captured_black = []
        self._build()
        self._new_game()

    def _build(self):
        c = self.app.theme.colors

        top = ttk.Frame(self, style="Toolbar.TFrame")
        top.pack(fill=tk.X)
        ttk.Label(top, text="♟ Chess", style="Toolbar.TLabel",
                  font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=8, pady=4)
        ttk.Button(top, text="New Game", style="Toolbar.TButton",
                   command=self._new_game).pack(side=tk.RIGHT, padx=4, pady=2)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)

        bsize = 8 * CELL_SIZE
        self.canvas = tk.Canvas(body, width=bsize, height=bsize,
                                highlightthickness=1,
                                highlightbackground="#333333")
        self.canvas.pack(side=tk.LEFT, padx=16, pady=16)
        self.canvas.bind("<Button-1>", self._on_click)

        info = ttk.Frame(body)
        info.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=16)

        self.turn_label = ttk.Label(info, text="Turn: White",
                                    font=("Segoe UI", 14, "bold"))
        self.turn_label.pack(anchor=tk.W, pady=4)

        self.status_label = ttk.Label(info, text="",
                                      font=("Segoe UI", 11))
        self.status_label.pack(anchor=tk.W, pady=4)

        ttk.Label(info, text="Captured:",
                  font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, pady=(16, 4))
        self.captured_label = ttk.Label(info, text="",
                                        font=("Segoe UI", 14))
        self.captured_label.pack(anchor=tk.W, pady=2)

        ttk.Label(info, text="Move History:",
                  font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, pady=(16, 4))
        self.history_text = tk.Text(info, width=20, height=15,
                                    font=("Consolas", 10),
                                    bg=c["terminal_bg"], fg=c["terminal_fg"],
                                    state=tk.DISABLED, relief=tk.FLAT)
        self.history_text.pack(fill=tk.BOTH, expand=True)

    def _new_game(self):
        self._board = [row[:] for row in INITIAL_BOARD]
        self._turn = "white"
        self._selected = None
        self._valid_moves = []
        self._move_history = []
        self._captured_white = []
        self._captured_black = []
        self.turn_label.config(text="Turn: White")
        self.status_label.config(text="")
        self.captured_label.config(text="")
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)
        self.history_text.config(state=tk.DISABLED)
        self._draw()

    def _is_white(self, piece):
        return piece.isupper()

    def _is_black(self, piece):
        return piece.islower()

    def _own_piece(self, piece):
        if self._turn == "white":
            return self._is_white(piece)
        return self._is_black(piece)

    def _enemy_piece(self, piece):
        if not piece:
            return False
        if self._turn == "white":
            return self._is_black(piece)
        return self._is_white(piece)

    def _get_moves(self, row, col):
        piece = self._board[row][col]
        if not piece:
            return []
        moves = []
        p = piece.upper()

        if p == "P":
            direction = -1 if self._is_white(piece) else 1
            start_row = 6 if self._is_white(piece) else 1
            nr = row + direction
            if 0 <= nr < 8 and not self._board[nr][col]:
                moves.append((nr, col))
                if row == start_row and not self._board[nr + direction][col]:
                    moves.append((nr + direction, col))
            for dc in [-1, 1]:
                nc = col + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = self._board[nr][nc]
                    if target and self._enemy_piece(target):
                        moves.append((nr, nc))

        elif p == "R":
            moves.extend(self._slide(row, col, [(-1, 0), (1, 0), (0, -1), (0, 1)]))

        elif p == "B":
            moves.extend(self._slide(row, col, [(-1, -1), (-1, 1), (1, -1), (1, 1)]))

        elif p == "Q":
            moves.extend(self._slide(row, col,
                                     [(-1, 0), (1, 0), (0, -1), (0, 1),
                                      (-1, -1), (-1, 1), (1, -1), (1, 1)]))

        elif p == "K":
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < 8 and 0 <= nc < 8:
                        target = self._board[nr][nc]
                        if not target or self._enemy_piece(target):
                            moves.append((nr, nc))

        elif p == "N":
            for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                           (1, -2), (1, 2), (2, -1), (2, 1)]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = self._board[nr][nc]
                    if not target or self._enemy_piece(target):
                        moves.append((nr, nc))

        return moves

    def _slide(self, row, col, directions):
        moves = []
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                target = self._board[nr][nc]
                if not target:
                    moves.append((nr, nc))
                elif self._enemy_piece(target):
                    moves.append((nr, nc))
                    break
                else:
                    break
                nr += dr
                nc += dc
        return moves

    def _on_click(self, event):
        col = event.x // CELL_SIZE
        row = event.y // CELL_SIZE
        if col < 0 or col >= 8 or row < 0 or row >= 8:
            return

        if self._selected:
            sr, sc = self._selected
            if (row, col) in self._valid_moves:
                self._make_move(sr, sc, row, col)
                self._selected = None
                self._valid_moves = []
            elif self._board[row][col] and self._own_piece(self._board[row][col]):
                self._selected = (row, col)
                self._valid_moves = self._get_moves(row, col)
            else:
                self._selected = None
                self._valid_moves = []
        else:
            piece = self._board[row][col]
            if piece and self._own_piece(piece):
                self._selected = (row, col)
                self._valid_moves = self._get_moves(row, col)

        self._draw()

    def _make_move(self, sr, sc, dr, dc):
        piece = self._board[sr][sc]
        captured = self._board[dr][dc]
        if captured:
            if self._is_white(captured):
                self._captured_black.append(captured)
            else:
                self._captured_white.append(captured)

        self._board[dr][dc] = piece
        self._board[sr][sc] = ""

        cols = "abcdefgh"
        notation = f"{PIECES.get(piece, piece)}{cols[sc]}{8 - sr}-{cols[dc]}{8 - dr}"
        if captured:
            notation += f" x{PIECES.get(captured, captured)}"
        self._move_history.append(notation)

        self.history_text.config(state=tk.NORMAL)
        num = (len(self._move_history) + 1) // 2
        if self._turn == "white":
            self.history_text.insert(tk.END, f"{num}. {notation} ")
        else:
            self.history_text.insert(tk.END, f"{notation}\n")
        self.history_text.see(tk.END)
        self.history_text.config(state=tk.DISABLED)

        cap_w = " ".join(PIECES.get(p, p) for p in self._captured_white)
        cap_b = " ".join(PIECES.get(p, p) for p in self._captured_black)
        self.captured_label.config(text=f"W: {cap_w}\nB: {cap_b}")

        self._turn = "black" if self._turn == "white" else "white"
        self.turn_label.config(
            text=f"Turn: {self._turn.capitalize()}")

        if captured and captured.upper() == "K":
            winner = "Black" if self._is_white(captured) else "White"
            self.status_label.config(text=f"Checkmate! {winner} wins!")

    def _draw(self):
        self.canvas.delete("all")
        light = "#f0d9b5"
        dark = "#b58863"
        sel_color = "#ffff00"

        for r in range(8):
            for c in range(8):
                x1, y1 = c * CELL_SIZE, r * CELL_SIZE
                x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
                bg = light if (r + c) % 2 == 0 else dark

                if self._selected and self._selected == (r, c):
                    bg = sel_color

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg,
                                             outline="")

                if (r, c) in self._valid_moves:
                    cx, cy = x1 + CELL_SIZE // 2, y1 + CELL_SIZE // 2
                    if self._board[r][c]:
                        self.canvas.create_oval(
                            x1 + 2, y1 + 2, x2 - 2, y2 - 2,
                            outline="#ff4444", width=3)
                    else:
                        self.canvas.create_oval(
                            cx - 8, cy - 8, cx + 8, cy + 8,
                            fill="#666666", outline="")

                piece = self._board[r][c]
                if piece:
                    symbol = PIECES.get(piece, piece)
                    self.canvas.create_text(
                        x1 + CELL_SIZE // 2, y1 + CELL_SIZE // 2,
                        text=symbol, font=("Segoe UI", CELL_SIZE // 2))

        cols = "abcdefgh"
        for i in range(8):
            self.canvas.create_text(
                i * CELL_SIZE + CELL_SIZE // 2, 8 * CELL_SIZE - 4,
                text=cols[i], font=("Segoe UI", 8), fill="#444444",
                anchor=tk.S)
            self.canvas.create_text(
                4, i * CELL_SIZE + CELL_SIZE // 2,
                text=str(8 - i), font=("Segoe UI", 8), fill="#444444",
                anchor=tk.W)

    def on_close(self):
        pass
