# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for SessionManager — JSON session persistence.
"""
import json
import os
import pytest

tk = pytest.importorskip("tkinter")

from gui.apps.session_manager import SessionManager


class TestSessionManager:
    def test_load_empty(self, tmp_sessions_file):
        """Loading when no file exists returns empty list."""
        mgr = SessionManager()
        assert mgr.load_sessions() == []

    def test_add_session(self, tmp_sessions_file):
        """Adding a session persists it to disk."""
        mgr = SessionManager()
        mgr.add_session("myserver", "ssh", "ssh user@host")
        sessions = mgr.load_sessions()
        assert len(sessions) == 1
        assert sessions[0]["name"] == "myserver"
        assert sessions[0]["type"] == "ssh"
        assert sessions[0]["connection"] == "ssh user@host"

    def test_add_multiple_sessions(self, tmp_sessions_file):
        """Multiple sessions accumulate correctly."""
        mgr = SessionManager()
        mgr.add_session("server1", "ssh", "ssh user@host1")
        mgr.add_session("serial1", "serial", "COM3:115200")
        mgr.add_session("local1", "local", "local")
        sessions = mgr.load_sessions()
        assert len(sessions) == 3
        assert sessions[0]["type"] == "ssh"
        assert sessions[1]["type"] == "serial"
        assert sessions[2]["type"] == "local"

    def test_remove_session(self, tmp_sessions_file):
        """Removing a session by name works."""
        mgr = SessionManager()
        mgr.add_session("keep", "ssh", "ssh keep@host")
        mgr.add_session("remove", "ssh", "ssh remove@host")
        mgr.remove_session("remove")
        sessions = mgr.load_sessions()
        assert len(sessions) == 1
        assert sessions[0]["name"] == "keep"

    def test_remove_nonexistent(self, tmp_sessions_file):
        """Removing a session that doesn't exist is a no-op."""
        mgr = SessionManager()
        mgr.add_session("exists", "ssh", "ssh exists@host")
        mgr.remove_session("doesnotexist")
        assert len(mgr.load_sessions()) == 1

    def test_search_by_name(self, tmp_sessions_file):
        """Searching matches by session name (case-insensitive)."""
        mgr = SessionManager()
        mgr.add_session("Production-Web", "ssh", "ssh prod@web")
        mgr.add_session("Staging-DB", "ssh", "ssh stage@db")
        mgr.add_session("Local-Dev", "local", "local")
        results = mgr.search("prod")
        assert len(results) == 1
        assert results[0]["name"] == "Production-Web"

    def test_search_by_connection(self, tmp_sessions_file):
        """Searching matches by connection string."""
        mgr = SessionManager()
        mgr.add_session("myhost", "ssh", "ssh admin@192.168.1.1")
        results = mgr.search("192.168")
        assert len(results) == 1

    def test_search_no_results(self, tmp_sessions_file):
        """Searching with no matches returns empty list."""
        mgr = SessionManager()
        mgr.add_session("server", "ssh", "ssh user@host")
        assert mgr.search("nonexistent") == []

    def test_search_case_insensitive(self, tmp_sessions_file):
        """Search is case-insensitive."""
        mgr = SessionManager()
        mgr.add_session("MyServer", "ssh", "ssh user@host")
        assert len(mgr.search("myserver")) == 1
        assert len(mgr.search("MYSERVER")) == 1

    def test_load_corrupted_file(self, tmp_sessions_file):
        """Loading a corrupted JSON file returns empty list."""
        with open(tmp_sessions_file, "w") as f:
            f.write("not valid json{{{")
        mgr = SessionManager()
        assert mgr.load_sessions() == []

    def test_load_wrong_type(self, tmp_sessions_file):
        """Loading a JSON file with wrong root type returns empty list."""
        with open(tmp_sessions_file, "w") as f:
            json.dump({"not": "a list"}, f)
        mgr = SessionManager()
        assert mgr.load_sessions() == []

    def test_session_file_created(self, tmp_sessions_file):
        """The sessions file is created on first save."""
        mgr = SessionManager()
        assert not os.path.exists(tmp_sessions_file)
        mgr.add_session("test", "ssh", "ssh test@host")
        assert os.path.exists(tmp_sessions_file)

    def test_session_json_format(self, tmp_sessions_file):
        """Saved JSON is properly formatted."""
        mgr = SessionManager()
        mgr.add_session("test", "ssh", "ssh test@host")
        with open(tmp_sessions_file, "r") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 1
        assert set(data[0].keys()) == {"name", "type", "connection"}
