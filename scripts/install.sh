#!/usr/bin/env bash
# wlanspawn installer
# Usage: curl -sSL https://raw.githubusercontent.com/yourusername/wlanspawn/main/scripts/install.sh | bash

set -euo pipefail

REPO="https://github.com/yourusername/wlanspawn"
MIN_PYTHON="3.9"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
DIM='\033[2m'
NC='\033[0m' # No Color

info()    { echo -e "${CYAN}→${NC} $*"; }
success() { echo -e "${GREEN}✓${NC} $*"; }
warn()    { echo -e "${YELLOW}!${NC} $*"; }
error()   { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

echo ""
echo -e "${CYAN}╻ ╻╻  ┏━┓┏┓╻┏━┓┏━┓┏━┓╻ ╻┏┓╻${NC}"
echo -e "${CYAN}┃╻┃┃  ┣━┫┃┗┫┗━┓┣━┛┣━┫┃╻┃┃┗┫${NC}"
echo -e "${CYAN}┗┻┛┗━╸╹ ╹╹ ╹┗━┛╹  ╹ ╹┗┻┛╹ ╹${NC}"
echo ""
echo -e "${DIM}Wi-Fi hotspot manager installer${NC}"
echo ""

# --- Check OS ---
if [[ "$(uname)" == "Darwin" ]]; then
    warn "macOS is not yet fully supported. Some features may not work."
elif [[ "$(uname)" != "Linux" ]]; then
    error "This installer only supports Linux (and best-effort macOS)."
fi

# --- Check Python ---
PYTHON=""
for py in python3 python3.12 python3.11 python3.10 python3.9; do
    if command -v "$py" &>/dev/null; then
        ver=$($py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=${ver%%.*}
        minor=${ver#*.}
        if (( major >= 3 && minor >= 9 )); then
            PYTHON="$py"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    error "Python $MIN_PYTHON+ is required. Install it from https://python.org"
fi

success "Found Python: $($PYTHON --version)"

# --- Prefer pipx ---
if command -v pipx &>/dev/null; then
    info "Installing wlanspawn via pipx …"
    pipx install wlanspawn
    success "Installed! Run: wlanspawn --version"
    echo ""
    echo -e "  ${DIM}Next steps:${NC}"
    echo -e "  ${CYAN}sudo wlanspawn init${NC}   — Configure hotspot"
    echo -e "  ${CYAN}sudo wlanspawn up${NC}     — Start hotspot"
    echo -e "  ${CYAN}wlanspawn doctor${NC}      — Check dependencies"
    echo ""
    exit 0
fi

# --- Fall back to pip ---
warn "pipx not found, falling back to pip --user."
info "Tip: Install pipx with:  $PYTHON -m pip install --user pipx"
echo ""

info "Installing wlanspawn via pip …"
"$PYTHON" -m pip install --user --quiet wlanspawn

# Ensure ~/.local/bin is on PATH
LOCAL_BIN="$HOME/.local/bin"
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    warn "$LOCAL_BIN is not on your PATH."
    echo ""
    echo -e "  Add to your shell config (${DIM}~/.bashrc${NC} / ${DIM}~/.zshrc${NC} / ${DIM}~/.config/fish/config.fish${NC}):"
    echo -e "  ${CYAN}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    echo ""
    echo -e "  Then reload: ${CYAN}source ~/.bashrc${NC}"
    echo ""
fi

success "wlanspawn installed!"
echo ""
echo -e "  ${DIM}Next steps:${NC}"
echo -e "  ${CYAN}sudo wlanspawn init${NC}   — Configure hotspot"
echo -e "  ${CYAN}sudo wlanspawn up${NC}     — Start hotspot"
echo -e "  ${CYAN}wlanspawn doctor${NC}      — Check dependencies"
echo ""
