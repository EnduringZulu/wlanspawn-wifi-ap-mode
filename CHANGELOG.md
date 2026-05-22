# Changelog

All notable changes to wlanspawn will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- macOS backend (planned)
- Systemd unit file support

---

## [0.1.0] — 2024-XX-XX

### Added
- `wlanspawn init` — interactive setup wizard with interface auto-detection
- `wlanspawn up` — start hotspot (supports `--ssid`, `--password`, `--iface` overrides)
- `wlanspawn down` — stop hotspot and clean up
- `wlanspawn status` — rich status panel with `--json` option
- `wlanspawn clients` — connected client table with `--watch` and `--json` options
- `wlanspawn doctor` — dependency health checker with fix hints
- `wlanspawn config show/edit/path` — configuration management subcommands
- **NetworkManager backend** — nmcli + `ipv4.method shared` (recommended for desktop Linux)
- **hostapd backend** — hostapd + dnsmasq + iptables (for headless/server Linux)
- **Windows backend** — netsh hosted network + PowerShell ICS (best-effort)
- Auto OS/backend detection (Fedora, RHEL, Debian, Ubuntu, Arch, Windows)
- WPA2-PSK security (minimum 8-character password enforced)
- Hidden SSID support
- TOML configuration format with `~/.config/wlanspawn/config.toml`
- Rich terminal output with panels, tables, and color
- `--debug` flag and log file support
- `--json` output flag for scripting integration
- One-liner install script (`scripts/install.sh`)
- GitHub Actions CI (lint + test matrix Python 3.9–3.12 + Windows smoke test)
- GitHub Actions release automation (PyPI publish on tag)

[Unreleased]: https://github.com/yourusername/wlanspawn/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/wlanspawn/releases/tag/v0.1.0
