# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
Generate EoSuite Help Guide PDF using the built-in PDF writer.
Run: python generate_help_pdf.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HELP_TEXT = """
================================================================================
                        EoSuite v1.1.0 — Help Guide
               Super Lightweight Terminal Suite with 23+ Tools
================================================================================

TABLE OF CONTENTS
-----------------
  1. Getting Started
  2. Main Window Layout
  3. Keyboard Shortcuts
  4. Terminal & Sessions
  5. Tool Reference (23 Apps)
  6. Theme & View Options
  7. CI / Testing
  8. Troubleshooting
  9. License & Credits

================================================================================
1. GETTING STARTED
================================================================================

  System Requirements:
    - Python 3.10 or higher (with tkinter)
    - Windows 10/11, macOS 12+, or Linux (Ubuntu 20.04+)

  Run from Source:
    $ git clone https://github.com/embeddedos-org/EoSuite.git
    $ cd EoSuite
    $ python EoSuite_GUI.py

  Download Binary:
    Visit https://github.com/embeddedos-org/EoSuite/releases
    - Windows: EoSuite-windows-x64.exe (portable, no install)
    - macOS:   EoSuite-macos-arm64.dmg
    - Linux:   EoSuite-linux-x64.deb or EoSuite-linux-x64

================================================================================
2. MAIN WINDOW LAYOUT
================================================================================

  EoSuite uses a MobaXterm-style layout with these components:

  +---------------------------------------------------------------+
  | Menu Bar: Terminal | Sessions | View | Tools | Games | Help   |
  +---------------------------------------------------------------+
  | Toolbar: Session | Servers | Tools | Games | View | Theme     |
  +---------------------------------------------------------------+
  | Sidebar   |  Tabbed Workspace                                 |
  | (Sessions)|  [Home] [Terminal] [eCal] [eWeb] ...              |
  |           |                                                    |
  | SSH       |  Active tool or terminal content                   |
  | Serial    |                                                    |
  | Local     |                                                    |
  +-----------+----------------------------------------------------+
  | Status Bar: Ready                            Dark Theme        |
  +---------------------------------------------------------------+

  Sidebar:
    - Collapsible panel on the left
    - Shows saved SSH, Serial, and Local sessions
    - Double-click a session to reconnect
    - Toggle with Ctrl+B

  Tabs:
    - Right-click any tab for: Pop-out, Duplicate, Close
    - Drag tabs to reorder (future feature)

  Split View:
    - View menu > Single / Horizontal / Vertical / Quad
    - Assign any tool to any pane

  Pop-out Windows:
    - Right-click tab > Pop-out to Window
    - Each pop-out has: re-attach, fullscreen, stay-on-top

================================================================================
3. KEYBOARD SHORTCUTS
================================================================================

  Ctrl+N / Ctrl+T     New local terminal
  Ctrl+Shift+S        New SSH session dialog
  Ctrl+B              Toggle sidebar
  Ctrl+W              Close current tab
  F11                 Toggle fullscreen
  Alt+F4              Exit application

================================================================================
4. TERMINAL & SESSIONS
================================================================================

  LOCAL TERMINAL
    Menu: Terminal > New Local Terminal (or Ctrl+N)
    Opens a system shell (cmd/PowerShell on Windows, bash on Linux/macOS)

  SSH CLIENT
    Menu: Terminal > New SSH Session (or Ctrl+Shift+S)
    Quick-connect format: user@hostname:port
    Supports: identity file (-i), custom port (-p)
    Sessions are saved automatically to ~/.eosuite/sessions.json

  SERIAL TERMINAL
    Menu: Terminal > New Serial Connection
    Auto-detects COM ports (Windows) or /dev/ttyUSB* (Linux)
    Baud rates: 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600

  SESSION MANAGER
    Menu: Sessions > Manage Sessions
    - View all saved sessions (SSH, Serial, Local)
    - Search by name or connection string
    - Remove old sessions
    - Sessions persist in JSON format

================================================================================
5. TOOL REFERENCE
================================================================================

  Access all tools from: Menu > Tools

  --------------------------------------------------------------------------
  eCal — Calculator                                           Menu: Tools
  --------------------------------------------------------------------------
    Modes: Basic, Scientific, Tax
    Basic: Type expressions like 2+3*4, press = or Enter
    Scientific: sin, cos, tan, log, sqrt, pi, e, factorial
    Tax: Enter income, select tax brackets, calculate liability
    Safe eval: Only allows math operations (no code injection)

  --------------------------------------------------------------------------
  eTimer — Stopwatch & Countdown                              Menu: Tools
  --------------------------------------------------------------------------
    Stopwatch: Start/Stop/Reset with lap times
    Countdown: Set hours:minutes:seconds, counts down to zero
    Display: Large digital format HH:MM:SS.mmm

  --------------------------------------------------------------------------
  eClock — World Clock                                        Menu: Tools
  --------------------------------------------------------------------------
    Shows live time for multiple cities worldwide
    37 pre-configured timezones (UTC-10 to UTC+12)
    Default cities: New York, London, Tokyo, Sydney, Mumbai,
                    Berlin, Sao Paulo, Los Angeles, Dubai, Singapore
    Add/Remove: Select from dropdown, click Add/Remove
    Analog clock: Shows hour/minute/second hands for selected city
    Click a city row to switch the analog display

  --------------------------------------------------------------------------
  eNote — Text Editor                                         Menu: Tools
  --------------------------------------------------------------------------
    Features: New, Open, Save, Save As, Find, Replace, Word Count
    Supports: .txt files, undo/redo, line/column display
    Find: Case-insensitive search with highlight
    Replace: Find and replace all occurrences
    Status bar: Shows Ln, Col, character count

  --------------------------------------------------------------------------
  eViewer — Hex Inspector                                     Menu: Tools
  --------------------------------------------------------------------------
    Opens any file in hex view with color-coded bytes:
      Blue   = offset column
      Green  = printable ASCII (0x20-0x7E)
      Orange = high bytes (> 0x7F)
      Red    = control characters (0x01-0x1F)
      Gray   = null bytes (0x00)
    Go to offset: Enter hex address to jump

  --------------------------------------------------------------------------
  eConverter — Format Converter                               Menu: Tools
  --------------------------------------------------------------------------
    Text:  Upper, Lower, Sort lines, Unique, Reverse
    Encoding: Base64 encode/decode, Hex encode/decode
    Data: CSV to JSON, JSON to CSV, JSON format/minify
    Docs: Text to PDF, Markdown to HTML
    Files: DOCX to Text, Image resize (requires Pillow)
    16+ conversion types with file input/output

  --------------------------------------------------------------------------
  eGuard — Keep Awake                                         Menu: Tools
  --------------------------------------------------------------------------
    Prevents screen sleep / screensaver activation
    Windows: Uses SetThreadExecutionState API
    macOS/Linux: Background thread activity
    Toggle: Click Activate/Deactivate button
    Status indicator: Green circle = active

  --------------------------------------------------------------------------
  eWeb — Web Browser                                          Menu: Tools
  --------------------------------------------------------------------------
    Rich HTML rendering with styled text (headings, bold, italic, links)
    Navigation: Back, Forward, Refresh, Home (google.com)
    Clickable links: Click to navigate, right-click for options
    Pop-out: Open pages in separate windows
    Status bar: Shows current URL and link preview on hover

  --------------------------------------------------------------------------
  eZip — Archive Manager                                      Menu: Tools
  --------------------------------------------------------------------------
    Supports: ZIP (read/write/append), TAR/TAR.GZ (read/extract)
    Open: Browse and view archive contents
    Create: Select files > create new ZIP archive
    Extract: Extract all to chosen directory
    Add: Append files to existing ZIP

  --------------------------------------------------------------------------
  eCleaner — Disk Cleanup                                     Menu: Tools
  --------------------------------------------------------------------------
    Categories: Temp files, Python cache, Log files,
                Clipboard, Browser cache, Recycle bin
    Workflow: Check categories > Scan > Review size > Clean
    Shows total reclaimable space before cleaning
    Safe: Confirms before deleting

  --------------------------------------------------------------------------
  eVPN — VPN & Proxy Manager                                  Menu: Tools
  --------------------------------------------------------------------------
    VPN Connect: OpenVPN, WireGuard, IKEv2, L2TP
    SSH SOCKS Proxy: Creates SOCKS5 tunnel through SSH
    Free Proxies: Fetches public SOCKS5/HTTP proxy lists
    Country filter: US, GB, DE, FR, JP, KR, IN, BR, and more
    Check IP: Verifies your public IP address

  --------------------------------------------------------------------------
  eChat — Chat Interface                                      Menu: Tools
  --------------------------------------------------------------------------
    Local chat with echo bot for testing
    Commands: /help, /clear, /time, /name <new_name>
    Custom username: Set in the header bar
    Color-coded: Timestamps (blue), usernames (green), system (gray)

  --------------------------------------------------------------------------
  ePaint — Drawing Canvas                                     Menu: Tools
  --------------------------------------------------------------------------
    Tools: Brush, Rectangle, Oval, Line, Eraser
    Colors: 8 quick-select colors + full color picker
    Brush size: Adjustable slider (1-20)
    Save: Export as PostScript (.ps) file
    Clear: Wipe entire canvas

  --------------------------------------------------------------------------
  ePlay — Media Player                                        Menu: Tools
  --------------------------------------------------------------------------
    Opens media files with system default player
    Controls: Play/Pause, Stop, Rewind, Forward, Prev, Next
    Volume: Adjustable slider (0-100)
    Playlist: Add multiple files, double-click to select
    Formats: MP3, WAV, OGG, FLAC, MP4, AVI, MKV

  --------------------------------------------------------------------------
  eBuffer — Clipboard Manager                                 Menu: Tools
  --------------------------------------------------------------------------
    Captures clipboard content automatically (every 2 seconds)
    20 slots maximum, newest first
    Actions per slot: Copy back, Preview, Delete
    Deduplication: Won't capture same content twice in a row
    Clear All: Removes all slots (with confirmation)

  --------------------------------------------------------------------------
  ePDF — PDF Viewer                                           Menu: Tools
  --------------------------------------------------------------------------
    Opens PDF files and extracts text for display
    Page navigation: Previous / Next with page counter
    Find: Search text within the current page
    Save Text: Export extracted text to .txt file
    Backends: pypdf, PyMuPDF, pdftotext, built-in parser

  --------------------------------------------------------------------------
  eFTP — File Transfer Client                                 Menu: Tools
  --------------------------------------------------------------------------
    FileZilla-style dual-pane layout
    Left pane: Local files with size and date
    Right pane: Remote files via SSH (ls -la)
    Transfer: Upload (local > remote), Download (remote > local)
    Actions: Delete remote, Create directory
    Protocols: SFTP, FTP, SCP

  --------------------------------------------------------------------------
  eTunnel — SSH Tunneling                                     Menu: Tools
  --------------------------------------------------------------------------
    Types: Local (-L), Remote (-R), Dynamic SOCKS (-D)
    Command preview: Shows exact SSH command before executing
    Multiple tunnels: Run several tunnels simultaneously
    Log: Shows connection status and errors

  --------------------------------------------------------------------------
  eVirusTower — Malware Scanner                               Menu: Tools
  --------------------------------------------------------------------------
    Scans files for known malware signatures (MD5 hashes)
    Pattern detection: cmd.exe del, WScript.Shell, powershell -enc
    EICAR test file detection
    Suspicious extensions: .exe, .bat, .vbs, .ps1, .scr
    Report export: Save scan results to text file

  --------------------------------------------------------------------------
  eVNC — Remote Desktop Viewer                                Menu: Tools
  --------------------------------------------------------------------------
    Connects to VNC servers using system VNC client
    Supported: TigerVNC, TightVNC, RealVNC, UltraVNC
    Quality: Low/Medium/High/Lossless
    Options: Fullscreen, View-only mode
    SSH Tunnel + VNC: Create encrypted tunnel first, then connect
    Saved connections: Store host/port/display for quick access

  --------------------------------------------------------------------------
  Snake — Classic Game                                       Menu: Games
  --------------------------------------------------------------------------
    Grid: 30x20 with adjustable speed
    Controls: Arrow keys or WASD
    Features: Score tracking, high score, food placement
    Reset: Start new game anytime

================================================================================
6. THEME & VIEW OPTIONS
================================================================================

  Toggle Theme:
    Menu: Settings > Toggle Theme
    Or click the theme button on the toolbar
    Switches between Dark (VS Code style) and Light mode

  Split View:
    Menu: View > Split Horizontal / Vertical / Quad / Single
    Assign any open tool to any pane

  Pop-out Windows:
    Right-click any tab > Pop-out to Window
    Pop-out windows support: Re-attach, Fullscreen, Stay on top

  Toggle Sidebar:  Ctrl+B or Menu: View > Toggle Sidebar
  Toggle Toolbar:  Ctrl+B or Menu: View > Toggle Toolbar
  Full Screen:     F11

================================================================================
7. CI / TESTING
================================================================================

  Run Tests:
    $ pip install -r requirements-dev.txt
    $ python -m pytest tests/ -v

  Test Coverage: 28 test files, 400+ test cases
  CI Pipeline: GitHub Actions — flake8 lint + pytest
  Matrix: Ubuntu / Windows / macOS x Python 3.11 / 3.12

  Run headless tests (no display):
    $ python -m pytest tests/ -v -m "not gui"

================================================================================
8. TROUBLESHOOTING
================================================================================

  "No module named tkinter":
    Install Python from python.org (includes tkinter by default)
    Linux: sudo apt install python3-tk

  SSH connection fails:
    Ensure ssh client is installed and in PATH
    Check hostname, port, and credentials

  Serial port not detected:
    Windows: Check Device Manager for COM ports
    Linux: Ensure user is in 'dialout' group
    macOS: Check /dev/tty.* devices

  VNC viewer not found:
    Install TigerVNC: https://tigervnc.org
    Linux: sudo apt install tigervnc-viewer
    macOS: brew install tiger-vnc

  Tests skipped (GUI tests):
    GUI tests require a display. Use xvfb-run on headless Linux.
    Non-GUI tests run with: pytest -m "not gui"

================================================================================
9. LICENSE & CREDITS
================================================================================

  License: MIT License
  Repository: https://github.com/embeddedos-org/EoSuite
  Built with Python + tkinter
  Cross-platform: Windows, macOS, Linux

  No external dependencies required for core functionality.
  Optional: pypdf (PDF reading), Pillow (image ops), python-docx (DOCX)

================================================================================
                          End of EoSuite Help Guide
================================================================================
"""


