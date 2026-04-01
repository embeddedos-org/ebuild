# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EWeb — HTML parser and browser navigation logic.
"""
import tkinter as tk
import pytest


class TestRichHTMLParser:
    """Test the RichHTMLParser without GUI."""

    def _parse(self, html):
        from gui.apps.eweb import RichHTMLParser
        p = RichHTMLParser()
        p.feed(html)
        return p

    def test_plain_text(self):
        p = self._parse("<p>Hello world</p>")
        text = "".join(t for t, _ in p.segments)
        assert "Hello world" in text

    def test_title_extraction(self):
        p = self._parse("<html><head><title>My Page</title></head><body></body></html>")
        assert p.title == "My Page"

    def test_heading_tags(self):
        p = self._parse("<h1>Big Title</h1>")
        found = False
        for text, tags in p.segments:
            if "Big Title" in text and "h1" in tags:
                found = True
        assert found

    def test_bold_tag(self):
        p = self._parse("<b>Bold Text</b>")
        found = False
        for text, tags in p.segments:
            if "Bold Text" in text and "bold" in tags:
                found = True
        assert found

    def test_italic_tag(self):
        p = self._parse("<i>Italic Text</i>")
        found = False
        for text, tags in p.segments:
            if "Italic Text" in text and "italic" in tags:
                found = True
        assert found

    def test_link_extraction(self):
        p = self._parse('<a href="https://example.com">Click me</a>')
        assert len(p.links) >= 1
        assert any("https://example.com" in url for url in p.links.values())

    def test_script_tags_skipped(self):
        p = self._parse("<script>alert('xss')</script><p>Visible</p>")
        text = "".join(t for t, _ in p.segments)
        assert "alert" not in text
        assert "Visible" in text

    def test_style_tags_skipped(self):
        p = self._parse("<style>body{color:red}</style><p>Content</p>")
        text = "".join(t for t, _ in p.segments)
        assert "color:red" not in text
        assert "Content" in text

    def test_list_items(self):
        p = self._parse("<ul><li>Item 1</li><li>Item 2</li></ul>")
        text = "".join(t for t, _ in p.segments)
        assert "Item 1" in text
        assert "Item 2" in text

    def test_br_newline(self):
        p = self._parse("Line1<br>Line2")
        text = "".join(t for t, _ in p.segments)
        assert "Line1" in text
        assert "Line2" in text

    def test_img_alt(self):
        p = self._parse('<img alt="Logo" src="logo.png">')
        text = "".join(t for t, _ in p.segments)
        assert "Logo" in text

    def test_img_no_alt(self):
        p = self._parse('<img src="photo.jpg">')
        text = "".join(t for t, _ in p.segments)
        assert "IMG" in text

    def test_entity_amp(self):
        p = self._parse("<p>A &amp; B</p>")
        text = "".join(t for t, _ in p.segments)
        assert "&" in text

    def test_entity_lt_gt(self):
        p = self._parse("<p>&lt;tag&gt;</p>")
        text = "".join(t for t, _ in p.segments)
        assert "<tag>" in text

    def test_charref_decimal(self):
        p = self._parse("<p>&#65;</p>")
        text = "".join(t for t, _ in p.segments)
        assert "A" in text

    def test_charref_hex(self):
        p = self._parse("<p>&#x41;</p>")
        text = "".join(t for t, _ in p.segments)
        assert "A" in text

    def test_hr_produces_line(self):
        p = self._parse("<hr>")
        text = "".join(t for t, _ in p.segments)
        assert "─" in text

    def test_pre_tag_preserves_mono(self):
        p = self._parse("<pre>code here</pre>")
        found = False
        for text, tags in p.segments:
            if "code here" in text and "mono" in tags:
                found = True
        assert found

    def test_empty_html(self):
        p = self._parse("")
        assert p.title == ""
        assert len(p.links) == 0

    def test_multiple_links(self):
        p = self._parse('<a href="u1">A</a> <a href="u2">B</a>')
        assert len(p.links) == 2

    def test_underline_tag(self):
        p = self._parse("<u>Underlined</u>")
        found = False
        for text, tags in p.segments:
            if "Underlined" in text and "underline" in tags:
                found = True
        assert found

    def test_blockquote(self):
        p = self._parse("<blockquote>Quoted text</blockquote>")
        text = "".join(t for t, _ in p.segments)
        assert "Quoted text" in text


def _colors():
    return {
        "bg": "#1e1e1e", "fg": "#d4d4d4", "accent": "#0078d4",
        "sidebar_bg": "#252526", "toolbar_bg": "#2d2d2d",
        "tab_bg": "#2d2d2d", "tab_active": "#1e1e1e",
        "input_bg": "#3c3c3c", "input_fg": "#d4d4d4",
        "border": "#3c3c3c", "hover": "#094771",
        "button_bg": "#0e639c", "button_fg": "#ffffff",
        "status_bg": "#007acc", "status_fg": "#ffffff",
        "tree_bg": "#252526", "tree_fg": "#cccccc",
        "tree_select": "#094771", "menu_bg": "#2d2d2d",
        "menu_fg": "#cccccc", "terminal_bg": "#0c0c0c",
        "terminal_fg": "#cccccc",
    }


@pytest.mark.gui
class TestEWebBrowser:
    def _make_browser(self, tk_root):
        from gui.apps.eweb import EWeb
        return EWeb(tk_root, type("App", (), {
            "theme": type("T", (), {"colors": _colors(), "is_dark": True})(),
            "set_status": lambda self, t: None,
            "notebook": tk_root,
        })())

    def test_initial_url(self, tk_root):
        b = self._make_browser(tk_root)
        assert b.url_var.get() == "https://"

    def test_history_empty(self, tk_root):
        b = self._make_browser(tk_root)
        assert b._history == []
        assert b._history_idx == -1

    def test_resolve_url_absolute(self, tk_root):
        b = self._make_browser(tk_root)
        assert b._resolve_url("https://example.com") == "https://example.com"

    def test_resolve_url_protocol_relative(self, tk_root):
        b = self._make_browser(tk_root)
        assert b._resolve_url("//cdn.example.com/file") == "https://cdn.example.com/file"

    def test_resolve_url_absolute_path(self, tk_root):
        b = self._make_browser(tk_root)
        b.url_var.set("https://example.com/page")
        assert b._resolve_url("/about") == "https://example.com/about"

    def test_content_is_readonly(self, tk_root):
        b = self._make_browser(tk_root)
        assert str(b.content.cget("state")) == "disabled"

    def test_render_error_shows_message(self, tk_root):
        b = self._make_browser(tk_root)
        b._render_error("https://fail.com", "Connection refused")
        content = b.content.get("1.0", tk.END)
        assert "Connection refused" in content

    def test_go_back_at_start(self, tk_root):
        b = self._make_browser(tk_root)
        b._go_back()  # should not raise

    def test_go_forward_at_end(self, tk_root):
        b = self._make_browser(tk_root)
        b._go_forward()  # should not raise

    def test_on_close_no_error(self, tk_root):
        b = self._make_browser(tk_root)
        b.on_close()  # should not raise

    def test_popups_list_empty(self, tk_root):
        b = self._make_browser(tk_root)
        assert b._popups == []
