# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for EZip — Archive manager zip/tar operations.
"""
import os
import zipfile
import pytest


class TestEZipArchiveOps:
    """Test archive operations without GUI."""

    def test_create_and_read_zip(self, tmp_path):
        src = tmp_path / "hello.txt"
        src.write_text("Hello World")
        archive = str(tmp_path / "test.zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(str(src), "hello.txt")
        assert zipfile.is_zipfile(archive)
        with zipfile.ZipFile(archive, "r") as zf:
            names = zf.namelist()
            assert "hello.txt" in names

    def test_zip_multiple_files(self, tmp_path):
        for i in range(3):
            (tmp_path / f"file{i}.txt").write_text(f"Content {i}")
        archive = str(tmp_path / "multi.zip")
        with zipfile.ZipFile(archive, "w") as zf:
            for i in range(3):
                zf.write(str(tmp_path / f"file{i}.txt"), f"file{i}.txt")
        with zipfile.ZipFile(archive, "r") as zf:
            assert len(zf.namelist()) == 3

    def test_zip_extract(self, tmp_path):
        src = tmp_path / "data.txt"
        src.write_text("Extract me")
        archive = str(tmp_path / "extract.zip")
        with zipfile.ZipFile(archive, "w") as zf:
            zf.write(str(src), "data.txt")
        extract_dir = tmp_path / "output"
        extract_dir.mkdir()
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(str(extract_dir))
        assert (extract_dir / "data.txt").read_text() == "Extract me"

    def test_zip_append(self, tmp_path):
        archive = str(tmp_path / "append.zip")
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("first.txt", "First")
        with zipfile.ZipFile(archive, "a") as zf:
            zf.writestr("second.txt", "Second")
        with zipfile.ZipFile(archive, "r") as zf:
            assert len(zf.namelist()) == 2

    def test_is_zipfile_false(self, tmp_path):
        not_zip = tmp_path / "notzip.txt"
        not_zip.write_text("This is not a zip")
        assert not zipfile.is_zipfile(str(not_zip))


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
class TestEZipGUI:
    def _make_ezip(self, tk_root):
        from gui.apps.ezip import EZip
        return EZip(tk_root, type("App", (), {
            "theme": type("T", (), {"colors": _colors()})(),
            "set_status": lambda self, t: None,
        })())

    def test_initial_state(self, tk_root):
        z = self._make_ezip(tk_root)
        assert z._archive_path is None

    def test_tree_columns(self, tk_root):
        z = self._make_ezip(tk_root)
        cols = z.tree.cget("columns")
        assert "Name" in cols
        assert "Size" in cols

    def test_info_label_initial(self, tk_root):
        z = self._make_ezip(tk_root)
        assert "No archive" in z.info_label.cget("text")

    def test_has_required_methods(self, tk_root):
        z = self._make_ezip(tk_root)
        assert hasattr(z, "_open_archive")
        assert hasattr(z, "_create_zip")
        assert hasattr(z, "_extract_all")
        assert hasattr(z, "_add_files")

    def test_open_archive_file_zip(self, tk_root, tmp_path):
        z = self._make_ezip(tk_root)
        archive = str(tmp_path / "test.zip")
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("a.txt", "AAA")
            zf.writestr("b.txt", "BBB")
        z._open_archive_file(archive)
        children = z.tree.get_children()
        assert len(children) == 2
        assert "ZIP" in z.info_label.cget("text")
