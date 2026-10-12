#!/bin/bash
# ============================================================================
# AetherOS — macOS Installer
# ============================================================================
# Double-click this file in Finder to install AetherOS on macOS.
#
# What it does:
#   1. Checks for macOS, Apple Silicon vs Intel, Python 3.11+, Homebrew
#   2. Creates a venv at ~/Library/Application Support/AetherOS/venv
#   3. Installs the package with `pip install -e .`
#   4. Creates launcher symlinks at /usr/local/bin/{aetheros,AetherOS}
#   5. Ensures /usr/local/bin is on PATH in shell config
#   6. Creates a Launchpad .app bundle
#   7. Suggests shell completion setup
#   8. Verifies the installation
# ============================================================================

set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────────────
BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $*"; }
info() { echo -e "${CYAN}→${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; exit 1; }

# ── 1. macOS check ──────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}◇  AetherOS — macOS Installer${NC}"
echo ""

[[ "$(uname)" == "Darwin" ]] || fail "This installer is for macOS only."

# ── 2. Architecture detection ───────────────────────────────────────────────
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    ok "Apple Silicon ($ARCH) detected"
    BREW_PREFIX="/opt/homebrew"
elif [[ "$ARCH" == "x86_64" ]]; then
    ok "Intel ($ARCH) detected"
    BREW_PREFIX="/usr/local"
else
    fail "Unknown architecture: $ARCH"
fi

# ── 3. Python 3.11+ ─────────────────────────────────────────────────────────
info "Checking for Python 3.11+..."
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)
        if [[ -n "$ver" ]] && python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    warn "Python 3.11+ not found. Attempting to install via Homebrew..."
    if command -v brew &>/dev/null; then
        brew install python@3.12
        PYTHON="$(brew --prefix python@3.12)/bin/python3"
    else
        fail "Python 3.11+ is required. Install it from https://www.python.org/downloads/ or via Homebrew."
    fi
fi

PY_VER=$("$PYTHON" --version 2>&1)
ok "$PY_VER"

# ── 3b. Homebrew check ─────────────────────────────────────────────────────
if command -v brew &>/dev/null; then
    BREW_VER=$(brew --version 2>&1 | head -1)
    ok "$BREW_VER"
else
    warn "Homebrew not found (optional but recommended). Install from https://brew.sh/"
fi

# ── 4. Virtual environment ──────────────────────────────────────────────────
VENV_DIR="$HOME/Library/Application Support/AetherOS/venv"
info "Creating virtual environment at $VENV_DIR ..."
mkdir -p "$HOME/Library/Application Support/AetherOS"
if [[ -d "$VENV_DIR" ]]; then
    warn "Removing existing venv ..."
    rm -rf "$VENV_DIR"
fi
"$PYTHON" -m venv "$VENV_DIR"
VENV_PYTHON="$VENV_DIR/bin/python"
ok "Virtual environment created"

# ── 5. Install package ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
info "Installing AetherOS from $SCRIPT_DIR ..."
cd "$SCRIPT_DIR"

# Upgrade pip first
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel --quiet

# Install the package in editable mode
if "$VENV_PYTHON" -m pip install -e . 2>&1; then
    ok "Package installed successfully"
else
    warn "Editable install failed; trying non-editable ..."
    "$VENV_PYTHON" -m pip install . 2>&1 || fail "pip install failed. Check the output above."
fi

# ── 6. Create launcher scripts ──────────────────────────────────────────────
info "Creating launcher scripts in /usr/local/bin/ ..."

LAUNCHER_CONTENT='#!/bin/bash
# AetherOS launcher — activates venv and runs the CLI
export PATH="'"$VENV_DIR"'/bin:$PATH"
exec "'"$VENV_DIR"'/bin/aetheros" "$@"
'

echo "$LAUNCHER_CONTENT" | sudo tee /usr/local/bin/aetheros >/dev/null
sudo chmod 755 /usr/local/bin/aetheros
ok "Created /usr/local/bin/aetheros"

sudo cp /usr/local/bin/aetheros /usr/local/bin/AetherOS
ok "Created /usr/local/bin/AetherOS"

