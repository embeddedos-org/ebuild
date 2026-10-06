#!/bin/bash
# EoS ebuild — Quick installer
# Makes 'ebuild' command available immediately in any terminal.
#
# Usage:
#   ./install.sh         # Install ebuild CLI
#   ./install.sh --check # Verify installation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✅${NC} $*"; }
err()  { echo -e "${RED}❌${NC} $*"; }
warn() { echo -e "${YELLOW}⚠️${NC} $*"; }

if [ "$1" = "--check" ]; then
    echo "Checking ebuild installation..."
    if command -v ebuild &>/dev/null; then
        ok "ebuild found: $(which ebuild)"
        ebuild --version
    else
        err "ebuild not found on PATH"
    fi
    exit 0
fi

echo "Installing ebuild..."

# Step 1: pip install (use user pip if available, fall back to system)
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/pip" ]; then
    PIP="$VIRTUAL_ENV/bin/pip"
elif [ -x "$HOME/.local/bin/pip3" ]; then
    PIP="$HOME/.local/bin/pip3"
elif [ -x "$HOME/.local/bin/pip" ]; then
    PIP="$HOME/.local/bin/pip"
elif command -v pip3 &>/dev/null; then
    PIP=pip3
elif command -v pip &>/dev/null; then
    PIP=pip
else
    err "pip not found. Install python3-pip first."
    exit 1
fi

if $PIP install -e "$SCRIPT_DIR" --quiet 2>/dev/null; then
    ok "Python package installed successfully"
else
    err "Python package failed to install. Try running \"$PIP install -e '$SCRIPT_DIR'\" manually"
    exit 1
fi

# Step 2: Find where pip put the ebuild script
EBUILD_BIN=""
# An active venv is checked first: pip installed into it, so any other hit is stale.
for candidate in \
    "${VIRTUAL_ENV:+$VIRTUAL_ENV/bin/ebuild}" \
    "$HOME/.local/bin/ebuild" \
    "/usr/local/bin/ebuild" \
    "/usr/bin/ebuild" \
    "$(python3 -m site --user-base 2>/dev/null)/bin/ebuild"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
        EBUILD_BIN="$candidate"
        break
    fi
done

if [ -z "$EBUILD_BIN" ]; then
    err "Could not find installed ebuild binary"
    exit 1
fi

if [ -n "$VIRTUAL_ENV" ] && [ "$EBUILD_BIN" = "$VIRTUAL_ENV/bin/ebuild" ]; then
    warn "Warning: Installing the ebuild binary from a virtual environment."
    warn "         This means its successful execution will depend on the virtual env existence."
fi

ok "ebuild binary: $EBUILD_BIN"

# Step 3: Make it globally available
# Try each location in order until one works
INSTALLED=false

# Option A: Already on PATH?
if command -v ebuild &>/dev/null; then
    ok "ebuild already on PATH"
    INSTALLED=true
fi

# Option B: Copy to /usr/local/bin (may need sudo)
if [ "$INSTALLED" = false ] && [ -w /usr/local/bin ]; then
    cp "$EBUILD_BIN" /usr/local/bin/ebuild
    chmod +x /usr/local/bin/ebuild
    ok "Copied to /usr/local/bin/ebuild"
    INSTALLED=true
fi

# Option C: Symlink to /usr/local/bin with sudo
if [ "$INSTALLED" = false ]; then
    if sudo -n true 2>/dev/null; then
        sudo ln -sf "$EBUILD_BIN" /usr/local/bin/ebuild
        ok "Symlinked to /usr/local/bin/ebuild (sudo)"
        INSTALLED=true
    fi
fi

# Option D: Add to PATH via shell config
if [ "$INSTALLED" = false ]; then
    EBUILD_DIR="$(dirname "$EBUILD_BIN")"

    # Add to all shell configs
    for rc in "$HOME/.bashrc" "$HOME/.profile" "$HOME/.zshrc"; do
        if [ -f "$rc" ] || [ "$rc" = "$HOME/.bashrc" ]; then
            if ! grep -q "$EBUILD_DIR" "$rc" 2>/dev/null; then
                echo "export PATH=\"$EBUILD_DIR:\$PATH\"" >> "$rc"
            fi
        fi
    done

    # Also export for current session
    export PATH="$EBUILD_DIR:$PATH"
    ok "Added $EBUILD_DIR to PATH in .bashrc/.profile"
    INSTALLED=true
fi

# Step 4: Verify
echo ""
if command -v ebuild &>/dev/null; then
    ok "ebuild is ready!"
    ebuild --version
    echo ""
    echo "Try: ebuild --help"
else
    echo "ebuild installed but requires a new terminal to take effect."
    echo "Run: source ~/.bashrc"
    echo "Or:  exec bash"
fi