def generate():
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "docs", "EoSuite_Help_Guide.pdf"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    text = HELP_TEXT.strip()
    lines = text.split("\n")
    font_name = "Courier"
    font_size = 9
    leading = font_size + 3
    margin_left = 40
    margin_top = 40
    margin_bottom = 40
    page_width = 612
    page_height = 792
    max_lines = int((page_height - margin_top - margin_bottom) / leading)

    pages_text = []
    for i in range(0, len(lines), max_lines):
        pages_text.append(lines[i:i + max_lines])

    def pdf_escape(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    objects = []
    offsets = []

    def add_obj(content):
        objects.append(content)
        return len(objects)

    cat_id = add_obj("")
    pages_id = add_obj("")
    font_id = add_obj(
        f"{len(objects)} 0 obj\n<< /Type /Font /Subtype /Type1 "
        f"/BaseFont /{font_name} >>\nendobj"
    )

    page_ids = []
    for page_lines in pages_text:
        stream_lines = [f"BT /{font_name} {font_size} Tf"]
        y = page_height - margin_top
        for line in page_lines:
            escaped = pdf_escape(line)
            stream_lines.append(f"1 0 0 1 {margin_left} {y} Tm ({escaped}) Tj")
            y -= leading
        stream_lines.append("ET")
        stream = "\n".join(stream_lines)

        stream_id = add_obj(
            f"{len(objects)} 0 obj\n<< /Length {len(stream)} >>\n"
            f"stream\n{stream}\nendstream\nendobj"
        )
        page_id = add_obj(
            f"{len(objects)} 0 obj\n<< /Type /Page /Parent {pages_id} 0 R "
            f"/MediaBox [0 0 {page_width} {page_height}] "
            f"/Contents {stream_id} 0 R "
            f"/Resources << /Font << /Courier {font_id} 0 R >> >> >>\nendobj"
        )
        page_ids.append(page_id)

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_id - 1] = (
        f"{pages_id} 0 obj\n<< /Type /Pages /Kids [{kids}] "
        f"/Count {len(page_ids)} >>\nendobj"
    )
    objects[cat_id - 1] = (
        f"{cat_id} 0 obj\n<< /Type /Catalog /Pages {pages_id} 0 R >>\nendobj"
    )

    with open(output_path, "wb") as f:
        f.write(b"%PDF-1.4\n")
        for i, obj in enumerate(objects):
            offsets.append(f.tell())
            if not obj.startswith(f"{i + 1} 0 obj"):
                obj = f"{i + 1} 0 obj\n{obj}\nendobj"
            f.write((obj + "\n").encode("latin-1", errors="replace"))

        xref_offset = f.tell()
        f.write(b"xref\n")
        f.write(f"0 {len(objects) + 1}\n".encode())
        f.write(b"0000000000 65535 f \n")
        for off in offsets:
            f.write(f"{off:010d} 00000 n \n".encode())

        f.write(b"trailer\n")
        f.write(f"<< /Size {len(objects) + 1} /Root {cat_id} 0 R >>\n".encode())
        f.write(b"startxref\n")
        f.write(f"{xref_offset}\n".encode())
        f.write(b"%%EOF\n")

    print(f"Generated: {output_path}")
    print(f"Size: {os.path.getsize(output_path):,} bytes")
    print(f"Pages: {len(page_ids)}")


if __name__ == "__main__":
    generate()