# ── 7. PATH setup ──────────────────────────────────────────────────────────
if ! echo "$PATH" | tr ':' '\n' | grep -qx '/usr/local/bin'; then
    info "Adding /usr/local/bin to PATH ..."
    for RC in "$HOME/.zshrc" "$HOME/.bash_profile"; do
        if [[ -f "$RC" ]]; then
            if ! grep -q '/usr/local/bin' "$RC" 2>/dev/null; then
                echo "" >> "$RC"
                echo "# AetherOS — ensure /usr/local/bin is on PATH" >> "$RC"
                echo 'export PATH="/usr/local/bin:$PATH"' >> "$RC"
                ok "Added /usr/local/bin to PATH in $RC"
            fi
        fi
    done
    # If neither exists, create .zshrc
    if [[ ! -f "$HOME/.zshrc" && ! -f "$HOME/.bash_profile" ]]; then
        echo 'export PATH="/usr/local/bin:$PATH"' >> "$HOME/.zshrc"
        ok "Created ~/.zshrc with /usr/local/bin on PATH"
    fi
    warn "Restart your terminal or run: export PATH=\"/usr/local/bin:\$PATH\""
else
    ok "/usr/local/bin is already on PATH"
fi

# ── 8. Launchpad .app bundle ────────────────────────────────────────────────
info "Creating Launchpad icon ..."

APP_DIR="$HOME/Applications/AetherOS.app"
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

cat > "$APP_DIR/Contents/Info.plist" <<-PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>AetherOS</string>
    <key>CFBundleIdentifier</key>
    <string>com.aetheros.cli</string>
    <key>CFBundleName</key>
    <string>AetherOS</string>
    <key>CFBundleDisplayName</key>
    <string>AetherOS</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
PLIST

cat > "$APP_DIR/Contents/MacOS/AetherOS" <<-LAUNCHER
#!/bin/bash
# AetherOS .app launcher — opens Terminal and runs the CLI
PATH="$VENV_DIR/bin:\$PATH"
exec "\$TERMINAL_PROG" /usr/local/bin/aetheros
LAUNCHER
chmod +x "$APP_DIR/Contents/MacOS/AetherOS"

# Create a simple icon placeholder (a 1x1 transparent PNG as a doc icon)
# This gives the app a basic icon in Launchpad; users can replace it later.
if [[ ! -f "$APP_DIR/Contents/Resources/AetherOS.icns" ]]; then
    # Generate a minimal pixel using base64 (tiny valid PNG)
    echo -n iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg== | base64 -d > "$APP_DIR/Contents/Resources/AetherOS.icns" 2>/dev/null || true
fi

ok "Created $APP_DIR (add to dock / Launchpad)"

# ── 9. Shell completion suggestion ──────────────────────────────────────────
echo ""
info "Shell completion (optional):"
echo ""
echo "  If you use bash, add to ~/.bash_profile:"
echo "      source <(/usr/local/bin/aetheros completions bash)"
echo ""
echo "  If you use zsh, add to ~/.zshrc:"
echo "      source <(/usr/local/bin/aetheros completions zsh)"
echo ""
echo "  If you use fish:"
echo "      /usr/local/bin/aetheros completions fish | source"
echo ""

# ── 10. Verify installation ────────────────────────────────────────────────
echo ""
info "Verifying installation ..."
echo ""

check_cmd() {
    local cmd="$1"
    if command -v "$cmd" &>/dev/null; then
        local ver_output
        ver_output=$("$cmd" --version 2>&1 || true)
        ok "$cmd is installed: $ver_output"
    else
        fail "$cmd not found after installation."
    fi
}

check_cmd aetheros
check_cmd AetherOS

# ── 11. Success message ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║        AetherOS installation complete!        ║${NC}"
echo -e "${BOLD}${GREEN}╚═══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Venv:     $VENV_DIR"
echo "  Launcher: /usr/local/bin/aetheros"
echo "  Launcher: /usr/local/bin/AetherOS"
echo "  Launchpad: $APP_DIR"
echo ""
echo "  Next steps:"
echo "    1. Restart your terminal or run:"
echo "       export PATH=\"/usr/local/bin:\$PATH\""
echo ""
echo "    2. Run the setup wizard:"
echo "       aetheros setup"
echo ""
echo "    3. Start the CLI:"
echo "       aetheros"
echo ""
echo "    4. Uninstall by running:"
echo "       sudo rm -f /usr/local/bin/aetheros /usr/local/bin/AetherOS"
echo "       rm -rf \"$VENV_DIR\" \"$APP_DIR\""
echo ""
