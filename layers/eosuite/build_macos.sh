#!/bin/bash
# ============================================
#   EoSuite — macOS Build Script
#   Creates a .app bundle and .dmg installer
# ============================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "  EoSuite — macOS Installer Builder"
echo "================================================"
echo ""

# Check Python
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3 not found. Install from https://python.org"
    exit 1
fi
echo "[1/5] Python: $($PYTHON --version)"

# Install dependencies
echo "[2/5] Installing dependencies..."
$PYTHON -m pip install --quiet --user pyinstaller pypdf Pillow python-docx 2>/dev/null

# Clean previous builds
echo "[3/5] Cleaning previous builds..."
rm -rf build dist

# Build .app bundle
echo "[4/5] Building EoSuite.app..."
$PYTHON -m PyInstaller \
    --onefile \
    --windowed \
    --name "EoSuite" \
    --icon assets/icon.ico \
    --add-data "assets/icon.ico:assets" \
    --hidden-import gui --hidden-import gui.styles \
    --hidden-import gui.toolbar --hidden-import gui.sidebar \
    --hidden-import gui.home_tab --hidden-import gui.terminal_tab \
    --hidden-import gui.split_manager --hidden-import gui.main_window \
    --hidden-import gui.apps \
    --hidden-import gui.apps.ecal --hidden-import gui.apps.etimer \
    --hidden-import gui.apps.enote --hidden-import gui.apps.eviewer \
    --hidden-import gui.apps.econverter --hidden-import gui.apps.eguard \
    --hidden-import gui.apps.eweb --hidden-import gui.apps.ezip \
    --hidden-import gui.apps.ecleaner --hidden-import gui.apps.evpn \
    --hidden-import gui.apps.echat --hidden-import gui.apps.epaint \
    --hidden-import gui.apps.eplay --hidden-import gui.apps.ebuffer \
    --hidden-import gui.apps.epdf --hidden-import gui.apps.eftp \
    --hidden-import gui.apps.etunnel --hidden-import gui.apps.evirustower \
    --hidden-import gui.apps.snake --hidden-import gui.apps.ssh_client \
    --hidden-import gui.apps.serial_term --hidden-import gui.apps.session_manager \
    --hidden-import pypdf --hidden-import PIL --hidden-import docx \
    --noconfirm \
    EoSuite_GUI.py

# Create DMG
echo "[5/5] Creating .dmg installer..."
if command -v hdiutil &>/dev/null; then
    DMG_NAME="EoSuite-1.0.0-macOS.dmg"
    DMG_DIR="dist/dmg_staging"
    mkdir -p "$DMG_DIR"
    cp dist/EoSuite "$DMG_DIR/"

    # Create Applications symlink
    ln -sf /Applications "$DMG_DIR/Applications"

    # Create DMG
    hdiutil create -volname "EoSuite" \
        -srcfolder "$DMG_DIR" \
        -ov -format UDZO \
        "dist/$DMG_NAME"

    rm -rf "$DMG_DIR"

    echo ""
    echo "================================================"
    echo "  BUILD SUCCESS!"
    echo "================================================"
    echo "  .app:  dist/EoSuite"
    echo "  .dmg:  dist/$DMG_NAME"
    echo "  Size:  $(du -h "dist/$DMG_NAME" | cut -f1)"
    echo ""
    echo "  To install: Open .dmg → drag EoSuite to Applications"
    echo "================================================"
else
    echo ""
    echo "================================================"
    echo "  BUILD SUCCESS! (no hdiutil — skipped .dmg)"
    echo "================================================"
    echo "  Binary: dist/EoSuite"
    echo "  Size:   $(du -h dist/EoSuite | cut -f1)"
    echo "  Run:    ./dist/EoSuite"
    echo "================================================"
fi
