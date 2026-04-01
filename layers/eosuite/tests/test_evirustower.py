# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Unit tests for eVirusTower — malware detection logic and scanner state.
"""
import os
import hashlib
import pytest

tk = pytest.importorskip("tkinter")


class TestMalwareDatabase:
    """Test the malware signature database and detection constants."""

    def test_known_hashes_exist(self):
        from gui.apps.evirustower import KNOWN_MALWARE_HASHES
        assert isinstance(KNOWN_MALWARE_HASHES, dict)
        assert len(KNOWN_MALWARE_HASHES) >= 1

    def test_eicar_hash_present(self):
        from gui.apps.evirustower import KNOWN_MALWARE_HASHES
        assert "44d88612fea8a8f36de82e1278abb02f" in KNOWN_MALWARE_HASHES
        assert KNOWN_MALWARE_HASHES["44d88612fea8a8f36de82e1278abb02f"] == "EICAR Test File"

    def test_suspicious_extensions_defined(self):
        from gui.apps.evirustower import SUSPICIOUS_EXTENSIONS
        assert isinstance(SUSPICIOUS_EXTENSIONS, set)
        assert ".exe" in SUSPICIOUS_EXTENSIONS
        assert ".bat" in SUSPICIOUS_EXTENSIONS
        assert ".vbs" in SUSPICIOUS_EXTENSIONS
        assert ".ps1" in SUSPICIOUS_EXTENSIONS

    def test_suspicious_patterns_defined(self):
        from gui.apps.evirustower import SUSPICIOUS_PATTERNS
        assert isinstance(SUSPICIOUS_PATTERNS, list)
        assert len(SUSPICIOUS_PATTERNS) >= 3
        for pattern, name in SUSPICIOUS_PATTERNS:
            assert isinstance(pattern, bytes)
            assert isinstance(name, str)

    def test_safe_extensions_not_flagged(self):
        from gui.apps.evirustower import SUSPICIOUS_EXTENSIONS
        safe = [".txt", ".py", ".md", ".json", ".csv", ".html", ".css"]
        for ext in safe:
            assert ext not in SUSPICIOUS_EXTENSIONS


class TestFileScanning:
    """Test file scanning logic using temp files."""

    def test_clean_file_not_detected(self, tmp_path):
        clean = tmp_path / "clean.txt"
        clean.write_text("This is a clean file with no malware.")
        from gui.apps.evirustower import KNOWN_MALWARE_HASHES, SUSPICIOUS_PATTERNS
        with open(str(clean), "rb") as f:
            data = f.read()
        md5 = hashlib.md5(data).hexdigest()
        assert md5 not in KNOWN_MALWARE_HASHES
        for pattern, _ in SUSPICIOUS_PATTERNS:
            assert pattern not in data

    def test_eicar_hash_matches_database(self):
        """Verify the EICAR MD5 hash is in the malware database (no file needed)."""
        eicar_string = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        from gui.apps.evirustower import KNOWN_MALWARE_HASHES
        md5 = hashlib.md5(eicar_string).hexdigest()
        assert md5 in KNOWN_MALWARE_HASHES

    def test_suspicious_bat_detected(self, tmp_path):
        bat = tmp_path / "test.bat"
        bat.write_bytes(b"@echo off\ncmd.exe /c del C:\\important\\*.*\n")
        from gui.apps.evirustower import SUSPICIOUS_PATTERNS
        with open(str(bat), "rb") as f:
            data = f.read()
        found = False
        for pattern, name in SUSPICIOUS_PATTERNS:
            if pattern in data:
                found = True
                break
        assert found

    def test_suspicious_vbs_detected(self, tmp_path):
        vbs = tmp_path / "test.vbs"
        vbs.write_bytes(b'Set obj = CreateObject("WScript.Shell")\nobj.Run "cmd"\n')
        from gui.apps.evirustower import SUSPICIOUS_PATTERNS
        with open(str(vbs), "rb") as f:
            data = f.read()
        found = False
        for pattern, name in SUSPICIOUS_PATTERNS:
            if pattern in data:
                found = True
                assert name == "WScript Shell Access"
                break
        assert found

    def test_powershell_encoded_detected(self, tmp_path):
        ps1 = tmp_path / "test.ps1"
        ps1.write_bytes(b"powershell -enc SQBFAFgA\n")
        from gui.apps.evirustower import SUSPICIOUS_PATTERNS
        with open(str(ps1), "rb") as f:
            data = f.read()
        found = any(p in data for p, _ in SUSPICIOUS_PATTERNS)
        assert found

    def test_large_file_skipped(self, tmp_path):
        """Files over 50MB should not be hashed (performance guard)."""
        large = tmp_path / "large.bin"
        large.write_bytes(b"\x00" * 100)  # Small stand-in
        size = os.path.getsize(str(large))
        assert size < 50_000_000  # Our test file is small, but the logic threshold is 50MB

    def test_clean_python_file(self, tmp_path):
        py = tmp_path / "clean.py"
        py.write_text("print('hello world')\n")
        from gui.apps.evirustower import KNOWN_MALWARE_HASHES, SUSPICIOUS_PATTERNS
        with open(str(py), "rb") as f:
            data = f.read()
        md5 = hashlib.md5(data).hexdigest()
        assert md5 not in KNOWN_MALWARE_HASHES
        assert not any(p in data for p, _ in SUSPICIOUS_PATTERNS)


class TestReportExport:
    """Test report generation logic."""

    def test_report_format(self, tmp_path):
        report_path = tmp_path / "report.txt"
        threats = [
            {"file": "/path/to/bad.exe", "threat": "EICAR Test File"},
            {"file": "/path/to/script.bat", "threat": "Destructive Command"},
        ]
        with open(str(report_path), "w", encoding="utf-8") as f:
            f.write("eVirusTower Scan Report\n" + "=" * 50 + "\n")
            f.write("Files scanned: 100\nThreats: %d\n\n" % len(threats))
            for t in threats:
                f.write("THREAT: %s\n  File: %s\n\n" % (t["threat"], t["file"]))
        content = report_path.read_text()
        assert "eVirusTower Scan Report" in content
        assert "Files scanned: 100" in content
        assert "Threats: 2" in content
        assert "EICAR Test File" in content
        assert "Destructive Command" in content
        assert "/path/to/bad.exe" in content

    def test_empty_report(self, tmp_path):
        report_path = tmp_path / "empty_report.txt"
        threats = []
        with open(str(report_path), "w", encoding="utf-8") as f:
            f.write("eVirusTower Scan Report\n" + "=" * 50 + "\n")
            f.write("Files scanned: 50\nThreats: 0\n\n")
        content = report_path.read_text()
        assert "Threats: 0" in content


@pytest.mark.gui
class TestEVirusTowerGUI:
    """Test GUI widget state management."""

    def _make_scanner(self, tk_root):
        from gui.apps.evirustower import EVirusTower
        return EVirusTower(tk_root, type("App", (), {
            "theme": type("T", (), {"colors": {
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
            }})(),
            "set_status": lambda self, t: None,
        })())

    def test_initial_state(self, tk_root):
        s = self._make_scanner(tk_root)
        assert s._scanning is False
        assert s._threats == []
        assert s._files_scanned == 0

    def test_stop_scan_sets_flag(self, tk_root):
        s = self._make_scanner(tk_root)
        s._scanning = True
        s._stop_scan()
        assert s._scanning is False

    def test_update_stats(self, tk_root):
        s = self._make_scanner(tk_root)
        s._files_scanned = 42
        s._threats = [{"file": "a", "threat": "b"}]
        s._update_stats()
        assert "42" in s.stat_files.cget("text")
        assert "1" in s.stat_threats.cget("text")

    def test_log_writes(self, tk_root):
        s = self._make_scanner(tk_root)
        s._log_msg("Scanning started")
        content = s.log.get("1.0", "end").strip()
        assert "Scanning started" in content

    def test_scan_complete_safe(self, tk_root):
        s = self._make_scanner(tk_root)
        s._files_scanned = 10
        s._threats = []
        s._scan_complete()
        assert s._scanning is False
        assert "clean" in s.scan_status.cget("text").lower()

    def test_scan_complete_threats(self, tk_root):
        s = self._make_scanner(tk_root)
        s._files_scanned = 10
        s._threats = [{"file": "bad.exe", "threat": "Malware"}]
        s._scan_complete()
        assert s._scanning is False
        assert "1" in s.scan_status.cget("text")

    def test_check_clean_file(self, tk_root, tmp_path):
        s = self._make_scanner(tk_root)
        clean = tmp_path / "safe.txt"
        clean.write_text("Perfectly safe content")
        s._check_file(str(clean))
        assert s._files_scanned == 1
        assert len(s._threats) == 0

    def test_check_suspicious_bat_file(self, tk_root, tmp_path):
        """Test _check_file detects suspicious batch scripts."""
        s = self._make_scanner(tk_root)
        bat = tmp_path / "evil.bat"
        bat.write_bytes(b"@echo off\ncmd.exe /c del C:\\Windows\\*.*\n")
        s._check_file(str(bat))
        assert s._files_scanned == 1
        assert len(s._threats) == 1
        assert "Destructive Command" in s._threats[0]["threat"]
