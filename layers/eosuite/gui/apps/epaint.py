# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite ePaint — Canvas widget for mouse-driven drawing with color picker.
"""
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog


class EPaint(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._color, self._brush_size, self._tool = "#ffffff", 3, "brush"
        self._last_x, self._last_y = None, None
        c = self.app.theme.colors

        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(fill=tk.X)
        for text, tool in [("✏ Brush", "brush"), ("⬜ Rect", "rect"), ("⬭ Oval", "oval"),
                           ("━ Line", "line"), ("🧹 Eraser", "eraser")]:
            ttk.Button(toolbar, text=text, style="Toolbar.TButton",
                       command=lambda t=tool: setattr(self, '_tool', t)).pack(side=tk.LEFT, padx=2, pady=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        self.color_btn = tk.Button(toolbar, text="  ", bg=self._color, width=3,
                                   command=self._pick_color, relief=tk.FLAT)
        self.color_btn.pack(side=tk.LEFT, padx=4, pady=2)
        for qc in ["#ffffff", "#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff", "#ff8800"]:
            tk.Button(toolbar, text=" ", bg=qc, width=2, relief=tk.FLAT, borderwidth=1,
                      command=lambda c=qc: self._set_color(c)).pack(side=tk.LEFT, padx=1, pady=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Label(toolbar, text="Size:", style="Toolbar.TLabel").pack(side=tk.LEFT, padx=4)
        self.size_var = tk.IntVar(value=3)
        ttk.Scale(toolbar, from_=1, to=20, variable=self.size_var, orient=tk.HORIZONTAL, length=100).pack(side=tk.LEFT, padx=4)
        self.size_var.trace_add("write", lambda *a: setattr(self, '_brush_size', self.size_var.get()))

        ttk.Button(toolbar, text="🗑 Clear", style="Toolbar.TButton", command=lambda: self.canvas.delete("all")).pack(side=tk.RIGHT, padx=4, pady=2)
        ttk.Button(toolbar, text="💾 Save", style="Toolbar.TButton", command=self._save).pack(side=tk.RIGHT, padx=4, pady=2)

        self.canvas = tk.Canvas(self, bg=c["terminal_bg"], highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _set_color(self, color):
        self._color = color
        self.color_btn.config(bg=color)

    def _pick_color(self):
        result = colorchooser.askcolor(color=self._color, title="Pick Color")
        if result[1]:
            self._set_color(result[1])

    def _on_press(self, e):
        self._last_x, self._last_y = e.x, e.y
        if self._tool == "brush":
            s = self._brush_size
            self.canvas.create_oval(e.x - s, e.y - s, e.x + s, e.y + s, fill=self._color, outline="")
        elif self._tool == "eraser":
            s = self._brush_size * 2
            self.canvas.create_oval(e.x - s, e.y - s, e.x + s, e.y + s, fill=self.app.theme.colors["terminal_bg"], outline="")

    def _on_drag(self, e):
        if self._tool == "brush":
            self.canvas.create_line(self._last_x, self._last_y, e.x, e.y, fill=self._color,
                                    width=self._brush_size * 2, capstyle=tk.ROUND, smooth=True)
        elif self._tool == "eraser":
            self.canvas.create_line(self._last_x, self._last_y, e.x, e.y,
                                    fill=self.app.theme.colors["terminal_bg"],
                                    width=self._brush_size * 4, capstyle=tk.ROUND)
        self._last_x, self._last_y = e.x, e.y

    def _on_release(self, e):
        if self._tool == "rect":
            self.canvas.create_rectangle(self._last_x, self._last_y, e.x, e.y, outline=self._color, width=self._brush_size)
        elif self._tool == "oval":
            self.canvas.create_oval(self._last_x, self._last_y, e.x, e.y, outline=self._color, width=self._brush_size)
        elif self._tool == "line":
            self.canvas.create_line(self._last_x, self._last_y, e.x, e.y, fill=self._color, width=self._brush_size)
        self._last_x, self._last_y = None, None

    def _save(self):
        path = filedialog.asksaveasfilename(defaultextension=".ps", filetypes=[("PostScript", "*.ps"), ("All files", "*.*")])
        if path:
            self.canvas.postscript(file=path, colormode="color")
            self.app.set_status(f"Canvas saved: {path}")
"""
EoSuite ePaint — Canvas widget for mouse-driven drawing with color picker.
"""
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog


class EPaint(ttk.Frame):
    """Drawing canvas with color picker and brush tools."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._color = "#ffffff"
        self._brush_size = 3
        self._tool = "brush"
        self._last_x = None
        self._last_y = None
        self._build()

    def _build(self):
        c = self.app.theme.colors

        # Toolbar
        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(fill=tk.X)

        tools = [
            ("✏ Brush", "brush"),
            ("⬜ Rectangle", "rect"),
            ("⬭ Oval", "oval"),
            ("━ Line", "line"),
            ("🧹 Eraser", "eraser"),
        ]
        for text, tool in tools:
            ttk.Button(toolbar, text=text, style="Toolbar.TButton",
                       command=lambda t=tool: self._set_tool(t)).pack(
                side=tk.LEFT, padx=2, pady=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=4)

        # Color picker
        self.color_btn = tk.Button(
            toolbar, text="  ", bg=self._color, width=3,
            command=self._pick_color, relief=tk.FLAT)
        self.color_btn.pack(side=tk.LEFT, padx=4, pady=2)

        # Quick colors
        quick_colors = ["#ffffff", "#ff0000", "#00ff00", "#0000ff",
                        "#ffff00", "#ff00ff", "#00ffff", "#ff8800"]
        for qc in quick_colors:
            btn = tk.Button(toolbar, text=" ", bg=qc, width=2,
                            relief=tk.FLAT, borderwidth=1,
                            command=lambda c=qc: self._set_color(c))
            btn.pack(side=tk.LEFT, padx=1, pady=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=4)

        # Brush size
        ttk.Label(toolbar, text="Size:", style="Toolbar.TLabel").pack(
            side=tk.LEFT, padx=4)
        self.size_var = tk.IntVar(value=3)
        size_scale = ttk.Scale(toolbar, from_=1, to=20,
                               variable=self.size_var, orient=tk.HORIZONTAL,
                               length=100)
        size_scale.pack(side=tk.LEFT, padx=4)
        self.size_var.trace_add("write", self._update_size)

        # Actions
        ttk.Button(toolbar, text="🗑 Clear", style="Toolbar.TButton",
                   command=self._clear).pack(side=tk.RIGHT, padx=4, pady=2)
        ttk.Button(toolbar, text="💾 Save", style="Toolbar.TButton",
                   command=self._save).pack(side=tk.RIGHT, padx=4, pady=2)

        # Canvas
        self.canvas = tk.Canvas(
            self, bg=c["terminal_bg"], highlightthickness=0,
            cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _set_tool(self, tool: str):
        self._tool = tool

    def _set_color(self, color: str):
        self._color = color
        self.color_btn.config(bg=color)

    def _pick_color(self):
        result = colorchooser.askcolor(color=self._color, title="Pick Color")
        if result[1]:
            self._set_color(result[1])

    def _update_size(self, *_args):
        self._brush_size = self.size_var.get()

    def _on_press(self, event):
        self._last_x = event.x
        self._last_y = event.y
        if self._tool == "brush":
            self.canvas.create_oval(
                event.x - self._brush_size, event.y - self._brush_size,
                event.x + self._brush_size, event.y + self._brush_size,
                fill=self._color, outline="")
        elif self._tool == "eraser":
            c = self.app.theme.colors
            self.canvas.create_oval(
                event.x - self._brush_size * 2, event.y - self._brush_size * 2,
                event.x + self._brush_size * 2, event.y + self._brush_size * 2,
                fill=c["terminal_bg"], outline="")

    def _on_drag(self, event):
        if self._tool == "brush":
            self.canvas.create_line(
                self._last_x, self._last_y, event.x, event.y,
                fill=self._color, width=self._brush_size * 2,
                capstyle=tk.ROUND, smooth=True)
            self._last_x = event.x
            self._last_y = event.y
        elif self._tool == "eraser":
            c = self.app.theme.colors
            self.canvas.create_line(
                self._last_x, self._last_y, event.x, event.y,
                fill=c["terminal_bg"], width=self._brush_size * 4,
                capstyle=tk.ROUND)
            self._last_x = event.x
            self._last_y = event.y

    def _on_release(self, event):
        if self._tool == "rect":
            self.canvas.create_rectangle(
                self._last_x, self._last_y, event.x, event.y,
                outline=self._color, width=self._brush_size)
        elif self._tool == "oval":
            self.canvas.create_oval(
                self._last_x, self._last_y, event.x, event.y,
                outline=self._color, width=self._brush_size)
        elif self._tool == "line":
            self.canvas.create_line(
                self._last_x, self._last_y, event.x, event.y,
                fill=self._color, width=self._brush_size)
        self._last_x = None
        self._last_y = None

    def _clear(self):
        self.canvas.delete("all")

    def _save(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".ps",
            filetypes=[("PostScript", "*.ps"), ("All files", "*.*")])
        if path:
            self.canvas.postscript(file=path, colormode="color")
            self.app.set_status(f"Canvas saved: {path}")
