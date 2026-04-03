#!/bin/bash
# ============================================
#   EoSuite — Linux Build Script
#   Creates .deb package and .AppImage
# ============================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="EoSuite"
APP_VERSION="1.0.0"
APP_DESC="Super Lightweight Terminal Suite — SSH, Serial, Tools, Games"

echo "================================================"
echo "  EoSuite — Linux Installer Builder"
echo "================================================"
echo ""

# Check Python
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3 not found."
    echo "Install: sudo apt install python3 python3-pip python3-tk"
    exit 1
fi
echo "[1/6] Python: $($PYTHON --version)"

# Check tkinter
$PYTHON -c "import tkinter" 2>/dev/null || {
    echo "ERROR: tkinter not found."
    echo "Install: sudo apt install python3-tk"
    exit 1
}

# Install dependencies
echo "[2/6] Installing dependencies..."
$PYTHON -m pip install --quiet --user pyinstaller pypdf Pillow python-docx 2>/dev/null

# Clean
echo "[3/6] Cleaning previous builds..."
rm -rf build dist

# Build binary
echo "[4/6] Building binary with PyInstaller..."
$PYTHON -m PyInstaller \
    --onefile \
    --windowed \
    --name "$APP_NAME" \
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

if [ ! -f "dist/$APP_NAME" ]; then
    echo "ERROR: Binary build failed!"
    exit 1
fi

BINARY_SIZE=$(du -h "dist/$APP_NAME" | cut -f1)
echo "  Binary: dist/$APP_NAME ($BINARY_SIZE)"

# ── Build .deb package ────────────────────────────────────

echo "[5/6] Building .deb package..."

DEB_NAME="${APP_NAME,,}_${APP_VERSION}_amd64"
DEB_DIR="dist/$DEB_NAME"

mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/usr/bin"
mkdir -p "$DEB_DIR/usr/share/applications"
mkdir -p "$DEB_DIR/usr/share/pixmaps"
mkdir -p "$DEB_DIR/usr/share/doc/$APP_NAME"

# Copy binary
cp "dist/$APP_NAME" "$DEB_DIR/usr/bin/EoSuite"
chmod 755 "$DEB_DIR/usr/bin/EoSuite"

# Control file
cat > "$DEB_DIR/DEBIAN/control" << EOF
Package: EoSuite
Version: $APP_VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: libc6 (>= 2.17)
Maintainer: EoSuite Team <EoSuite@example.com>
Description: $APP_DESC
 EoSuite is a lightweight cross-platform terminal suite featuring
 SSH client, serial/UART terminal, calculator, timer, text editor,
 hex viewer, web browser, archive manager, system cleaner, VPN manager,
 chat, paint, media player, PDF reader, FTP client, and more.
 .
 Single portable binary with MobaXterm-style GUI.
EOF

# Desktop entry
cat > "$DEB_DIR/usr/share/applications/EoSuite.desktop" << EOF
[Desktop Entry]
Type=Application
Name=EoSuite
Comment=$APP_DESC
Exec=/usr/bin/EoSuite
Icon=EoSuite
Terminal=false
Categories=System;TerminalEmulator;Utility;Network;
Keywords=terminal;ssh;serial;ftp;vpn;tools;
EOF

# Copy icon (convert .ico to .png if possible, otherwise use as-is)
if command -v convert &>/dev/null; then
    convert "assets/icon.ico" -resize 256x256 "$DEB_DIR/usr/share/pixmaps/EoSuite.png" 2>/dev/null || \
    cp "assets/icon.ico" "$DEB_DIR/usr/share/pixmaps/EoSuite.ico"
else
    cp "assets/icon.ico" "$DEB_DIR/usr/share/pixmaps/EoSuite.ico"
fi

# Copyright
cat > "$DEB_DIR/usr/share/doc/$APP_NAME/copyright" << EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: EoSuite
License: MIT
Copyright: 2026 EoSuite Team

License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files, to deal in the Software
 without restriction, including without limitation the rights to use, copy,
 modify, merge, publish, distribute, sublicense, and/or sell copies of the
 Software, and to permit persons to whom the Software is furnished to do so,
 subject to the following conditions: The above copyright notice and this
 permission notice shall be included in all copies or substantial portions
 of the Software.
EOF

