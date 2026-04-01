# CHANGELOG

## v1.1.0 — 2026-03-28

### 🐛 Bug Fixes

- **Fixed duplicate file contents** — `gui/styles.py`, `gui/terminal_tab.py`, and `gui/__init__.py` had their entire content duplicated, causing class redefinition errors and import conflicts
- **Fixed `winsock2.h` include order** — `platform.h` now includes `<winsock2.h>` before `<windows.h>`, eliminating the build warning in `echat.c` that caused unreliable socket operations on Windows
- **Fixed case-sensitive `#include` paths** — All 19 C source files referenced `"EOSUITE.h"` (uppercase) but the actual file is `eosuite.h`, which broke builds on Linux and macOS (case-sensitive filesystems)
- **Fixed `creationflags` bug in `terminal_tab.py`** — `subprocess.CREATE_NO_WINDOW` is now only passed on Windows, preventing crashes on Linux/macOS
- **Fixed hardcoded Python paths** — `EoSuite_GUI.bat`, `build.bat`, and `build_installer.bat` referenced hardcoded `C:\Python312\pythonw.exe` and `C:\tools\fb-python\...` paths; now auto-detect Python via `PATH`
- **Fixed `pyproject.toml` entry point** — Changed from `eosuite = "EoSuite_GUI:main"` (broken script reference) to `eosuite = "gui.main_window:MainWindow.launch"` (proper package entry)
- **Fixed missing `eosuite.h` version** — Updated `EOSUITE_VERSION` from `"1.0.0"` to match `pyproject.toml`

### ✨ New Features & Improvements

- **Added 7 missing hidden imports** — `EoSuite.spec`, `build_linux.sh`, and `build_macos.sh` now include: `gui.apps.tetris`, `gui.apps.minesweeper`, `gui.apps.dice`, `gui.apps.chess`, `gui.apps.eclock`, `gui.apps.evnc`
- **Improved `CMakeLists.txt` cross-platform support**:
  - Added `pthread` linking for Linux
  - Added `CoreFoundation` and `IOKit` framework linking for macOS
  - Added `-s` strip flag for release builds on Unix
  - Added `_CRT_SECURE_NO_WARNINGS` for MSVC builds
- **Added `MainWindow.launch()` classmethod** for proper `setuptools` GUI script entry point
- **Added GitHub Actions CI/CD**:
  - `ci.yml` — Lint (flake8) + test matrix (3 OS × 2 Python versions)
  - `release.yml` — Automated builds for Windows x64, macOS ARM64, Linux x64 with SHA256 checksums and GitHub Release publication
- **Added `LICENSE` file** (MIT)
- **Comprehensive README rewrite** with full API documentation for all 29 tools/apps

### 📦 Build System

- All build scripts now auto-detect compiler/Python locations
- `EoSuite.spec` includes all 29 app modules + 5 games + third-party libraries
- Excluded unnecessary heavy packages (numpy, scipy, tensorflow, etc.) from builds
- Proper UPX compression enabled for smaller binaries

### 📚 Documentation

- Complete API reference for every tool module (ECal, ETimer, ENote, EViewer, EConverter, EGuard, EWeb, EZip, ECleaner, EVpn, EChat, EPaint, EPlay, EBuffer, EPdf, EFTP, ETunnel, EVirusTower, EVnc, EClock, SnakeGame, Tetris, Minesweeper, Chess, DiceRoller, SSHDialog, SerialDialog, SessionManager)
- Architecture overview with module structure
- Build instructions for all 3 platforms
- Test coverage summary (27 test files, 400+ tests)
- Keyboard shortcuts reference

---

## v1.0.0 — 2026-02-01

- Initial release
- 22+ built-in tools
- MobaXterm-style GUI with dark/light themes
- Cross-platform support (Windows, macOS, Linux)
- SSH Client, Serial Terminal, Session Manager
- Split view (2-pane, 4-pane) with draggable dividers
- Pop-out windows with re-attach, fullscreen, stay-on-top
