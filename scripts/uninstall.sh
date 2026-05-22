#!/usr/bin/env bash
# wlanspawn uninstaller

set -euo pipefail

echo "Uninstalling wlanspawn …"

if command -v pipx &>/dev/null && pipx list 2>/dev/null | grep -q wlanspawn; then
    pipx uninstall wlanspawn
elif command -v pip3 &>/dev/null; then
    pip3 uninstall -y wlanspawn 2>/dev/null || pip3 uninstall --user -y wlanspawn 2>/dev/null || true
fi

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/wlanspawn"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/wlanspawn"

if [[ -d "$CONFIG_DIR" ]]; then
    read -rp "Remove config directory $CONFIG_DIR? [y/N] " yn
    if [[ "$yn" =~ ^[Yy]$ ]]; then
        rm -rf "$CONFIG_DIR"
        echo "✓ Config removed."
    fi
fi

if [[ -d "$DATA_DIR" ]]; then
    read -rp "Remove data/log directory $DATA_DIR? [y/N] " yn
    if [[ "$yn" =~ ^[Yy]$ ]]; then
        rm -rf "$DATA_DIR"
        echo "✓ Data/logs removed."
    fi
fi

echo "✓ wlanspawn uninstalled."