# Build .deb
if command -v dpkg-deb &>/dev/null; then
    dpkg-deb --build "$DEB_DIR" "dist/${DEB_NAME}.deb"
    DEB_SIZE=$(du -h "dist/${DEB_NAME}.deb" | cut -f1)
    echo "  .deb: dist/${DEB_NAME}.deb ($DEB_SIZE)"
else
    echo "  SKIP: dpkg-deb not found (install dpkg to build .deb)"
fi

rm -rf "$DEB_DIR"

# ── Build .AppImage ───────────────────────────────────────

echo "[6/6] Building .AppImage..."

APPIMAGE_DIR="dist/AppImage"
mkdir -p "$APPIMAGE_DIR/usr/bin"
mkdir -p "$APPIMAGE_DIR/usr/share/applications"
mkdir -p "$APPIMAGE_DIR/usr/share/icons/hicolor/256x256/apps"

cp "dist/$APP_NAME" "$APPIMAGE_DIR/usr/bin/EoSuite"
chmod 755 "$APPIMAGE_DIR/usr/bin/EoSuite"

# AppRun
cat > "$APPIMAGE_DIR/AppRun" << 'EOF'
#!/bin/bash
SELF="$(readlink -f "$0")"
HERE="${SELF%/*}"
exec "${HERE}/usr/bin/EoSuite" "$@"
EOF
chmod 755 "$APPIMAGE_DIR/AppRun"

# Desktop file at root
cat > "$APPIMAGE_DIR/EoSuite.desktop" << EOF
[Desktop Entry]
Type=Application
Name=EoSuite
Exec=EoSuite
Icon=EoSuite
Categories=System;TerminalEmulator;Utility;
EOF

# Icon
if command -v convert &>/dev/null; then
    convert "assets/icon.ico" -resize 256x256 \
        "$APPIMAGE_DIR/usr/share/icons/hicolor/256x256/apps/EoSuite.png" 2>/dev/null && \
    cp "$APPIMAGE_DIR/usr/share/icons/hicolor/256x256/apps/EoSuite.png" \
        "$APPIMAGE_DIR/EoSuite.png" || \
    cp "assets/icon.ico" "$APPIMAGE_DIR/EoSuite.png"
else
    cp "assets/icon.ico" "$APPIMAGE_DIR/EoSuite.png"
fi

# Download appimagetool if needed
APPIMAGE_TOOL="dist/appimagetool"
if [ ! -f "$APPIMAGE_TOOL" ]; then
    ARCH=$(uname -m)
    TOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage"
    echo "  Downloading appimagetool..."
    curl -sL "$TOOL_URL" -o "$APPIMAGE_TOOL" 2>/dev/null && chmod +x "$APPIMAGE_TOOL"
fi

if [ -x "$APPIMAGE_TOOL" ]; then
    APPIMAGE_NAME="EoSuite-${APP_VERSION}-$(uname -m).AppImage"
    "$APPIMAGE_TOOL" "$APPIMAGE_DIR" "dist/$APPIMAGE_NAME" 2>/dev/null
    APPIMAGE_SIZE=$(du -h "dist/$APPIMAGE_NAME" | cut -f1)
    echo "  .AppImage: dist/$APPIMAGE_NAME ($APPIMAGE_SIZE)"
else
    echo "  SKIP: appimagetool not available"
    echo "  Manual: Download appimagetool and run:"
    echo "    appimagetool dist/AppImage dist/EoSuite-${APP_VERSION}.AppImage"
fi

rm -rf "$APPIMAGE_DIR"

# ── Summary ───────────────────────────────────────────────

echo ""
echo "================================================"
echo "  BUILD COMPLETE!"
echo "================================================"
echo "  Binary:    dist/$APP_NAME"
[ -f "dist/${DEB_NAME}.deb" ] && echo "  .deb:      dist/${DEB_NAME}.deb"
[ -f "dist/EoSuite-${APP_VERSION}-"*".AppImage" ] && echo "  .AppImage: dist/EoSuite-${APP_VERSION}-*.AppImage"
echo ""
echo "  Install .deb:      sudo dpkg -i dist/${DEB_NAME}.deb"
echo "  Run .AppImage:     chmod +x dist/*.AppImage && ./dist/*.AppImage"
echo "  Run binary:        ./dist/$APP_NAME"
echo "================================================"
