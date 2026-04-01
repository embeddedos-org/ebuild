# ⚡ EoSuite

**Super Lightweight Terminal Suite** — MobaXterm-style GUI with 29+ built-in tools.

Cross-platform: **Windows** • **macOS** • **Linux**

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![CI](https://github.com/embeddedos-org/EoSuite/actions/workflows/ci.yml/badge.svg)
![Release](https://img.shields.io/github/v/release/embeddedos-org/EoSuite?label=Release)
![Downloads](https://img.shields.io/github/downloads/embeddedos-org/EoSuite/total?label=Downloads)

---

## 📥 Download

| Platform | Download | Install |
|----------|----------|---------|
| 🪟 **Windows x64** | [EoSuite-windows-x64.exe](https://github.com/embeddedos-org/EoSuite/releases/latest/download/EoSuite-windows-x64.exe) | Run directly — portable, no install needed |
| 🍎 **macOS ARM64** (M1/M2/M3) | [EoSuite-macos-arm64.dmg](https://github.com/embeddedos-org/EoSuite/releases/latest/download/EoSuite-macos-arm64.dmg) | Open DMG → drag to Applications |
| 🐧 **Linux x64** (.deb) | [EoSuite-linux-x64.deb](https://github.com/embeddedos-org/EoSuite/releases/latest/download/EoSuite-linux-x64.deb) | `sudo dpkg -i EoSuite-linux-x64.deb` |
| 🐧 **Linux x64** (binary) | [EoSuite-linux-x64](https://github.com/embeddedos-org/EoSuite/releases/latest/download/EoSuite-linux-x64) | `chmod +x EoSuite-linux-x64 && ./EoSuite-linux-x64` |

> **All releases:** [github.com/embeddedos-org/EoSuite/releases](https://github.com/embeddedos-org/EoSuite/releases)
> **Checksums:** Each release includes `SHA256SUMS.txt` for verification.

### Run from Source (no download needed)

```bash
git clone https://github.com/embeddedos-org/EoSuite.git
cd EoSuite
python EoSuite_GUI.py
```

---

## 📸 Features

### MobaXterm-Style Layout
- **Menu bar** — Terminal | Sessions | View | Tools | Games | Settings | Help
- **Icon toolbar** — Session, Servers, Tools, Games, View, Split, Settings, Help, Theme, Exit
- **Left sidebar** — Collapsible session tree with saved SSH/Serial connections
- **Tabbed workspace** — Multiple tools open simultaneously
- **Split view** — 2-pane or 4-pane with draggable dividers and pane assignment dialog
- **Pop-out windows** — Detach any tab to its own window (re-attach, fullscreen, stay on top)
- **Dark/Light theme** — Toggle with one click

### 🔐 Connectivity

| Tool | Description |
|------|-------------|
| **SSH Client** | `user@host:port`, identity file, session saving |
| **Serial Terminal** | Auto-detect COM ports, baud rate 9600–921600 |
| **eFTP** | FileZilla-style dual-pane SFTP/FTP/SCP client |
| **eTunnel** | SSH tunneling — Local/Remote/Dynamic SOCKS proxy |
| **Session Manager** | Save/load/search sessions from JSON config |

### 🧰 Built-in Tools (22+ Apps)

| Tool | Description |
|------|-------------|
| 🧮 **eCal** | Calculator with expression evaluation |
| ⏱ **eTimer** | Stopwatch + countdown with lap times |
| 📝 **eNote** | Text editor with find/replace/word count |
| 🔢 **eViewer** | Hex inspector — color-coded bytes, any file type |
| 🔄 **eConverter** | Word/Image/Text → PDF, CSV↔JSON, Base64, Hex |
| 🛡 **eGuard** | Keep-awake — prevents sleep on all platforms |
| 🌐 **eWeb** | Browser with rich HTML, clickable links, popups |
| 📦 **eZip** | Archive manager — 7-Zip/tar/zip |
| 🧹 **eCleaner** | Disk cleanup — temp files, cache, logs |
| 🔒 **eVPN** | OpenVPN, WireGuard, SSH SOCKS tunnel |
| 💬 **eChat** | Peer-to-peer TCP chat over IP |
| 🎨 **ePaint** | Canvas drawing with brush/shapes/colors |
| ▶ **ePlay** | Media player via ffplay/mpv/vlc |
| 📋 **eBuffer** | Clipboard manager — 10 slots |
| 📄 **ePDF** | PDF reader with sign, merge, split, convert |
| 🛡 **eVirusTower** | Malware scanner — local + remote (SSH client mode) |
| 🐍 **Snake** | Classic snake game with score and speed control |
| 🕐 **eClock** | Multi-city world clock with live time display |

---

## 🧪 Testing

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

### Test Coverage Summary

**27 test files · 400+ test cases** covering every GUI module, pure-logic helper, and core subsystem.

#### Connectivity & Sessions

| Test File | Module | Tests | Coverage |
|-----------|--------|:-----:|----------|
| `test_ssh_client.py` | SSH Client | 17 | Quick-connect parsing (`user@host:port`), command building, key file, session naming |
| `test_serial_term.py` | Serial Terminal | 4 | Port detection, baud rate list, platform-specific COM format |
| `test_etunnel.py` | eTunnel | 22 | Local/Remote/Dynamic forward command preview, custom port, state management, `on_close` |
| `test_eftp.py` | eFTP | 17 | `_format_size` (B/KB/MB/GB), initial state, disconnect, log, protocol defaults |
| `test_session_manager.py` | Session Manager | 12 | Add/remove/search sessions, JSON persistence, corrupted file handling |

#### Built-in Tools

| Test File | Module | Tests | Coverage |
|-----------|--------|:-----:|----------|
| `test_ecal.py` | eCal | 13 | Basic/scientific arithmetic, `_safe_eval`, division by zero, clear, modulo, tax attributes |
| `test_etimer.py` | eTimer | 7 | `_fmt` time formatting — zero, seconds, minutes, hours, milliseconds |
| `test_enote.py` | eNote | 8 | New/save file ops, status bar (Ln/Col/chars), undo, toolbar methods |
| `test_eviewer.py` | eViewer | 12 | Hex rendering, ASCII display, non-printable dots, offset goto, byte classification |
| `test_econverter.py` | eConverter | 18 | Text transforms (upper/lower/sort/unique/reverse), Base64 roundtrip, CSV↔JSON, PDF generation (header/EOF/multipage/special chars) |
| `test_eguard.py` | eGuard | 8 | Toggle activate/deactivate, status labels, button text, `on_close` cleanup |
| `test_eweb.py` | eWeb | 30 | `RichHTMLParser` (20 tests: headings, bold, italic, underline, links, entities, `<script>`/`<style>` skip, `<pre>`, lists, images, blockquote), URL resolution, browser state |
| `test_ezip.py` | eZip | 10 | Zip create/read/extract/append, `is_zipfile` validation, GUI tree population |
| `test_ecleaner.py` | eCleaner | 15 | `_fmt_size` (B→TB), category definitions, `_scan_dir` (empty/files/nonexistent), log scanning, GUI state |
| `test_evpn.py` | eVPN | 14 | Free proxy API definitions, VPN connect/disconnect, SSH SOCKS vars, country/protocol defaults |
| `test_echat.py` | eChat | 13 | Message display, `/help /time /name /clear` commands, username, welcome messages, readonly state |
| `test_epaint.py` | ePaint | 11 | Tool/color/brush state, press/release coordinates, canvas clear, cursor, all 5 tools |
| `test_eplay.py` | ePlay | 10 | Play/stop state, volume default, playlist, prev/next, rewind/forward status messages |
| `test_ebuffer.py` | eBuffer | 11 | Slot CRUD, capture dedup, clipboard copy, max slots enforcement, preview |
| `test_epdf.py` | ePDF | 10 | Page navigation (next/prev/boundary), page label, readonly text view, method existence |
| `test_eclock.py` | eClock | 17 | Timezone DB validation, UTC offsets, city time lookup, time/date formatting, add/remove cities, duplicate prevention, GUI state |

#### Security & Games

| Test File | Module | Tests | Coverage |
|-----------|--------|:-----:|----------|
| `test_evirustower.py` | eVirusTower | 21 | Malware hash DB, EICAR detection, suspicious extensions, pattern matching (bat/vbs/ps1), scan/clean state, report export |
| `test_snake.py` | Snake Game | 19 | Initial state (length/direction/score), food placement, reset, direction reversal prevention, WASD controls, grid dimensions |

#### Infrastructure

| Test File | Module | Tests | Coverage |
|-----------|--------|:-----:|----------|
| `test_styles.py` | Theme Manager | 10 | DARK/LIGHT key completeness, hex color validation, theme toggle, `apply()`, colors isolation |
| `test_imports.py` | All Modules | 60+ | Import smoke tests for every module, class existence checks, version, `SplitManager` methods |
| `test_evnc.py` | eVNC | 15 | Viewer constant definitions, default port/display/quality, connection save/remove, `_find_viewer` |

### Running Tests

```bash
# All tests (requires Python 3.10+ with tkinter)
python -m pytest tests/ -v

# Headless tests only (no display needed)
python -m pytest tests/ -v -m "not gui"

# Single module
python -m pytest tests/test_eweb.py -v
```

---

## 🔧 CI/CD

| Pipeline | Trigger | Jobs |
|----------|---------|------|
| **EoSuite CI** | Push to `master`/`main`, Pull Requests | Lint (flake8) → Tests (3 OS × 2 Python) |
| **EoSuite Release** | Tag `v*` push | Build Win/Mac/Linux + Publish GitHub Release |

The CI pipeline runs on every pull request:

1. **Lint** — `flake8` checks all `gui/` source files
2. **Test** — Full pytest suite across a 3×2 matrix:
   - **OS:** Ubuntu, Windows, macOS
   - **Python:** 3.11, 3.12
   - Linux uses `xvfb-run` for headless GUI testing

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New terminal |
| `Ctrl+Shift+S` | New SSH session |
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+W` | Close tab |
| `F11` | Fullscreen |

---

## 📜 License

MIT License — see LICENSE file.

---

**Built with ❤️ by the EoS team** · [github.com/embeddedos-org/EoSuite](https://github.com/embeddedos-org/EoSuite)
