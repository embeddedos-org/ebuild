# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

import sys, os, importlib
sys.path.insert(0, r"C:\Users\spatchava\Documents\EoS\EoSuite")
os.chdir(r"C:\Users\spatchava\Documents\EoS\EoSuite")

print("=== EoSuite Rename Verification ===\n")

# Check old files deleted
print("Old files removed:")
for f in ["gui/apps/calculator.py", "gui/apps/timer_app.py", "gui/apps/notepad.py", "gui/apps/hex_viewer.py"]:
    status = "GONE" if not os.path.exists(f) else "STILL EXISTS"
    print(f"  {f} -> {status}")

print("\nNew file imports:")
tests = [
    ("gui.apps.ecal", "ECal"),
    ("gui.apps.etimer", "ETimer"),
    ("gui.apps.enote", "ENote"),
    ("gui.apps.eviewer", "EViewer"),
    ("gui.apps.econverter", "EConverter"),
    ("gui.apps.echat", "EChat"),
    ("gui.apps.ebuffer", "EBuffer"),
    ("gui.apps.ecleaner", "ECleaner"),
    ("gui.apps.eguard", "EGuard"),
    ("gui.apps.epaint", "EPaint"),
    ("gui.apps.eplay", "EPlay"),
    ("gui.apps.epdf", "EPdf"),
    ("gui.apps.evpn", "EVpn"),
    ("gui.apps.eweb", "EWeb"),
    ("gui.apps.ezip", "EZip"),
    ("gui.apps.snake", "SnakeGame"),
    ("gui.apps.ssh_client", "SSHDialog"),
    ("gui.apps.serial_term", "SerialDialog"),
    ("gui.apps.session_manager", "SessionManager"),
    ("gui.styles", "ThemeManager"),
    ("gui.toolbar", "Toolbar"),
    ("gui.sidebar", "Sidebar"),
    ("gui.home_tab", "HomeTab"),
    ("gui.terminal_tab", "TerminalTab"),
    ("gui.main_window", "MainWindow"),
]

ok = 0
for mod_path, cls_name in tests:
    try:
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, cls_name)
        print(f"  {mod_path:30s} {cls_name:20s} OK")
        ok += 1
    except Exception as e:
        print(f"  {mod_path:30s} {cls_name:20s} FAIL: {e}")

print(f"\n{ok}/{len(tests)} imports passed")
print("\n=== ALL PASSED ===" if ok == len(tests) else "\n=== FAILURES DETECTED ===")
