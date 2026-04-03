# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eWeb — Browser with rich HTML rendering, clickable links, and popup support.
Uses tkinter Text widget with tags for formatted display (headings, bold, links, lists).
"""
import re
import threading
import urllib.request
import urllib.error
import html.parser
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox


class RichHTMLParser(html.parser.HTMLParser):
    """Parse HTML into a list of (text, tags) segments for styled display."""

    def __init__(self):
        super().__init__()
        self.segments = []  # [(text, set_of_tags), ...]
        self.title = ""
        self.links = {}  # tag_name -> url
        self._link_count = 0
        self._tag_stack = []
        self._skip = False
        self._in_title = False
        self._in_pre = False
        self._list_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag in ("script", "style", "noscript", "svg", "path"):
            self._skip = True
            return
        if tag == "title":
            self._in_title = True
        if tag in ("pre", "code"):
            self._in_pre = True
            self._tag_stack.append("mono")
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.segments.append(("\n\n", set()))
            self._tag_stack.append(tag)
        if tag in ("p", "div", "section", "article", "header", "footer", "main"):
            self.segments.append(("\n", set()))
        if tag == "br":
            self.segments.append(("\n", set()))
        if tag in ("b", "strong"):
            self._tag_stack.append("bold")
        if tag in ("i", "em"):
            self._tag_stack.append("italic")
        if tag in ("u", "ins"):
            self._tag_stack.append("underline")
        if tag in ("ul", "ol"):
            self._list_depth += 1
        if tag == "li":
            indent = "  " * self._list_depth
            self.segments.append((f"\n{indent}• ", set()))
        if tag == "a" and "href" in attrs_dict:
            href = attrs_dict["href"]
            self._link_count += 1
            link_tag = f"link_{self._link_count}"
            self.links[link_tag] = href
            self._tag_stack.append(link_tag)
        if tag == "img":
            alt = attrs_dict.get("alt", "")
            src = attrs_dict.get("src", "")
            if alt:
                self.segments.append((f"[IMG: {alt}]", {"italic"}))
            elif src:
                short = src.split("/")[-1][:40]
                self.segments.append((f"[IMG: {short}]", {"italic"}))
        if tag == "hr":
            self.segments.append(("\n" + "─" * 60 + "\n", {"dim"}))
        if tag == "tr":
            self.segments.append(("\n", set()))
        if tag in ("td", "th"):
            self.segments.append(("\t", set()))
        if tag == "blockquote":
            self.segments.append(("\n│ ", {"italic"}))
            self._tag_stack.append("italic")
        if tag == "table":
            self.segments.append(("\n", set()))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg"):
            self._skip = False
            return
        if tag == "title":
            self._in_title = False
        if tag in ("pre", "code"):
            self._in_pre = False
            if "mono" in self._tag_stack:
                self._tag_stack.remove("mono")
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.segments.append(("\n", set()))
            if tag in self._tag_stack:
                self._tag_stack.remove(tag)
        if tag in ("b", "strong") and "bold" in self._tag_stack:
            self._tag_stack.remove("bold")
        if tag in ("i", "em") and "italic" in self._tag_stack:
            self._tag_stack.remove("italic")
        if tag in ("u", "ins") and "underline" in self._tag_stack:
            self._tag_stack.remove("underline")
        if tag in ("ul", "ol"):
            self._list_depth = max(0, self._list_depth - 1)
            self.segments.append(("\n", set()))
        if tag == "a":
            for t in reversed(self._tag_stack):
                if t.startswith("link_"):
                    self._tag_stack.remove(t)
                    break
        if tag == "blockquote" and "italic" in self._tag_stack:
            self._tag_stack.remove("italic")
            self.segments.append(("\n", set()))
        if tag == "p":
            self.segments.append(("\n", set()))

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        if self._skip:
            return
        text = data if self._in_pre else re.sub(r'\s+', ' ', data)
        if text:
            tags = set(self._tag_stack)
            self.segments.append((text, tags))

    def handle_entityref(self, name):
        entities = {"amp": "&", "lt": "<", "gt": ">", "quot": '"',
                    "apos": "'", "nbsp": " ", "mdash": "—", "ndash": "–",
                    "bull": "•", "copy": "©", "reg": "®", "trade": "™"}
        self.handle_data(entities.get(name, f"&{name};"))

    def handle_charref(self, name):
        try:
            if name.startswith("x"):
                ch = chr(int(name[1:], 16))
            else:
                ch = chr(int(name))
            self.handle_data(ch)
        except (ValueError, OverflowError):
            self.handle_data(f"&#{name};")


class EWeb(ttk.Frame):
    """Web browser with rich HTML rendering, clickable links, and popup support."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._history = []
        self._history_idx = -1
        self._current_links = {}
        self._popups = []
        self._build()

    def _build(self):
        c = self.app.theme.colors

        # Navigation bar
        nav = ttk.Frame(self, style="Toolbar.TFrame")
        nav.pack(fill=tk.X)

        ttk.Button(nav, text="◀", width=3, style="Toolbar.TButton",
                   command=self._go_back).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(nav, text="▶", width=3, style="Toolbar.TButton",
                   command=self._go_forward).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(nav, text="↻", width=3, style="Toolbar.TButton",
                   command=self._refresh).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(nav, text="🏠", width=3, style="Toolbar.TButton",
                   command=self._go_home).pack(side=tk.LEFT, padx=2, pady=2)

        self.url_var = tk.StringVar(value="https://")
        url_entry = ttk.Entry(nav, textvariable=self.url_var, font=("Consolas", 11))
        url_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=4, pady=2)
        url_entry.bind("<Return>", self._navigate)

        ttk.Button(nav, text="🔗 New Tab", style="Toolbar.TButton",
                   command=self._open_in_new_tab).pack(side=tk.RIGHT, padx=2, pady=2)
        ttk.Button(nav, text="📤 Pop-out", style="Toolbar.TButton",
                   command=self._open_popup).pack(side=tk.RIGHT, padx=2, pady=2)
        ttk.Button(nav, text="Go", style="Toolbar.TButton",
                   command=self._navigate).pack(side=tk.RIGHT, padx=4, pady=2)

        # Content area
        self.content = tk.Text(
            self, font=("Segoe UI", 11), bg=c["input_bg"], fg=c["input_fg"],
            insertbackground=c["input_fg"], wrap=tk.WORD, state=tk.DISABLED,
            relief=tk.FLAT, borderwidth=4, padx=10, pady=8, cursor="arrow")
        scrollbar = ttk.Scrollbar(self, command=self.content.yview)
        self.content.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content.pack(fill=tk.BOTH, expand=True)

        self._setup_tags()

        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=4)
        self.link_label = ttk.Label(status_frame, text="", foreground="#6688cc")
        self.link_label.pack(side=tk.RIGHT, padx=4)

    def _setup_tags(self):
        c = self.app.theme.colors
        t = self.content
        t.tag_configure("h1", font=("Segoe UI", 22, "bold"), spacing1=12, spacing3=6)
        t.tag_configure("h2", font=("Segoe UI", 18, "bold"), spacing1=10, spacing3=5)
        t.tag_configure("h3", font=("Segoe UI", 15, "bold"), spacing1=8, spacing3=4)
        t.tag_configure("h4", font=("Segoe UI", 13, "bold"), spacing1=6, spacing3=3)
        t.tag_configure("h5", font=("Segoe UI", 12, "bold"), spacing1=4, spacing3=2)
        t.tag_configure("h6", font=("Segoe UI", 11, "bold"), spacing1=4, spacing3=2)
        t.tag_configure("bold", font=("Segoe UI", 11, "bold"))
        t.tag_configure("italic", font=("Segoe UI", 11, "italic"))
        t.tag_configure("underline", underline=True)
        t.tag_configure("mono", font=("Consolas", 10), background="#2a2a2a" if c["bg"].startswith("#1") or c["bg"].startswith("#2") else "#f0f0f0")
        t.tag_configure("dim", foreground="#888888")

    def _make_link_tag(self, tag_name, url):
        fg = "#58a6ff" if self.app.theme.is_dark else "#0366d6"
        self.content.tag_configure(tag_name, foreground=fg, underline=True)
        self.content.tag_bind(tag_name, "<Enter>",
                              lambda e, u=url: self._on_link_enter(u))
        self.content.tag_bind(tag_name, "<Leave>",
                              lambda e: self._on_link_leave())
        self.content.tag_bind(tag_name, "<Button-1>",
                              lambda e, u=url: self._on_link_click(u))
        self.content.tag_bind(tag_name, "<Button-3>",
                              lambda e, u=url: self._on_link_right_click(e, u))

    def _on_link_enter(self, url):
        self.content.configure(cursor="hand2")
        self.link_label.config(text=url[:100])

    def _on_link_leave(self):
        self.content.configure(cursor="arrow")
        self.link_label.config(text="")

    def _on_link_click(self, url):
        resolved = self._resolve_url(url)
        self.url_var.set(resolved)
        self._navigate()

    def _on_link_right_click(self, event, url):
        resolved = self._resolve_url(url)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Open in new popup", command=lambda: self._open_url_popup(resolved))
        menu.add_command(label="Copy URL", command=lambda: self._copy_url(resolved))
        menu.tk_popup(event.x_root, event.y_root)

    def _resolve_url(self, url):
        if url.startswith(("http://", "https://")):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            base = self.url_var.get()
            from urllib.parse import urlparse
            p = urlparse(base)
            return f"{p.scheme}://{p.netloc}{url}"
        base = self.url_var.get()
        if not base.endswith("/"):
            base = base.rsplit("/", 1)[0] + "/"
        return base + url

    def _copy_url(self, url):
        self.clipboard_clear()
        self.clipboard_append(url)
        self.status_label.config(text="URL copied to clipboard")

    def _navigate(self, _event=None):
        url = self.url_var.get().strip()
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self.url_var.set(url)

        self.status_label.config(text=f"Loading {url}...")
        self.update_idletasks()

        thread = threading.Thread(target=self._fetch_and_render, args=(url,), daemon=True)
        thread.start()

    def _fetch_and_render(self, url):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EoSuite-eWeb/1.0",
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Language": "en-US,en;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode("utf-8", errors="replace")

            parser = RichHTMLParser()
            parser.feed(data)

            self.after(0, lambda: self._render_page(url, parser))
        except Exception as e:
            self.after(0, lambda: self._render_error(url, str(e)))

    def _render_page(self, url, parser):
        self.content.config(state=tk.NORMAL)
        self.content.delete("1.0", tk.END)

        self._current_links = parser.links

        for text, tags in parser.segments:
            if not text:
                continue
            tag_tuple = tuple(tags) if tags else ()

            # Configure link tags
            for t in tags:
                if t.startswith("link_") and t in parser.links:
                    self._make_link_tag(t, parser.links[t])

            self.content.insert(tk.END, text, tag_tuple)

        self.content.config(state=tk.DISABLED)

        # Update history
        if self._history_idx < len(self._history) - 1:
            self._history = self._history[:self._history_idx + 1]
        self._history.append(url)
        self._history_idx = len(self._history) - 1

        title = parser.title or url
        self.status_label.config(text=f"Loaded: {title}")

    def _render_error(self, url, error):
        self.content.config(state=tk.NORMAL)
        self.content.delete("1.0", tk.END)
        self.content.insert("1.0", f"Error loading page:\n\n{error}\n\nURL: {url}", ("bold",))
        self.content.config(state=tk.DISABLED)
        self.status_label.config(text=f"Error: {error}")

    def _go_back(self):
        if self._history_idx > 0:
            self._history_idx -= 1
            self.url_var.set(self._history[self._history_idx])
            self._navigate()

    def _go_forward(self):
        if self._history_idx < len(self._history) - 1:
            self._history_idx += 1
            self.url_var.set(self._history[self._history_idx])
            self._navigate()

    def _refresh(self):
        self._navigate()

    def _go_home(self):
        self.url_var.set("https://www.google.com")
        self._navigate()

    def _open_popup(self):
        """Open current page in a popup window."""
        url = self.url_var.get().strip()
        if url and url != "https://":
            self._open_url_popup(url)

    def _open_url_popup(self, url):
        """Open a URL in a standalone popup browser window."""
        popup = tk.Toplevel(self)
        popup.title(f"eWeb — {url[:60]}")
        popup.geometry("900x650")
        popup.minsize(500, 400)
        self._popups.append(popup)

        # Mini nav bar in popup
        nav = ttk.Frame(popup)
        nav.pack(fill=tk.X)
        popup_url = tk.StringVar(value=url)
        ttk.Entry(nav, textvariable=popup_url, font=("Consolas", 10)).pack(
            fill=tk.X, expand=True, side=tk.LEFT, padx=4, pady=2)
        ttk.Button(nav, text="✕ Close", command=popup.destroy).pack(side=tk.RIGHT, padx=4)

        content = tk.Text(popup, font=("Segoe UI", 11), wrap=tk.WORD,
                          state=tk.DISABLED, padx=10, pady=8)
        scroll = ttk.Scrollbar(popup, command=content.yview)
        content.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        content.pack(fill=tk.BOTH, expand=True)

        status = ttk.Label(popup, text="Loading...")
        status.pack(fill=tk.X, side=tk.BOTTOM)

        def fetch():
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 EoSuite-eWeb/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read().decode("utf-8", errors="replace")
                parser = RichHTMLParser()
                parser.feed(data)

                def render():
                    content.config(state=tk.NORMAL)
                    for text, tags in parser.segments:
                        if text:
                            content.insert(tk.END, text)
                    content.config(state=tk.DISABLED)
                    status.config(text=f"Loaded: {parser.title or url}")
                    popup.title(f"eWeb — {parser.title or url[:40]}")

                popup.after(0, render)
            except Exception as e:
                popup.after(0, lambda: status.config(text=f"Error: {e}"))

        threading.Thread(target=fetch, daemon=True).start()

    def _open_in_new_tab(self):
        """Open URL in a new eWeb tab."""
        url = self.url_var.get().strip()
        if not url or url == "https://":
            return
        new_tab = EWeb(self.app.notebook, self.app)
        self.app.notebook.add(new_tab, text=f"🌐 eWeb (2)")
        self.app.notebook.select(new_tab)
        new_tab.url_var.set(url)
        new_tab._navigate()

    def on_close(self):
        for p in self._popups:
            try:
                p.destroy()
            except Exception:
                pass
