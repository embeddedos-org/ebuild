# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Main Window — Application frame with MobaXterm-style layout.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from gui.styles import ThemeManager
from gui.toolbar import Toolbar
from gui.sidebar import Sidebar
from gui.home_tab import HomeTab
from gui.split_manager import SplitManager


class MainWindow:
    APP_TITLE = "EoSuite"
    DEFAULT_SIZE = "1200x750"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(self.APP_TITLE)
        self.root.geometry(self.DEFAULT_SIZE)
        self.root.minsize(800, 500)

        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except tk.TclError:
                pass

        self.theme = ThemeManager(self.root)
        self._build_menu()

        self.toolbar = Toolbar(self.root, self)
        self.toolbar.pack(fill=tk.X)
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X)

        self.content = ttk.Frame(self.root)
        self.content.pack(fill=tk.BOTH, expand=True)

        self.sidebar = Sidebar(self.content, self)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Separator(self.content, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y)

        self.notebook = ttk.Notebook(self.content)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind("<Button-3>", self._tab_right_click)

        self.split_mgr = SplitManager(self.content, self)

        self.status_frame = ttk.Frame(self.root, style="Status.TFrame")
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_label = ttk.Label(self.status_frame, text="  Ready", style="Status.TLabel")
        self.status_label.pack(side=tk.LEFT, padx=4, pady=2)
        self.status_right = ttk.Label(self.status_frame, text="Dark Theme  ", style="Status.TLabel")
        self.status_right.pack(side=tk.RIGHT, padx=4, pady=2)

        self.home_tab = HomeTab(self.notebook, self)
        self.notebook.add(self.home_tab, text="🏠 Home")

        self.session_mgr = None
        self._bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self._load_sessions()

    def _build_menu(self):
        c = self.theme.colors
        menubar = tk.Menu(self.root, bg=c["menu_bg"], fg=c["menu_fg"],
                          activebackground=c["hover"], activeforeground=c["fg"], relief=tk.FLAT)

        m_term = tk.Menu(menubar, tearoff=0)
        m_term.add_command(label="New Local Terminal", command=self.start_local_terminal, accelerator="Ctrl+N")
        m_term.add_command(label="New SSH Session", command=self.new_session, accelerator="Ctrl+Shift+S")
        m_term.add_command(label="New Serial Connection", command=self.new_serial)
        m_term.add_separator()
        m_term.add_command(label="Exit", command=self.exit_app, accelerator="Alt+F4")
        menubar.add_cascade(label="Terminal", menu=m_term)

        m_sess = tk.Menu(menubar, tearoff=0)
        m_sess.add_command(label="New SSH Session", command=self.new_session)
        m_sess.add_command(label="New Serial Connection", command=self.new_serial)
        m_sess.add_separator()
        m_sess.add_command(label="Manage Sessions", command=self._manage_sessions)
        m_sess.add_command(label="Recover Sessions", command=self.recover_sessions)
        menubar.add_cascade(label="Sessions", menu=m_sess)

        m_view = tk.Menu(menubar, tearoff=0)
        m_view.add_command(label="Toggle Sidebar", command=self.toggle_view)
        m_view.add_command(label="Toggle Toolbar", command=self.toggle_toolbar, accelerator="Ctrl+B")
        m_view.add_command(label="Toggle Theme", command=self.toggle_theme)
        m_view.add_separator()
        m_view.add_command(label="⬜ Single View", command=lambda: self.split_mgr.layout_single())
        m_view.add_command(label="⬛⬛ Split Horizontal", command=lambda: self.split_mgr.layout_h2())
        m_view.add_command(label="⬛/⬛ Split Vertical", command=lambda: self.split_mgr.layout_v2())
        m_view.add_command(label="⊞ Quad View", command=lambda: self.split_mgr.layout_quad())
        m_view.add_separator()
        m_view.add_command(label="📤 Pop-out Current Tab", command=lambda: self.split_mgr.popout_current())
        m_view.add_separator()
        m_view.add_command(label="Full Screen", command=self._toggle_fullscreen, accelerator="F11")
        menubar.add_cascade(label="View", menu=m_view)

        m_tools = tk.Menu(menubar, tearoff=0)
        for label, cmd in [
            ("🧮 eCal", self.open_ecal),
            ("⏱ eTimer", self.open_etimer),
            ("📝 eNote", self.open_enote),
            ("🔢 eViewer", self.open_eviewer),
            ("🛡 eGuard", self.open_eguard),
            ("🌐 eWeb", self.open_eweb),
            ("📦 eZip", self.open_ezip),
            ("🧹 eCleaner", self.open_ecleaner),
            ("🔒 eVPN", self.open_evpn),
            ("💬 eChat", self.open_echat),
            ("🎨 ePaint", self.open_epaint),
            ("▶ ePlay", self.open_eplay),
            ("📋 eBuffer", self.open_ebuffer),
            ("🔄 eConverter", self.open_econverter),
            ("📄 ePDF", self.open_epdf),
            ("📂 eFTP", self.open_eftp),
            ("🚇 eTunnel", self.open_etunnel),
            ("🛡 eVirusTowerClient", self.open_evirustower),
            ("🖥 eVNC", self.open_evnc),
            ("🕐 eClock", self.open_eclock),
        ]:
            m_tools.add_command(label=label, command=cmd)
        menubar.add_cascade(label="Tools", menu=m_tools)

        m_games = tk.Menu(menubar, tearoff=0)
        for label, cmd in [
            ("🐍 Snake", self.open_snake),
            ("🧱 Tetris", self.open_tetris),
            ("💣 Minesweeper", self.open_minesweeper),
            ("🎲 Dice", self.open_dice),
            ("♟ Chess", self.open_chess),
        ]:
            m_games.add_command(label=label, command=cmd)
        menubar.add_cascade(label="Games", menu=m_games)

        m_settings = tk.Menu(menubar, tearoff=0)
        m_settings.add_command(label="Toggle Theme", command=self.toggle_theme)
        m_settings.add_command(label="Preferences", command=self.open_settings)
        menubar.add_cascade(label="Settings", menu=m_settings)

        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label="About EoSuite", command=self._show_about)
        m_help.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        menubar.add_cascade(label="Help", menu=m_help)

        self.root.config(menu=menubar)

    def _bind_shortcuts(self):
        self.root.bind("<Control-n>", lambda e: self.start_local_terminal())
        self.root.bind("<Control-t>", lambda e: self.start_local_terminal())
        self.root.bind("<Control-Shift-S>", lambda e: self.new_session())
        self.root.bind("<Control-b>", lambda e: self.toggle_view())
        self.root.bind("<Control-Shift-T>", lambda e: self.toggle_toolbar())
        self.root.bind("<Control-w>", lambda e: self._close_current_tab())
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())

    def _get_session_mgr(self):
        if self.session_mgr is None:
            from gui.apps.session_manager import SessionManager
            self.session_mgr = SessionManager()
        return self.session_mgr

    def _load_sessions(self):
        try:
            mgr = self._get_session_mgr()
            sessions = mgr.load_sessions()
            for s in sessions:
                stype = s.get("type", "ssh")
                name = s.get("name", "Unnamed")
                conn = s.get("connection", "")
                if stype == "ssh":
                    self.sidebar.add_ssh_session(name, conn)
                elif stype == "serial":
                    self.sidebar.add_serial_session(name, conn)
                else:
                    self.sidebar.add_local_session(name, conn)
            self.home_tab.load_recent_sessions(sessions)
        except Exception:
            pass

    def start_local_terminal(self):
        from gui.terminal_tab import TerminalTab
        tab = TerminalTab(self.notebook, self)
        self.notebook.add(tab, text="💻 Terminal")
        self.notebook.select(tab)
        self.set_status("Local terminal started")

    def new_session(self):
        from gui.apps.ssh_client import SSHDialog
        SSHDialog(self.root, self)

    def new_serial(self):
        from gui.apps.serial_term import SerialDialog
        SerialDialog(self.root, self)

    def connect_session(self, connection_str, name=""):
        if connection_str == "local":
            self.start_local_terminal()
            return
        from gui.terminal_tab import TerminalTab
        tab = TerminalTab(self.notebook, self, command=connection_str)
        display = name or connection_str
        self.notebook.add(tab, text=f"🔐 {display}")
        self.notebook.select(tab)
        self.set_status(f"Connected: {display}")

    def recover_sessions(self):
        try:
            mgr = self._get_session_mgr()
            sessions = mgr.load_sessions()
            if not sessions:
                messagebox.showinfo("Recover Sessions", "No saved sessions found.")
                return
            for s in sessions:
                self.connect_session(s.get("connection", ""), s.get("name", ""))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def search_sessions(self, query):
        self.set_status(f"Searching: {query}")
        try:
            mgr = self._get_session_mgr()
            results = mgr.search(query)
            self.home_tab.load_recent_sessions(results)
        except Exception:
            pass

    def _manage_sessions(self):
        from gui.apps.session_manager import SessionManagerDialog
        SessionManagerDialog(self.root, self)

    def _open_tool_tab(self, module_path, class_name, title):
        # Check if tab with this title already exists — focus it instead
        # Use stripped comparison to handle emoji rendering differences
        title_key = title.strip()
        for tab_id in self.notebook.tabs():
            existing = self.notebook.tab(tab_id, "text").strip()
            if existing == title_key or existing.endswith(title_key.lstrip("\U0001f000-\U0001ffff ")):
                self.notebook.select(tab_id)
                self.set_status(f"Focused: {title}")
                return
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        tab = cls(self.notebook, self)
        self.notebook.add(tab, text=title)
        self.notebook.select(tab)
        self.set_status(f"Opened {title}")

    def open_ecal(self):
        self._open_tool_tab("gui.apps.ecal", "ECal", "🧮 eCal")

    def open_etimer(self):
        self._open_tool_tab("gui.apps.etimer", "ETimer", "⏱ eTimer")

    def open_enote(self):
        self._open_tool_tab("gui.apps.enote", "ENote", "📝 eNote")

    def open_eviewer(self):
        self._open_tool_tab("gui.apps.eviewer", "EViewer", "🔢 eViewer")

    def open_eguard(self):
        self._open_tool_tab("gui.apps.eguard", "EGuard", "🛡 eGuard")

    def open_eweb(self):
        self._open_tool_tab("gui.apps.eweb", "EWeb", "🌐 eWeb")

    def open_ezip(self):
        self._open_tool_tab("gui.apps.ezip", "EZip", "📦 eZip")

    def open_ecleaner(self):
        self._open_tool_tab("gui.apps.ecleaner", "ECleaner", "🧹 eCleaner")

    def open_evpn(self):
        self._open_tool_tab("gui.apps.evpn", "EVpn", "🔒 eVPN")

    def open_echat(self):
        self._open_tool_tab("gui.apps.echat", "EChat", "💬 eChat")

    def open_epaint(self):
        self._open_tool_tab("gui.apps.epaint", "EPaint", "🎨 ePaint")

    def open_eplay(self):
        self._open_tool_tab("gui.apps.eplay", "EPlay", "▶ ePlay")

    def open_ebuffer(self):
        self._open_tool_tab("gui.apps.ebuffer", "EBuffer", "📋 eBuffer")

    def open_econverter(self):
        self._open_tool_tab("gui.apps.econverter", "EConverter", "🔄 eConverter")

    def open_epdf(self):
        self._open_tool_tab("gui.apps.epdf", "EPdf", "📄 ePDF")

    def open_eftp(self):
        self._open_tool_tab("gui.apps.eftp", "EFTP", "📂 eFTP")

    def open_etunnel(self):
        self._open_tool_tab("gui.apps.etunnel", "ETunnel", "🚇 eTunnel")

    def open_evirustower(self):
        self._open_tool_tab("gui.apps.evirustower", "EVirusTower", "🛡 eVirusTowerClient")

    def open_evnc(self):
        self._open_tool_tab("gui.apps.evnc", "EVnc", "🖥 eVNC")

    def open_eclock(self):
        self._open_tool_tab("gui.apps.eclock", "EClock", "🕐 eClock")

    def open_snake(self):
        self._open_tool_tab("gui.apps.snake", "SnakeGame", "🐍 Snake")

    def open_tetris(self):
        self._open_tool_tab("gui.apps.tetris", "Tetris", "🧱 Tetris")

    def open_minesweeper(self):
        self._open_tool_tab("gui.apps.minesweeper", "Minesweeper", "💣 Minesweeper")

    def open_dice(self):
        self._open_tool_tab("gui.apps.dice", "DiceRoller", "🎲 Dice")

    def open_chess(self):
        self._open_tool_tab("gui.apps.chess", "Chess", "♟ Chess")

    def servers(self):
        messagebox.showinfo("Servers", "Server management coming soon.")

    def tools_menu(self):
        pass

    def games_menu(self):
        self.open_snake()

    def toggle_view(self):
        self.sidebar.toggle()

    def toggle_toolbar(self):
        if self.toolbar.winfo_viewable():
            self.toolbar.pack_forget()
            self.set_status("Toolbar hidden")
        else:
            self.toolbar.pack(fill="x", before=self.content)
            self.set_status("Toolbar visible")

    def split_view(self):
        self.split_mgr.show_split_menu()

    def open_settings(self):
        messagebox.showinfo("Settings", "Preferences panel coming in a future update.")

    def open_help(self):
        self._show_about()

    def toggle_theme(self):
        self.theme.toggle()
        mode = "Dark" if self.theme.is_dark else "Light"
        self.status_right.config(text=f"{mode} Theme  ")
        self.set_status(f"Switched to {mode} theme")

    def exit_app(self):
        if messagebox.askokcancel("Exit", "Close EoSuite?"):
            self.root.destroy()

    def _close_current_tab(self):
        current = self.notebook.select()
        if current:
            idx = self.notebook.index(current)
            if idx == 0:
                return
            tab_widget = self.notebook.nametowidget(current)
            if hasattr(tab_widget, "on_close"):
                tab_widget.on_close()
            self.notebook.forget(current)

    def _tab_right_click(self, event):
        """Right-click on a tab for context menu (close, pop-out, move)."""
        try:
            tab_idx = self.notebook.index(f"@{event.x},{event.y}")
        except Exception:
            return

        menu = tk.Menu(self.root, tearoff=0)
        if tab_idx > 0:  # Don't allow closing/popping Home tab
            menu.add_command(label="📤 Pop-out to Window",
                             command=lambda: self.split_mgr._popout_tab(self.notebook, tab_idx))
            menu.add_command(label="📋 Duplicate Tab",
                             command=lambda: self._duplicate_tab(tab_idx))
            menu.add_separator()
            menu.add_command(label="✕ Close Tab",
                             command=lambda: self._close_tab_at(tab_idx))
            menu.add_command(label="✕ Close Other Tabs",
                             command=lambda: self._close_other_tabs(tab_idx))
            menu.add_command(label="✕ Close All Tabs",
                             command=self._close_all_tabs)
        menu.tk_popup(event.x_root, event.y_root)

    def _close_tab_at(self, idx):
        """Close tab at specific index."""
        tab_id = self.notebook.tabs()[idx]
        widget = self.notebook.nametowidget(tab_id)
        if hasattr(widget, "on_close"):
            widget.on_close()
        self.notebook.forget(idx)

    def _close_other_tabs(self, keep_idx):
        """Close all tabs except Home and the specified one."""
        tabs = list(self.notebook.tabs())
        for i in range(len(tabs) - 1, 0, -1):  # Skip Home at 0
            if i != keep_idx:
                widget = self.notebook.nametowidget(tabs[i])
                if hasattr(widget, "on_close"):
                    widget.on_close()
                self.notebook.forget(tabs[i])

    def _close_all_tabs(self):
        """Close all tabs except Home."""
        tabs = list(self.notebook.tabs())
        for i in range(len(tabs) - 1, 0, -1):
            widget = self.notebook.nametowidget(tabs[i])
            if hasattr(widget, "on_close"):
                widget.on_close()
            self.notebook.forget(tabs[i])

    def _duplicate_tab(self, idx):
        """Duplicate a tab — for tools, temporarily allow a second instance."""
        tab_id = self.notebook.tabs()[idx]
        text = self.notebook.tab(tab_id, "text")
        if "Terminal" in text:
            self.start_local_terminal()
            return
        # For tools, force-open a new instance by using a numbered title
        title_map = {
            "eCal": ("gui.apps.ecal", "ECal"),
            "eTimer": ("gui.apps.etimer", "ETimer"),
            "eNote": ("gui.apps.enote", "ENote"),
            "eViewer": ("gui.apps.eviewer", "EViewer"),
            "eGuard": ("gui.apps.eguard", "EGuard"),
            "eWeb": ("gui.apps.eweb", "EWeb"),
            "eZip": ("gui.apps.ezip", "EZip"),
            "eCleaner": ("gui.apps.ecleaner", "ECleaner"),
            "eVPN": ("gui.apps.evpn", "EVpn"),
            "eChat": ("gui.apps.echat", "EChat"),
            "ePaint": ("gui.apps.epaint", "EPaint"),
            "ePlay": ("gui.apps.eplay", "EPlay"),
            "eBuffer": ("gui.apps.ebuffer", "EBuffer"),
            "eConverter": ("gui.apps.econverter", "EConverter"),
            "ePDF": ("gui.apps.epdf", "EPdf"),
            "eFTP": ("gui.apps.eftp", "EFTP"),
            "eTunnel": ("gui.apps.etunnel", "ETunnel"),
            "eVirusTowerClient": ("gui.apps.evirustower", "EVirusTower"),
            "Snake": ("gui.apps.snake", "SnakeGame"),
            "eClock": ("gui.apps.eclock", "EClock"),
            "Tetris": ("gui.apps.tetris", "Tetris"),
            "Minesweeper": ("gui.apps.minesweeper", "Minesweeper"),
            "Dice": ("gui.apps.dice", "DiceRoller"),
            "Chess": ("gui.apps.chess", "Chess"),
        }
        for key, (mod_path, cls_name) in title_map.items():
            if key in text:
                import importlib
                mod = importlib.import_module(mod_path)
                cls = getattr(mod, cls_name)
                tab = cls(self.notebook, self)
                self.notebook.add(tab, text=f"{text} (2)")
                self.notebook.select(tab)
                return

    def _toggle_fullscreen(self):
        fs = self.root.attributes("-fullscreen")
        self.root.attributes("-fullscreen", not fs)

    def set_status(self, text):
        self.status_label.config(text=f"  {text}")

    def _show_about(self):
        messagebox.showinfo("About EoSuite",
                            "EoSuite v1.1.0\n\nMulti-tool terminal suite\n"
                            "SSH • Serial • Tools • Games\n\n"
                            "Built with Python + tkinter\nCross-platform: Windows, macOS, Linux")

    def _show_shortcuts(self):
        messagebox.showinfo("Keyboard Shortcuts",
                            "Ctrl+N / Ctrl+T — New local terminal\n"
                            "Ctrl+Shift+S — New SSH session\nCtrl+B — Toggle sidebar\n"
                            "Ctrl+W — Close current tab\nF11 — Toggle fullscreen\nAlt+F4 — Exit")

    def run(self):
        self.root.mainloop()

    @classmethod
    def launch(cls):
        app = cls()
        app.run()
