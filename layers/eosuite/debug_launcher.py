# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Debug Launcher — Imports every module, validates all classes,
tests instantiation logic, and reports issues without requiring tkinter GUI.
"""
import sys
import os
import importlib
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESULTS = {"pass": 0, "fail": 0, "warn": 0}
ISSUES = []


def log_pass(msg):
    RESULTS["pass"] += 1
    print(f"  ✓ {msg}")


def log_fail(msg, err=""):
    RESULTS["fail"] += 1
    ISSUES.append((msg, err))
    print(f"  ✗ {msg}")
    if err:
        print(f"    → {err}")


def log_warn(msg):
    RESULTS["warn"] += 1
    print(f"  ⚠ {msg}")


# ---------------------------------------------------------------------------
# Phase 1: Module imports
# ---------------------------------------------------------------------------
print("=" * 70)
print("PHASE 1: Module Import Checks")
print("=" * 70)

# Mock tkinter if not available
try:
    import tkinter
    HAS_TK = True
    print("  tkinter: available")
except ImportError:
    HAS_TK = False
    print("  tkinter: NOT available — using mock stubs")
    from unittest.mock import MagicMock
    _tk = MagicMock()
    for mod in ("tkinter", "tkinter.ttk", "tkinter.filedialog",
                "tkinter.messagebox", "tkinter.scrolledtext",
                "tkinter.colorchooser", "tkinter.simpledialog",
                "_tkinter"):
        sys.modules.setdefault(mod, _tk)

ALL_MODULES = [
    "gui",
    "gui.styles",
    "gui.toolbar",
    "gui.sidebar",
    "gui.home_tab",
    "gui.terminal_tab",
    "gui.split_manager",
    "gui.main_window",
    "gui.apps",
    "gui.apps.ecal",
    "gui.apps.etimer",
    "gui.apps.eclock",
    "gui.apps.enote",
    "gui.apps.eviewer",
    "gui.apps.econverter",
    "gui.apps.eguard",
    "gui.apps.eweb",
    "gui.apps.ezip",
    "gui.apps.ecleaner",
    "gui.apps.evpn",
    "gui.apps.echat",
    "gui.apps.epaint",
    "gui.apps.eplay",
    "gui.apps.ebuffer",
    "gui.apps.epdf",
    "gui.apps.eftp",
    "gui.apps.etunnel",
    "gui.apps.evirustower",
    "gui.apps.evnc",
    "gui.apps.snake",
    "gui.apps.ssh_client",
    "gui.apps.serial_term",
    "gui.apps.session_manager",
]

for mod_name in ALL_MODULES:
    try:
        importlib.import_module(mod_name)
        log_pass(f"import {mod_name}")
    except Exception as e:
        log_fail(f"import {mod_name}", str(e))

# ---------------------------------------------------------------------------
# Phase 2: Class existence checks
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("PHASE 2: Class & Attribute Existence")
print("=" * 70)

CLASS_MAP = [
    ("gui.styles", "ThemeManager"),
    ("gui.styles", "DARK"),
    ("gui.styles", "LIGHT"),
    ("gui.apps.ecal", "ECal"),
    ("gui.apps.etimer", "ETimer"),
    ("gui.apps.eclock", "EClock"),
    ("gui.apps.enote", "ENote"),
    ("gui.apps.eviewer", "EViewer"),
    ("gui.apps.econverter", "EConverter"),
    ("gui.apps.eguard", "EGuard"),
    ("gui.apps.eweb", "EWeb"),
    ("gui.apps.eweb", "RichHTMLParser"),
    ("gui.apps.ezip", "EZip"),
    ("gui.apps.ecleaner", "ECleaner"),
    ("gui.apps.evpn", "EVpn"),
    ("gui.apps.echat", "EChat"),
    ("gui.apps.epaint", "EPaint"),
    ("gui.apps.eplay", "EPlay"),
    ("gui.apps.ebuffer", "EBuffer"),
    ("gui.apps.epdf", "EPdf"),
    ("gui.apps.eftp", "EFTP"),
    ("gui.apps.etunnel", "ETunnel"),
    ("gui.apps.evirustower", "EVirusTower"),
    ("gui.apps.evnc", "EVnc"),
    ("gui.apps.snake", "SnakeGame"),
    ("gui.apps.ssh_client", "SSHDialog"),
    ("gui.apps.serial_term", "SerialDialog"),
    ("gui.apps.session_manager", "SessionManager"),
    ("gui.apps.session_manager", "SessionManagerDialog"),
    ("gui.main_window", "MainWindow"),
]

for mod_name, cls_name in CLASS_MAP:
    try:
        mod = importlib.import_module(mod_name)
        if hasattr(mod, cls_name):
            log_pass(f"{mod_name}.{cls_name}")
        else:
            log_fail(f"{mod_name}.{cls_name}", "attribute not found")
    except Exception as e:
        log_fail(f"{mod_name}.{cls_name}", str(e))

# ---------------------------------------------------------------------------
# Phase 3: eClock timezone DB validation
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("PHASE 3: eClock Timezone Database Validation")
print("=" * 70)

try:
    from gui.apps.eclock import TIMEZONE_DB, DEFAULT_CITIES, EClock
    import datetime

    if len(TIMEZONE_DB) >= 30:
        log_pass(f"TIMEZONE_DB has {len(TIMEZONE_DB)} cities")
    else:
        log_fail(f"TIMEZONE_DB only has {len(TIMEZONE_DB)} cities (expected 30+)")

    if len(DEFAULT_CITIES) == 10:
        log_pass(f"DEFAULT_CITIES has {len(DEFAULT_CITIES)} entries")
    else:
        log_fail(f"DEFAULT_CITIES has {len(DEFAULT_CITIES)} entries (expected 10)")

    for city in DEFAULT_CITIES:
        if city in TIMEZONE_DB:
            log_pass(f"Default city '{city}' in TIMEZONE_DB")
        else:
            log_fail(f"Default city '{city}' NOT in TIMEZONE_DB")

    for city, (tz, offset) in TIMEZONE_DB.items():
        if not isinstance(tz, str) or len(tz) == 0:
            log_fail(f"City '{city}' has invalid tz label: {tz!r}")
        if not isinstance(offset, (int, float)):
            log_fail(f"City '{city}' has invalid offset type: {type(offset)}")
        if offset < -12 or offset > 14:
            log_warn(f"City '{city}' has unusual offset: {offset}")

    known = {"London": 0, "New York": -5, "Tokyo": 9, "Mumbai": 5.5, "Sydney": 10}
    for city, expected in known.items():
        actual = TIMEZONE_DB[city][1]
        if actual == expected:
            log_pass(f"{city} offset = {actual}")
        else:
            log_fail(f"{city} offset = {actual} (expected {expected})")

    t = EClock.get_city_time("London")
    if isinstance(t, datetime.datetime):
        log_pass(f"get_city_time('London') = {EClock.fmt_time(t)}")
    else:
        log_fail("get_city_time('London') returned None")

    if EClock.get_city_time("Atlantis") is None:
        log_pass("get_city_time('Atlantis') = None (correct)")
    else:
        log_fail("get_city_time('Atlantis') should return None")

    dt = datetime.datetime(2026, 3, 15, 14, 30, 45)
    fmt = EClock.fmt_time(dt)
    if fmt == "14:30:45":
        log_pass(f"fmt_time = {fmt}")
    else:
        log_fail(f"fmt_time = {fmt} (expected 14:30:45)")

    fmtd = EClock.fmt_date(dt)
    if "Mar" in fmtd and "15" in fmtd:
        log_pass(f"fmt_date = {fmtd}")
    else:
        log_fail(f"fmt_date = {fmtd} (expected 'Sun, Mar 15')")

except Exception as e:
    log_fail("eClock validation", traceback.format_exc())

# ---------------------------------------------------------------------------
# Phase 4: EConverter static methods
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("PHASE 4: EConverter PDF Generation")
print("=" * 70)

try:
    from gui.apps.econverter import EConverter
    import tempfile

    out = os.path.join(tempfile.gettempdir(), "eosuite_test.pdf")
    EConverter._text_to_pdf_file(None, "Hello EoSuite!", out)
    if os.path.exists(out) and os.path.getsize(out) > 0:
        with open(out, "rb") as f:
            header = f.read(8)
        if header.startswith(b"%PDF"):
            log_pass(f"PDF generated: {os.path.getsize(out)} bytes, valid header")
        else:
            log_fail("PDF header invalid")
        os.remove(out)
    else:
        log_fail("PDF file not created or empty")
except Exception as e:
    log_fail("EConverter PDF", str(e))

# ---------------------------------------------------------------------------
# Phase 5: SessionManager persistence
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("PHASE 5: SessionManager Persistence")
print("=" * 70)

try:
    import gui.apps.session_manager as sm
    import tempfile
    import json

    tmp_dir = tempfile.mkdtemp()
    orig_dir = sm.CONFIG_DIR
    orig_file = sm.SESSIONS_FILE
    sm.CONFIG_DIR = tmp_dir
    sm.SESSIONS_FILE = os.path.join(tmp_dir, "sessions.json")

    mgr = sm.SessionManager()

    sessions = mgr.load_sessions()
    if sessions == []:
        log_pass("load_sessions() returns [] when no file")
    else:
        log_fail(f"load_sessions() returned {sessions} (expected [])")

    mgr.add_session("test-server", "ssh", "ssh admin@host")
    loaded = mgr.load_sessions()
    if len(loaded) == 1 and loaded[0]["name"] == "test-server":
        log_pass("add_session + load_sessions works")
    else:
        log_fail(f"add_session failed: {loaded}")

    results = mgr.search("test")
    if len(results) == 1:
        log_pass("search('test') found 1 result")
    else:
        log_fail(f"search('test') found {len(results)} results")

    mgr.remove_session("test-server")
    if mgr.load_sessions() == []:
        log_pass("remove_session works")
    else:
        log_fail("remove_session did not remove")

    sm.CONFIG_DIR = orig_dir
    sm.SESSIONS_FILE = orig_file
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
except Exception as e:
    log_fail("SessionManager", traceback.format_exc())

# ---------------------------------------------------------------------------
# Phase 6: ECleaner format_size
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("PHASE 6: ECleaner Size Formatting")
print("=" * 70)

try:
    from gui.apps.ecleaner import ECleaner
    fmt = ECleaner._fmt_size if hasattr(ECleaner, "_fmt_size") else ECleaner._fmt

    tests = [
        (0, "B"), (512, "B"), (2048, "KB"),
        (5 * 1024 * 1024, "MB"), (3 * 1024**3, "GB"),
        (2 * 1024**4, "TB"),
    ]
    for size, expected_unit in tests:
        result = fmt(size)
        if expected_unit in result:
            log_pass(f"fmt({size}) = {result}")
        else:
            log_fail(f"fmt({size}) = {result} (expected {expected_unit})")
except Exception as e:
    log_fail("ECleaner formatting", str(e))

# ---------------------------------------------------------------------------
# Phase 7: eVirusTower malware DB
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("PHASE 7: eVirusTower Malware Database")
print("=" * 70)

try:
    from gui.apps.evirustower import (
        KNOWN_MALWARE_HASHES, SUSPICIOUS_EXTENSIONS, SUSPICIOUS_PATTERNS
    )

    if "44d88612fea8a8f36de82e1278abb02f" in KNOWN_MALWARE_HASHES:
        log_pass("EICAR hash present in DB")
    else:
        log_fail("EICAR hash missing from DB")

    for ext in [".exe", ".bat", ".vbs", ".ps1"]:
        if ext in SUSPICIOUS_EXTENSIONS:
            log_pass(f"Suspicious ext: {ext}")
        else:
            log_fail(f"Missing suspicious ext: {ext}")

    if len(SUSPICIOUS_PATTERNS) >= 3:
        log_pass(f"SUSPICIOUS_PATTERNS has {len(SUSPICIOUS_PATTERNS)} entries")
    else:
        log_fail(f"SUSPICIOUS_PATTERNS only has {len(SUSPICIOUS_PATTERNS)}")
except Exception as e:
    log_fail("eVirusTower DB", str(e))

# ---------------------------------------------------------------------------
# Phase 8: RichHTMLParser
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("PHASE 8: eWeb HTML Parser")
print("=" * 70)

try:
    from gui.apps.eweb import RichHTMLParser

    p = RichHTMLParser()
    p.feed("<html><head><title>Test</title></head>"
           "<body><h1>Hello</h1><p>World</p>"
           "<a href='https://x.com'>Link</a>"
           "<script>evil()</script>"
           "<b>Bold</b></body></html>")

    text = "".join(t for t, _ in p.segments)

    if p.title == "Test":
        log_pass(f"Title extracted: {p.title}")
    else:
        log_fail(f"Title = {p.title!r} (expected 'Test')")

    if "Hello" in text:
        log_pass("H1 content parsed")
    else:
        log_fail("H1 content missing")

    if "evil" not in text:
        log_pass("<script> content filtered")
    else:
        log_fail("<script> content leaked into output")

    if len(p.links) >= 1:
        log_pass(f"Links extracted: {len(p.links)}")
    else:
        log_fail("No links extracted")

    found_bold = any("bold" in tags for _, tags in p.segments)
    if found_bold:
        log_pass("Bold tag detected")
    else:
        log_fail("Bold tag not detected")
except Exception as e:
    log_fail("RichHTMLParser", str(e))

# ---------------------------------------------------------------------------
# Phase 9: EFTP format_size
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("PHASE 9: eFTP Size Formatting")
print("=" * 70)

try:
    from gui.apps.eftp import EFTP
    ftp = EFTP.__new__(EFTP)
    tests = [(0, "0 B"), (1024, "KB"), (1048576, "MB"), (1073741824, "GB")]
    for size, expected in tests:
        result = ftp._format_size(size)
        if expected in result:
            log_pass(f"_format_size({size}) = {result}")
        else:
            log_fail(f"_format_size({size}) = {result} (expected '{expected}')")
except Exception as e:
    log_fail("EFTP format_size", str(e))

# ---------------------------------------------------------------------------
# Phase 10: MainWindow integration check
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("PHASE 10: MainWindow Tool Integration")
print("=" * 70)

try:
    from gui.main_window import MainWindow

    expected_methods = [
        "open_ecal", "open_etimer", "open_eclock", "open_enote",
        "open_eviewer", "open_eguard", "open_eweb", "open_ezip",
        "open_ecleaner", "open_evpn", "open_echat", "open_epaint",
        "open_eplay", "open_ebuffer", "open_econverter", "open_epdf",
        "open_eftp", "open_etunnel", "open_evirustower", "open_evnc",
        "open_snake",
    ]

    for method in expected_methods:
        if hasattr(MainWindow, method):
            log_pass(f"MainWindow.{method}")
        else:
            log_fail(f"MainWindow.{method} MISSING")
except Exception as e:
    log_fail("MainWindow integration", str(e))

# ---------------------------------------------------------------------------
# Phase 11: ETimer formatting
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("PHASE 11: eTimer Formatting")
print("=" * 70)

try:
    from gui.apps.etimer import ETimer

    tests = [
        (0, "00:00:00.000"),
        (1.0, "00:00:01.000"),
        (60.0, "00:01:00.000"),
        (3600.0, "01:00:00.000"),
        (3661.123, "01:01:01.123"),
    ]
    for secs, expected in tests:
        result = ETimer._fmt(secs)
        if result == expected:
            log_pass(f"_fmt({secs}) = {result}")
        else:
            log_fail(f"_fmt({secs}) = {result} (expected {expected})")
except Exception as e:
    log_fail("ETimer formatting", str(e))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"  Passed:   {RESULTS['pass']}")
print(f"  Failed:   {RESULTS['fail']}")
print(f"  Warnings: {RESULTS['warn']}")
print(f"  Total:    {RESULTS['pass'] + RESULTS['fail'] + RESULTS['warn']}")

if ISSUES:
    print(f"\n{'=' * 70}")
    print("ISSUES FOUND")
    print("=" * 70)
    for msg, err in ISSUES:
        print(f"  ✗ {msg}")
        if err:
            print(f"    → {err}")
else:
    print(f"\n  ★ All checks passed — no issues found!")

sys.exit(1 if RESULTS["fail"] > 0 else 0)
