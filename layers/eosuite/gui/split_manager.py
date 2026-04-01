# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Split View Manager — Smart split with pane assignment dialog.
Users pick which tabs go in which pane. Draggable sash dividers for resizing.
"""
import tkinter as tk
from tkinter import ttk


class SplitAssignDialog:
    """Dialog that lets users pick which open tabs go in which split pane."""

    def __init__(self, parent, tab_list, num_panes, pane_labels):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Assign Tabs to Panes")
        self.dialog.geometry("500x420")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        ttk.Label(self.dialog, text="Assign each tab to a pane:",
                  font=("Segoe UI", 12, "bold")).pack(pady=(12, 4))
        ttk.Label(self.dialog, text="Drag the center divider after splitting to resize.",
                  foreground="#888888").pack(pady=(0, 10))

        # Scrollable frame for tab assignments
        canvas = tk.Canvas(self.dialog, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.dialog, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.assignments = {}
        for i, (text, _widget) in enumerate(tab_list):
            row = ttk.Frame(inner)
            row.pack(fill=tk.X, pady=3, padx=5)

            ttk.Label(row, text=text, font=("Segoe UI", 10), width=30,
                      anchor=tk.W).pack(side=tk.LEFT, padx=(0, 10))

            var = tk.StringVar(value=pane_labels[i % num_panes])
            self.assignments[i] = var

            combo = ttk.Combobox(row, textvariable=var, values=pane_labels,
                                 state="readonly", width=15)
            combo.pack(side=tk.RIGHT)

        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, pady=10, padx=10)

        ttk.Button(btn_frame, text="Auto-assign (even split)",
                   command=lambda: self._auto_assign(tab_list, num_panes, pane_labels)
                   ).pack(side=tk.LEFT, padx=4)

        ttk.Button(btn_frame, text="Cancel",
                   command=self._cancel).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="✓ Apply Split",
                   command=self._apply).pack(side=tk.RIGHT, padx=4)

        self.dialog.protocol("WM_DELETE_WINDOW", self._cancel)
        self.dialog.wait_window()

    def _auto_assign(self, tab_list, num_panes, pane_labels):
        for i in range(len(tab_list)):
            self.assignments[i].set(pane_labels[i % num_panes])

    def _apply(self):
        self.result = {i: var.get() for i, var in self.assignments.items()}
        self.dialog.destroy()

    def _cancel(self):
        self.result = None
        self.dialog.destroy()


class SplitManager:
    """Manages split layouts with draggable dividers and smart tab assignment."""

    def __init__(self, parent_frame, app):
        self.parent = parent_frame
        self.app = app
        self.current_layout = "single"
        self.paned = None
        self.panes = []
        self.notebooks = []
        self._saved_tabs = []

    def get_active_notebook(self):
        if not self.notebooks:
            return self.app.notebook
        try:
            focused = self.parent.focus_get()
            for nb in self.notebooks:
                if focused and str(focused).startswith(str(nb)):
                    return nb
        except Exception:
            pass
        return self.notebooks[0] if self.notebooks else self.app.notebook

    # ─── Public API ───────────────────────────────────────────

    def show_split_menu(self):
        menu = tk.Menu(self.app.root, tearoff=0)
        menu.add_command(label="⬜  Single View", command=self.layout_single)
        menu.add_separator()
        menu.add_command(label="◧  Split Left | Right", command=lambda: self._split_with_dialog("h2"))
        menu.add_command(label="⬒  Split Top / Bottom", command=lambda: self._split_with_dialog("v2"))
        menu.add_separator()
        menu.add_command(label="⊞  Quad (2×2)", command=lambda: self._split_with_dialog("quad"))
        menu.add_separator()
        menu.add_command(label="◧  Quick Split Left | Right", command=self.layout_h2)
        menu.add_command(label="⬒  Quick Split Top / Bottom", command=self.layout_v2)
        menu.add_command(label="⊞  Quick Quad", command=self.layout_quad)
        menu.add_separator()
        menu.add_command(label="📤  Pop-out Current Tab", command=self.popout_current)

        try:
            menu.tk_popup(self.app.root.winfo_pointerx(), self.app.root.winfo_pointery())
        except Exception:
            menu.tk_popup(400, 80)

    def popout_current(self):
        nb = self.app.notebook
        current = nb.select()
        if not current:
            return
        idx = nb.index(current)
        if idx == 0:
            self.app.set_status("Cannot pop out the Home tab")
            return
        self._popout_tab(nb, idx)
        self.app.set_status("Tab popped out to window")

    # ─── Smart split with dialog ──────────────────────────────

    def _split_with_dialog(self, layout_type):
        tabs = self._steal_tabs()
        if len(tabs) < 2:
            self._restore_tabs(tabs)
            self.app.set_status("Need at least 2 open tabs to split")
            return

        if layout_type == "quad":
            labels = ["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right"]
            num = 4
        elif layout_type == "h2":
            labels = ["Left Pane", "Right Pane"]
            num = 2
        else:
            labels = ["Top Pane", "Bottom Pane"]
            num = 2

        dlg = SplitAssignDialog(self.app.root, tabs, num, labels)
        if dlg.result is None:
            self._restore_tabs(tabs)
            return

        # Group tabs by assigned pane
        pane_map = {label: [] for label in labels}
        for idx, label in dlg.result.items():
            pane_map[label].append(tabs[idx])

        # Ensure every pane has at least something — move overflow
        non_empty = [l for l, t in pane_map.items() if t]
        empty = [l for l, t in pane_map.items() if not t]
        for e in empty:
            # Steal one tab from the pane with the most
            biggest = max(non_empty, key=lambda l: len(pane_map[l]))
            if len(pane_map[biggest]) > 1:
                pane_map[e].append(pane_map[biggest].pop())

        if layout_type == "h2":
            self._apply_h2(pane_map, labels)
        elif layout_type == "v2":
            self._apply_v2(pane_map, labels)
        else:
            self._apply_quad(pane_map, labels)

    def _apply_h2(self, pane_map, labels):
        self.current_layout = "h2"
        self._destroy_paned()

        self.paned = tk.PanedWindow(self.parent, orient=tk.HORIZONTAL,
                                     sashwidth=6, sashrelief=tk.RAISED,
                                     bg="#555555", opaqueresize=True)
        self.paned.pack(fill=tk.BOTH, expand=True)

        left = self._make_notebook(self.paned)
        right = self._make_notebook(self.paned)
        self.paned.add(left, stretch="always")
        self.paned.add(right, stretch="always")

        nbs = {labels[0]: left, labels[1]: right}
        for label, tab_list in pane_map.items():
            for text, widget in tab_list:
                nbs[label].add(widget, text=text)

        for nb in [left, right]:
            if nb.tabs():
                nb.select(0)
        self.app.set_status("Layout: Left | Right — drag sash to resize")

    def _apply_v2(self, pane_map, labels):
        self.current_layout = "v2"
        self._destroy_paned()

        self.paned = tk.PanedWindow(self.parent, orient=tk.VERTICAL,
                                     sashwidth=6, sashrelief=tk.RAISED,
                                     bg="#555555", opaqueresize=True)
        self.paned.pack(fill=tk.BOTH, expand=True)

        top = self._make_notebook(self.paned)
        bot = self._make_notebook(self.paned)
        self.paned.add(top, stretch="always")
        self.paned.add(bot, stretch="always")

        nbs = {labels[0]: top, labels[1]: bot}
        for label, tab_list in pane_map.items():
            for text, widget in tab_list:
                nbs[label].add(widget, text=text)

        for nb in [top, bot]:
            if nb.tabs():
                nb.select(0)
        self.app.set_status("Layout: Top / Bottom — drag sash to resize")

    def _apply_quad(self, pane_map, labels):
        self.current_layout = "quad"
        self._destroy_paned()

        self.paned = tk.PanedWindow(self.parent, orient=tk.VERTICAL,
                                     sashwidth=6, sashrelief=tk.RAISED,
                                     bg="#555555", opaqueresize=True)
        self.paned.pack(fill=tk.BOTH, expand=True)

        top_pw = tk.PanedWindow(self.paned, orient=tk.HORIZONTAL,
                                 sashwidth=6, sashrelief=tk.RAISED,
                                 bg="#555555", opaqueresize=True)
        bot_pw = tk.PanedWindow(self.paned, orient=tk.HORIZONTAL,
                                 sashwidth=6, sashrelief=tk.RAISED,
                                 bg="#555555", opaqueresize=True)
        self.paned.add(top_pw, stretch="always")
        self.paned.add(bot_pw, stretch="always")

        tl = self._make_notebook(top_pw)
        tr = self._make_notebook(top_pw)
        bl = self._make_notebook(bot_pw)
        br = self._make_notebook(bot_pw)
        top_pw.add(tl, stretch="always")
        top_pw.add(tr, stretch="always")
        bot_pw.add(bl, stretch="always")
        bot_pw.add(br, stretch="always")

        nbs = {labels[0]: tl, labels[1]: tr, labels[2]: bl, labels[3]: br}
        for label, tab_list in pane_map.items():
            for text, widget in tab_list:
                nbs[label].add(widget, text=text)

        for nb in [tl, tr, bl, br]:
            if nb.tabs():
                nb.select(0)
        self.app.set_status("Layout: Quad — drag any sash to resize")

    # ─── Quick split (auto round-robin, no dialog) ────────────

    def layout_single(self):
        self._collect_all_back()
        self.current_layout = "single"
        self.app.notebook.pack(fill=tk.BOTH, expand=True)
        self.app.set_status("Layout: Single view")

    def layout_h2(self):
        tabs = self._steal_tabs()
        if len(tabs) < 2:
            self._restore_tabs(tabs)
            self.app.set_status("Need at least 2 tabs to split")
            return
        self.current_layout = "h2"
        self.app.notebook.pack_forget()
        self._destroy_paned()

        self.paned = tk.PanedWindow(self.parent, orient=tk.HORIZONTAL,
                                     sashwidth=6, sashrelief=tk.RAISED,
                                     bg="#555555", opaqueresize=True)
        self.paned.pack(fill=tk.BOTH, expand=True)

        left = self._make_notebook(self.paned)
        right = self._make_notebook(self.paned)
        self.paned.add(left, stretch="always")
        self.paned.add(right, stretch="always")

        mid = len(tabs) // 2
        for text, widget in tabs[:mid]:
            left.add(widget, text=text)
        for text, widget in tabs[mid:]:
            right.add(widget, text=text)

        left.select(0)
        right.select(0)
        self.app.set_status("Layout: Left | Right — drag center bar to resize")

    def layout_v2(self):
        tabs = self._steal_tabs()
        if len(tabs) < 2:
            self._restore_tabs(tabs)
            self.app.set_status("Need at least 2 tabs to split")
            return
        self.current_layout = "v2"
        self.app.notebook.pack_forget()
        self._destroy_paned()

        self.paned = tk.PanedWindow(self.parent, orient=tk.VERTICAL,
                                     sashwidth=6, sashrelief=tk.RAISED,
                                     bg="#555555", opaqueresize=True)
        self.paned.pack(fill=tk.BOTH, expand=True)

        top = self._make_notebook(self.paned)
        bot = self._make_notebook(self.paned)
        self.paned.add(top, stretch="always")
        self.paned.add(bot, stretch="always")

        mid = len(tabs) // 2
        for text, widget in tabs[:mid]:
            top.add(widget, text=text)
        for text, widget in tabs[mid:]:
            bot.add(widget, text=text)

        top.select(0)
        bot.select(0)
        self.app.set_status("Layout: Top / Bottom — drag center bar to resize")

    def layout_quad(self):
        tabs = self._steal_tabs()
        if len(tabs) < 2:
            self._restore_tabs(tabs)
            self.app.set_status("Need at least 2 tabs to split")
            return
        self.current_layout = "quad"
        self.app.notebook.pack_forget()
        self._destroy_paned()

        self.paned = tk.PanedWindow(self.parent, orient=tk.VERTICAL,
                                     sashwidth=6, sashrelief=tk.RAISED,
                                     bg="#555555", opaqueresize=True)
        self.paned.pack(fill=tk.BOTH, expand=True)

        top_pw = tk.PanedWindow(self.paned, orient=tk.HORIZONTAL,
                                 sashwidth=6, sashrelief=tk.RAISED,
                                 bg="#555555", opaqueresize=True)
        bot_pw = tk.PanedWindow(self.paned, orient=tk.HORIZONTAL,
                                 sashwidth=6, sashrelief=tk.RAISED,
                                 bg="#555555", opaqueresize=True)
        self.paned.add(top_pw, stretch="always")
        self.paned.add(bot_pw, stretch="always")

        nbs = [self._make_notebook(top_pw), self._make_notebook(top_pw),
               self._make_notebook(bot_pw), self._make_notebook(bot_pw)]
        top_pw.add(nbs[0], stretch="always")
        top_pw.add(nbs[1], stretch="always")
        bot_pw.add(nbs[2], stretch="always")
        bot_pw.add(nbs[3], stretch="always")

        for i, (text, widget) in enumerate(tabs):
            nbs[i % 4].add(widget, text=text)

        for nb in nbs:
            if nb.tabs():
                nb.select(0)
        self.app.set_status("Layout: Quad (2×2) — drag any sash to resize")

    # ─── Internal helpers ─────────────────────────────────────

    def _make_notebook(self, parent):
        nb = ttk.Notebook(parent)
        nb.bind("<Button-3>", lambda e, n=nb: self._pane_tab_menu(e, n))
        self.notebooks.append(nb)
        return nb

    def _steal_tabs(self):
        self._collect_all_back()
        tabs = []
        while self.app.notebook.tabs():
            tab_id = self.app.notebook.tabs()[0]
            widget = self.app.notebook.nametowidget(tab_id)
            text = self.app.notebook.tab(tab_id, "text")
            self.app.notebook.forget(0)
            tabs.append((text, widget))
        return tabs

    def _restore_tabs(self, tabs):
        for text, widget in tabs:
            self.app.notebook.add(widget, text=text)
        self.app.notebook.pack(fill=tk.BOTH, expand=True)

    def _collect_all_back(self):
        collected = []
        for nb in self.notebooks:
            for tab_id in list(nb.tabs()):
                widget = nb.nametowidget(tab_id)
                text = nb.tab(tab_id, "text")
                nb.forget(tab_id)
                collected.append((text, widget))
        self._destroy_paned()
        for text, widget in collected:
            self.app.notebook.add(widget, text=text)

    def _destroy_paned(self):
        if self.paned:
            self.paned.destroy()
            self.paned = None
        self.notebooks.clear()
        self.panes.clear()

    def _pane_tab_menu(self, event, notebook):
        try:
            tab_idx = notebook.index(f"@{event.x},{event.y}")
        except Exception:
            return

        menu = tk.Menu(self.app.root, tearoff=0)
        menu.add_command(label="📤 Pop-out to Window",
                         command=lambda: self._popout_tab(notebook, tab_idx))

        for i, nb in enumerate(self.notebooks):
            if nb != notebook:
                menu.add_command(label=f"→ Move to Pane {i + 1}",
                                 command=lambda n=notebook, ti=tab_idx, target=nb:
                                 self._move_tab(n, ti, target))

        menu.add_separator()
        menu.add_command(label="✕ Close Tab",
                         command=lambda: self._close_tab(notebook, tab_idx))
        menu.add_separator()
        menu.add_command(label="⬜ Back to Single View", command=self.layout_single)
        menu.tk_popup(event.x_root, event.y_root)

    def _close_tab(self, notebook, idx):
        tab_id = notebook.tabs()[idx]
        widget = notebook.nametowidget(tab_id)
        if hasattr(widget, "on_close"):
            widget.on_close()
        notebook.forget(idx)

    def _move_tab(self, source_nb, tab_idx, target_nb):
        tab_id = source_nb.tabs()[tab_idx]
        widget = source_nb.nametowidget(tab_id)
        text = source_nb.tab(tab_id, "text")
        source_nb.forget(tab_idx)
        target_nb.add(widget, text=text)
        target_nb.select(widget)

    def _popout_tab(self, notebook, tab_idx):
        tab_id = notebook.tabs()[tab_idx]
        widget = notebook.nametowidget(tab_id)
        text = notebook.tab(tab_id, "text")
        notebook.forget(tab_idx)

        popup = tk.Toplevel(self.app.root)
        popup.title(f"EoSuite — {text}")
        popup.geometry("800x600")
        popup.minsize(400, 300)

        toolbar = ttk.Frame(popup)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="📥 Re-attach",
                   command=lambda: self._reattach(popup, widget, text)).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar, text="🔲 Fullscreen",
                   command=lambda: popup.attributes("-fullscreen",
                                                     not popup.attributes("-fullscreen"))
                   ).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar, text="📌 Stay on Top",
                   command=lambda: popup.attributes("-topmost",
                                                     not popup.attributes("-topmost"))
                   ).pack(side=tk.LEFT, padx=2, pady=2)
        spacer = ttk.Frame(toolbar)
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(toolbar, text="✕ Close",
                   command=popup.destroy).pack(side=tk.RIGHT, padx=2, pady=2)

        ttk.Separator(popup, orient=tk.HORIZONTAL).pack(fill=tk.X)
        widget.pack_forget()
        widget.master = popup
        widget.pack(fill=tk.BOTH, expand=True)
        popup.protocol("WM_DELETE_WINDOW",
                       lambda: self._on_popup_close(popup, widget, text))
        try:
            popup.iconbitmap(self.app.root.iconbitmap())
        except Exception:
            pass

    def _reattach(self, popup, widget, text):
        widget.pack_forget()
        widget.master = self.app.notebook
        self.app.notebook.add(widget, text=text)
        self.app.notebook.select(widget)
        popup.destroy()
        self.app.set_status(f"Re-attached: {text}")

    def _on_popup_close(self, popup, widget, text):
        if hasattr(widget, "on_close"):
            widget.on_close()
        popup.destroy()
