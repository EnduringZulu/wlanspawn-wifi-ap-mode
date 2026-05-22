# wlanspawn

<div align="center">

```
╻ ╻╻  ┏━┓┏┓╻┏━┓┏━┓┏━┓╻ ╻┏┓╻
┃╻┃┃  ┣━┫┃┗┫┗━┓┣━┛┣━┫┃╻┃┃┗┫
┗┻┛┗━╸╹ ╹╹ ╹┗━┛╹  ╹ ╹┗┻┛╹ ╹
```

**Turn any Wi-Fi adapter into a hotspot in seconds.**

[![CI](https://github.com/yourusername/wlanspawn/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/wlanspawn/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/wlanspawn.svg)](https://pypi.org/project/wlanspawn/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform: Linux | Windows](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey.svg)](#supported-platforms)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

</div>

---

## Overview

**wlanspawn** is a cross-platform CLI tool that bridges your internet connection to a Wi-Fi hotspot with a single command. Point it at your internet source interface (`wlan0`, `eth0`, …) and your AP-capable adapter (`wlan1`), and it handles everything: access point creation, DHCP, NAT, and IP forwarding.

```
  ┌─────────────┐          ┌──────────────────┐          ┌──────────────┐
  │  Internet   │ ──wlan0──│    wlanspawn     │──wlan1───│ Your devices │
  │  (router)   │          │  (this machine)  │    AP    │ phone/laptop │
  └─────────────┘          └──────────────────┘          └──────────────┘
```

### Why wlanspawn?

| | wlanspawn | `create_ap` | `linux-wifi-hotspot` | `nmcli` manual |
|---|---|---|---|---|
| Single command start | ✅ | ✅ | ✅ | ❌ |
| Interactive setup wizard | ✅ | ❌ | ✅ | ❌ |
| Rich status / client view | ✅ | ❌ | ❌ | ❌ |
| Dependency doctor | ✅ | ❌ | ❌ | ❌ |
| Windows support | ✅ (best-effort) | ❌ | ❌ | ❌ |
| Multiple backends | ✅ | ❌ | ❌ | — |
| Saved config (no re-entry) | ✅ | ❌ | ❌ | ❌ |
| `pip install` | ✅ | ❌ | ❌ | ❌ |

---

## Demo

```
$ sudo wlanspawn init

╭──────────────────────────────────────────╮
│ wlanspawn configuration wizard           │
│ Press Enter to accept the default shown  │
╰──────────────────────────────────────────╯

 Detected wireless interfaces
 Interface   MAC                State   AP capable
 wlan0       aa:bb:cc:dd:ee:ff  up      ✓
 wlan1       11:22:33:44:55:66  down    ✓

  Internet source interface: wlan0
  Hotspot AP interface: wlan1
  SSID: MyHotspot
  Password: supersecret
  Band [2.4GHz/5GHz]: 2.4GHz
  Channel: 6
  Hide SSID? [y/N]: N
  Backend [auto/networkmanager/hostapd/windows]: auto

✓ Config saved → /home/user/.config/wlanspawn/config.toml

$ sudo wlanspawn up

↑ Starting hotspot MyHotspot on wlan1 …
  Internet source : wlan0
  Band / Channel  : 2.4GHz / ch6
  Gateway         : 192.168.73.1
  Backend         : auto

Using backend: networkmanager

╭──────────────────────────────────────╮
│ ✓ Hotspot is live!                   │
│                                      │
│   SSID     : MyHotspot              │
│   Password : supersecret            │
│   Gateway  : 192.168.73.1           │
│                                      │
│ Run wlanspawn status or             │
│     wlanspawn clients to monitor.   │
╰──────────────────────────────────────╯

$ sudo wlanspawn clients

  Connected clients (2)
  ┌───────────────────┬───────────────┬──────────────┬──────────┬─────────┬─────────┐
  │ MAC Address       │ IP Address    │ Hostname     │ Signal   │ ↓ RX    │ ↑ TX    │
  ├───────────────────┼───────────────┼──────────────┼──────────┼─────────┼─────────┤
  │ aa:bb:cc:11:22:33 │ 192.168.73.10 │ android-home │ -58 dBm  │ 42 MB   │ 3 MB    │
  │ de:ad:be:ef:ca:fe │ 192.168.73.11 │ —            │ -72 dBm  │ 1 MB    │ 120 KB  │
  └───────────────────┴───────────────┴──────────────┴──────────┴─────────┴─────────┘

$ sudo wlanspawn doctor

╭──────────────────────────────────────────────╮
│ wlanspawn doctor                             │
│ Checking system dependencies …              │
╰──────────────────────────────────────────────╯

  ✓  python          Python 3.12.3
  ✓  privileges      Running as root / administrator
  ✓  ip              `ip` found
  ✓  iptables        `iptables` found
  ✓  iw              `iw` found — AP capability detection available
  !  ip_forward      IPv4 forwarding currently disabled
                     wlanspawn will enable it automatically with `wlanspawn up`
  ✓  nmcli           `nmcli` found: nmcli tool, version 1.46.0
  ✓  NetworkManager  NetworkManager service is running

  6 passed  1 warnings  0 failed

  ✓ All checks passed. You're good to go!
```

---

## Features

- 🚀 **One-command hotspot** — `wlanspawn up` does everything
- 🔧 **Interactive init wizard** — guided setup with interface auto-detection
- 💾 **Persistent config** — configure once, run forever
- 🏥 **`doctor` command** — diagnoses missing dependencies with fix hints
- 👥 **Client monitoring** — live table of connected devices with signal & bytes
- 📡 **Multi-backend** — NetworkManager, hostapd+dnsmasq, or Windows netsh
- 🖥️ **Cross-platform** — Fedora, RHEL, Debian, Ubuntu, Arch, Windows
- 🔒 **WPA2-PSK** — secure by default, hidden SSID optional
- 📊 **JSON output** — `--json` flag for scripting / monitoring integrations
- 🔁 **Watch mode** — `wlanspawn clients --watch` auto-refreshes

---

## Supported Platforms

| Platform | Backend | Status |
|---|---|---|
| Fedora / RHEL | NetworkManager | ✅ Full support |
| Debian / Ubuntu | NetworkManager | ✅ Full support |
| Arch Linux | NetworkManager / hostapd | ✅ Full support |
| Generic Linux | hostapd + dnsmasq | ✅ Full support |
| Windows 10/11 | netsh hosted network | ⚠️ Best-effort |
| macOS | — | 🔜 Planned |

**Kernel requirement:** Linux 4.4+ (nl80211 with AP mode support)

---

## Installation

### System Dependencies

Before installing wlanspawn, ensure you have the required system packages:

#### **Fedora / RHEL**
```bash
sudo dnf install -y python3 python3-pip iw hostapd dnsmasq NetworkManager
```

#### **Debian / Ubuntu**
```bash
sudo apt install -y python3 python3-pip iw hostapd dnsmasq network-manager
```

#### **Arch Linux**
```bash
sudo pacman -S python python-pip iw hostapd dnsmasq networkmanager
```

---

### Install wlanspawn

#### **Option 1: From source (recommended for now)**

```bash
# Clone the repository
git clone https://github.com/yourusername/wlanspawn.git
cd wlanspawn

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"

# Or install without dev dependencies
pip install -e .

# Verify installation
wlanspawn --version
```

#### **Option 2: pipx (isolated install)**

*Coming soon when published to PyPI*

```bash
pipx install wlanspawn
```

#### **Option 3: pip (system or virtualenv)**

*Coming soon when published to PyPI*

```bash
pip install wlanspawn
# or
pip install --user wlanspawn
```

#### **Option 4: One-liner install script (Linux)**

```bash
curl -sSL https://raw.githubusercontent.com/yourusername/wlanspawn/main/scripts/install.sh | bash
```

---

### Post-Installation

After installation, verify everything works:

```bash
# Check installation
wlanspawn --version

# Run system check (no root needed)
wlanspawn doctor

# Initialize configuration
sudo wlanspawn init
```

---

### Distro packages (coming soon)

| Distro | Command |
|---|---|
| Fedora/RHEL | `dnf install wlanspawn` *(pending)* |
| Debian/Ubuntu | `apt install wlanspawn` *(pending)* |
| Arch (AUR) | `yay -S wlanspawn` *(pending)* |

---

## Quick Start

Get a hotspot running in 30 seconds:

```bash
# 1. Install system dependencies (Fedora example)
sudo dnf install -y python3 python3-pip iw NetworkManager

# 2. Clone and install wlanspawn
git clone https://github.com/yourusername/wlanspawn.git
cd wlanspawn
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 3. Run the setup wizard
sudo wlanspawn init
# Follow the prompts to configure your hotspot

# 4. Start the hotspot
sudo wlanspawn up

# 5. Monitor connected clients
sudo wlanspawn clients --watch
```

That's it! Your hotspot is now broadcasting.

---

## Usage

### Basic Commands

##### `wlanspawn init`

Run the interactive setup wizard. Saves your config to `~/.config/wlanspawn/config.toml`.

```bash
sudo wlanspawn init                    # Start interactive wizard
sudo wlanspawn init --force            # Re-run even if config exists
```

**What it does:**
- Auto-detects wireless interfaces
- Checks which interfaces support AP mode
- Guides you through SSID, password, channel selection
- Saves config for future use

---

#### `wlanspawn up`

Start the hotspot using your saved config.

```bash
sudo wlanspawn up                      # Use saved config
sudo wlanspawn up --ssid "GuestNet" --password "temppass123"  # Override settings
sudo wlanspawn up --iface wlan1        # Override AP interface
```

**What it does:**
- Validates configuration
- Selects and initializes the appropriate backend
- Configures the AP interface
- Sets up DHCP server
- Enables NAT/IP forwarding
- Starts broadcasting the hotspot

---

#### `wlanspawn down`

Stop the hotspot and clean up.

```bash
sudo wlanspawn down
```

**What it does:**
- Stops the AP
- Tears down DHCP server
- Removes NAT rules
- Restores interface to original state

---

#### `wlanspawn status`

Show current hotspot configuration and running state.

```bash
sudo wlanspawn status                  # Human-readable table
sudo wlanspawn status --json           # Machine-readable output
```

**Example output:**
```
Hotspot Status

 Key              Value
 Running          ✓ Yes
 SSID             MyHotspot
 Backend          networkmanager
 AP Interface     wlan1
 Internet Source  wlan0
 Gateway          192.168.73.1
 Band / Channel   2.4GHz / ch6
 Connected clients 2
```

---

#### `wlanspawn clients`

List connected devices with IP, hostname, signal strength, and traffic.

```bash
sudo wlanspawn clients                 # Show once
sudo wlanspawn clients --watch         # Auto-refresh every 5s (Ctrl+C to stop)
sudo wlanspawn clients --json          # JSON output for scripts
```

**Example output:**
```
Connected clients (2)

 MAC Address       IP Address    Hostname     Signal   ↓ RX    ↑ TX
 aa:bb:cc:11:22:33 192.168.73.10 android-home -58 dBm  42 MB   3 MB
 de:ad:be:ef:ca:fe 192.168.73.11 —            -72 dBm  1 MB    120 KB
```

---

#### `wlanspawn doctor`

Check that all runtime dependencies are present and correctly configured.

```bash
wlanspawn doctor                       # No sudo needed
wlanspawn doctor --backend networkmanager  # Check specific backend
```

**What it checks:**
- Python version
- Root privileges (when needed)
- Network tools (`ip`, `iw`, `iptables`)
- Backend availability (`nmcli`, `hostapd`, `dnsmasq`)
- IP forwarding configuration
- Service status (NetworkManager, etc.)

---

#### `wlanspawn config`

Manage the configuration file directly.

```bash
wlanspawn config show                  # Print config with syntax highlighting
wlanspawn config edit                  # Open in $EDITOR (vim, nano, etc.)
wlanspawn config path                  # Print config file location
```

---

### Advanced Usage Examples

#### Temporary guest network

```bash
# Quick one-off hotspot without saving config
sudo wlanspawn up --ssid "Guest-WiFi-2024" --password "temporary123" --iface wlan1
```

#### Monitor clients in real-time

```bash
# Watch mode with auto-refresh
sudo wlanspawn clients --watch
```

#### Scripting / automation

```bash
# Get client count for monitoring
CLIENT_COUNT=$(sudo wlanspawn clients --json | jq '. | length')
echo "Connected clients: $CLIENT_COUNT"

# Check if hotspot is running
if sudo wlanspawn status --json | jq -e '.running == true' > /dev/null; then
    echo "Hotspot is active"
else
    echo "Hotspot is down"
fi
```

#### Using a custom config file

```bash
# Use different config for different scenarios
sudo wlanspawn -c ~/work-hotspot.toml up
sudo wlanspawn -c ~/home-hotspot.toml up
```

#### Debug mode

```bash
# Get verbose output for troubleshooting
sudo wlanspawn --debug up
sudo wlanspawn --debug status
```

---

### Global Flags

```
-V, --version       Show version and exit
-c, --config PATH   Use custom config file (default: ~/.config/wlanspawn/config.toml)
--debug             Enable debug/verbose output
-h, --help          Show help message
```

---

## Configuration

Config is stored at:
- **Linux/macOS**: `~/.config/wlanspawn/config.toml`
- **Windows**: `%APPDATA%\wlanspawn\config.toml`

### Configuration File Format

```toml
# wlanspawn configuration
# Edit this file or run `wlanspawn init` to reconfigure

[hotspot]
ssid     = "MyHotspot"       # Network name (visible to clients)
password = "supersecret"     # WPA2 password (minimum 8 characters)
band     = "2.4GHz"          # "2.4GHz" or "5GHz"
channel  = 6                 # 2.4GHz: 1-11 (US), 1-13 (EU)
                             # 5GHz: 36, 40, 44, 48, 149, 153, 157, 161
hidden   = false             # true = hidden SSID (clients must enter name manually)

[interfaces]
internet = "wlan0"           # Interface with internet connection
                             # Examples: wlan0, eth0, enp3s0, wlp2s0
ap       = "wlan1"           # Interface that will broadcast the AP
                             # Must support AP mode (check with `iw list`)

[network]
gateway          = "192.168.73.1"      # IP address of this machine on AP network
subnet           = "192.168.73.0/24"   # Subnet for AP network
dhcp_range_start = "192.168.73.10"     # First IP to assign to clients
dhcp_range_end   = "192.168.73.100"    # Last IP to assign to clients
dns              = "8.8.8.8,1.1.1.1"   # DNS servers (comma-separated)

[backend]
type = "auto"    # auto | networkmanager | hostapd | windows
                 # auto = wlanspawn picks the best available backend

[logging]
level = "INFO"   # DEBUG | INFO | WARNING | ERROR
file  = "~/.local/share/wlanspawn/wlanspawn.log"
```

### Configuration Examples

#### Example 1: Ethernet to Wi-Fi bridge

Share your wired connection via Wi-Fi:

```toml
[hotspot]
ssid     = "Office-Guest"
password = "welcome2024"
band     = "2.4GHz"
channel  = 11

[interfaces]
internet = "eth0"     # Wired ethernet
ap       = "wlan0"    # Wi-Fi broadcasts AP
```

#### Example 2: Wi-Fi repeater/extender

Extend an existing Wi-Fi network (requires 2 Wi-Fi adapters):

```toml
[hotspot]
ssid     = "Home-Extended"
password = "sameasmain"
band     = "5GHz"      # Use 5GHz to avoid interference
channel  = 36

[interfaces]
internet = "wlan0"    # Connects to existing Wi-Fi
ap       = "wlan1"    # Broadcasts extended network
```

#### Example 3: Hidden network with custom subnet

```toml
[hotspot]
ssid     = "SecureAP"
password = "VeryStrong!Password123"
band     = "5GHz"
channel  = 149
hidden   = true       # Clients must manually enter SSID

[network]
gateway          = "10.0.50.1"
subnet           = "10.0.50.0/24"
dhcp_range_start = "10.0.50.100"
dhcp_range_end   = "10.0.50.200"
dns              = "1.1.1.1,8.8.8.8"  # Cloudflare + Google DNS
```

#### Example 4: Force specific backend

```toml
[backend]
type = "hostapd"    # Force hostapd backend instead of NetworkManager

[hotspot]
ssid     = "Server-AP"
password = "serverpass"
band     = "2.4GHz"
channel  = 6

[interfaces]
internet = "eth0"
ap       = "wlan0"
```

---

## Frequently Asked Questions (FAQ)

### General

**Q: Do I need two Wi-Fi adapters?**  
A: Usually yes. You need one interface to connect to the internet, and another to broadcast the hotspot. Exception: if you have ethernet (`eth0`), you only need one Wi-Fi adapter for the AP.

**Q: Can I use the same Wi-Fi adapter for both internet and AP?**  
A: No. Most Wi-Fi drivers don't support being a client and AP simultaneously on the same adapter.

**Q: Does wlanspawn work on Raspberry Pi?**  
A: Yes! Raspberry Pi is a great use case. The built-in Wi-Fi supports AP mode on most models (Pi 3, 4, Zero W).

**Q: Why do I need root/sudo?**  
A: Configuring network interfaces, IP forwarding, and NAT requires root privileges. Only `wlanspawn doctor` and `wlanspawn config` commands work without root.

### Performance

**Q: What's the maximum number of clients?**  
A: Depends on your hardware. Typical consumer Wi-Fi adapters handle 10-20 clients. NetworkManager default is ~50. Adjust `dhcp_range_start/end` for more.

**Q: Can I limit bandwidth per client?**  
A: Not yet. Planned for v0.3.0.

**Q: 2.4GHz or 5GHz — which should I use?**  
A:
- **2.4GHz**: Better range, more compatibility, more interference
- **5GHz**: Faster speeds, less congestion, shorter range
- Default: 2.4GHz (better compatibility)

### Compatibility

**Q: Does my Wi-Fi adapter support AP mode?**  
A: Check with:
```bash
iw list | grep -A 10 "Supported interface modes"
```
Look for `* AP` in the output. If missing, your adapter doesn't support it.

**Q: Which Wi-Fi adapters are recommended?**  
A:
- Most Intel Wi-Fi cards (iwlwifi driver)
- Realtek RTL8812AU/RTL8814AU USB adapters
- Atheros ath9k/ath10k chipsets
- Raspberry Pi built-in Wi-Fi

**Q: What about USB Wi-Fi dongles?**  
A: Many work great! Look for adapters with "AP mode support" in specs. Avoid very cheap no-name dongles.

### Security

**Q: Is the hotspot secure?**  
A: Yes. wlanspawn enforces WPA2-PSK encryption. Open (no-password) hotspots are not supported by design.

**Q: Where is my password stored?**  
A: In `~/.config/wlanspawn/config.toml` as plaintext. Protect it:
```bash
chmod 600 ~/.config/wlanspawn/config.toml
```

**Q: Can I block specific devices?**  
A: Not yet. MAC filtering planned for v0.3.0.

### Troubleshooting

**Q: "hostapd failed to start"**  
A: Common causes:
1. Interface is managed by NetworkManager → disable it: `sudo nmcli device set wlan1 managed no`
2. Wrong channel → try 1, 6, or 11
3. Driver issue → check `dmesg | tail`

**Q: Clients can connect but have no internet**  
A:
1. Check IP forwarding: `sysctl net.ipv4.ip_forward` (should be 1)
2. Check NAT: `sudo iptables -t nat -L -n -v | grep MASQUERADE`
3. Verify internet interface is up: `ip addr show wlan0`

**Q: Can I use wlanspawn with VPN?**  
A: Yes! Set `interfaces.internet` to your VPN interface (usually `tun0`, `wg0`, etc.).

**Q: Does it work with mobile data (4G/5G USB modem)?**  
A: Yes! Set `interfaces.internet` to your modem's interface (usually `ppp0`, `wwan0`, or similar).

---

## Architecture

```
wlanspawn/
├── cli.py              ← Click commands & Rich output
├── config.py           ← TOML config load/save, init wizard
├── detector.py         ← OS/interface/backend auto-detection
├── doctor.py           ← Dependency health checks
├── logger.py           ← Rich logging setup
├── backends/
│   ├── base.py         ← Abstract HotspotBackend interface
│   ├── networkmanager.py ← nmcli backend (Linux, recommended)
│   ├── hostapd.py      ← hostapd + dnsmasq backend (Linux, fallback)
│   └── windows.py      ← netsh hosted network (Windows)
└── utils/
    ├── network.py      ← Interface listing, client parsing, ARP
    └── system.py       ← OS detection, subprocess, privilege checks
```

### Backend selection logic

```
wlanspawn up
    │
    ├─ config.backend.type = "networkmanager" → use NetworkManagerBackend
    ├─ config.backend.type = "hostapd"        → use HostapdBackend
    ├─ config.backend.type = "windows"        → use WindowsBackend
    └─ config.backend.type = "auto"
           │
           ├─ Linux + nmcli available + NetworkManager active → NetworkManagerBackend
           ├─ Linux + hostapd + dnsmasq available             → HostapdBackend
           └─ Windows                                          → WindowsBackend
```

---

## Roadmap

### v0.1.0 — MVP *(current)*
- [x] `init`, `up`, `down`, `status`, `clients`, `doctor` commands
- [x] NetworkManager backend (nmcli, `ipv4.method shared`)
- [x] hostapd + dnsmasq backend
- [x] Windows netsh backend (best-effort)
- [x] Auto OS/backend detection
- [x] TOML config with init wizard
- [x] WPA2-PSK, band selection, hidden SSID

### v0.2.0 — Quality
- [ ] Systemd service unit (`wlanspawn enable` / `wlanspawn disable`)
- [ ] `wlanspawn logs` command (tail log file)
- [ ] macOS support (Internet Sharing via `networksetup`)
- [ ] 5 GHz support on Windows (via Mobile Hotspot API)
- [ ] Shell completions (`wlanspawn --install-completion`)

### v0.3.0 — Advanced Features
- [ ] Client allowlist/blocklist (MAC filtering)
- [ ] Bandwidth throttling per client
- [ ] QR code generation (`wlanspawn qr`) for easy phone connect
- [ ] Traffic statistics (`wlanspawn stats`)
- [ ] Multiple saved profiles (`wlanspawn profile use <name>`)
- [ ] Captive portal support

### v1.0.0 — Stable
- [ ] Full test coverage (>80%)
- [ ] Distro packages (Fedora COPR, Ubuntu PPA, AUR)
- [ ] Plugin/hook system for custom integrations
- [ ] TUI dashboard (`wlanspawn tui`)

---

## Development

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/wlanspawn.git
cd wlanspawn

# Create virtual environment (Python 3.9+)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
wlanspawn --version
pytest --version
ruff --version
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=wlanspawn --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=wlanspawn --cov-report=html
# Open htmlcov/index.html in browser

# Run specific test file
pytest tests/test_config.py

# Run specific test
pytest tests/test_config.py::TestDefaults::test_default_hotspot

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Code Quality

```bash
# Format code with black
black wlanspawn tests

# Lint with ruff (auto-fix)
ruff check wlanspawn tests --fix

# Lint without auto-fix
ruff check wlanspawn tests

# Type checking with mypy
mypy wlanspawn

# Run all checks
black wlanspawn tests && ruff check wlanspawn tests && mypy wlanspawn
```

### Project Makefile

```bash
make help       # Show all available targets
make test       # Run tests with coverage
make lint       # Run black + ruff + mypy
make format     # Format code with black
make dev        # Install in editable mode with dev deps
make clean      # Remove build artifacts, cache, etc.
make dist       # Build source and wheel distributions
make install    # Install from source
```

### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make changes and test**
   ```bash
   # Make code changes
   vim wlanspawn/cli.py
   
   # Run tests
   pytest
   
   # Format and lint
   black wlanspawn tests
   ruff check wlanspawn tests --fix
   ```

3. **Test manually**
   ```bash
   # Your changes are immediately available (editable install)
   sudo wlanspawn up --debug
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: add new feature X"
   git push origin feat/my-feature
   ```

### Testing on Different Platforms

#### Docker (recommended)

```bash
# Test on Fedora
docker run -it --rm \
  --privileged \
  --net=host \
  -v $(pwd):/wlanspawn \
  fedora:latest \
  bash -c "cd /wlanspawn && dnf install -y python3 python3-pip iw && pip3 install -e '.[dev]' && pytest"

# Test on Ubuntu
docker run -it --rm \
  --privileged \
  --net=host \
  -v $(pwd):/wlanspawn \
  ubuntu:latest \
  bash -c "cd /wlanspawn && apt update && apt install -y python3 python3-pip iw && pip3 install -e '.[dev]' && pytest"
```

#### Virtual Machines

Use VirtualBox/QEMU with USB Wi-Fi passthrough to test real hotspot functionality.

### Project Structure

```
wlanspawn/
├── wlanspawn/              # Main package
│   ├── __init__.py         # Version, metadata
│   ├── cli.py              # Click CLI commands
│   ├── config.py           # TOML config handling
│   ├── detector.py         # OS/interface detection
│   ├── doctor.py           # Dependency checks
│   ├── logger.py           # Logging setup
│   ├── backends/           # Backend implementations
│   │   ├── base.py         # Abstract base class
│   │   ├── networkmanager.py
│   │   ├── hostapd.py
│   │   └── windows.py
│   └── utils/              # Utilities
│       ├── network.py      # Interface listing, client parsing
│       └── system.py       # OS detection, subprocess helpers
├── tests/                  # Test suite
│   ├── conftest.py         # Pytest fixtures
│   ├── test_backends.py
│   ├── test_config.py
│   └── test_detector.py
├── docs/                   # Documentation
├── examples/               # Example configs
├── scripts/                # Install/uninstall scripts
├── pyproject.toml          # Project metadata, dependencies, tool config
├── README.md               # This file
├── CHANGELOG.md            # Version history
├── CONTRIBUTING.md         # Contribution guidelines
├── LICENSE                 # MIT License
└── Makefile                # Development automation
```

### Adding a New Backend

1. **Create backend class** in `wlanspawn/backends/yourbackend.py`:
   ```python
   from wlanspawn.backends.base import HotspotBackend
   
   class YourBackend(HotspotBackend):
       name = "yourbackend"
       
       def is_available(self) -> bool:
           # Check if backend can run
           
       def is_running(self) -> bool:
           # Check if hotspot is active
           
       def up(self) -> None:
           # Start hotspot
           
       def down(self) -> None:
           # Stop hotspot
           
       def status(self) -> dict:
           # Return status info
           
       def clients(self) -> list[Client]:
           # Return connected clients
   ```

2. **Register backend** in `wlanspawn/backends/__init__.py`

3. **Add tests** in `tests/test_backends.py`

4. **Update documentation** in README.md

### Debug Tips

```bash
# Enable debug logging
sudo wlanspawn --debug up

# Check Python imports
python3 -c "from wlanspawn.cli import main; main()"

# Run single test with print output
pytest -s tests/test_config.py::TestDefaults::test_default_hotspot

# Interactive debugging with pdb
pytest --pdb tests/test_config.py

# Check test coverage for specific module
pytest --cov=wlanspawn.config tests/test_config.py
```

---

## Contributing

Contributions are welcome and appreciated! Please read the [contribution guide](CONTRIBUTING.md).

### Quick contribution guide

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feat/my-feature`)
3. **Write** code and tests
4. **Ensure** `make lint && make test` pass
5. **Commit** with a descriptive message
6. **Open** a pull request

### Areas where help is especially welcome

- macOS backend (Internet Sharing via `networksetup` / `pfctl`)
- Windows Mobile Hotspot API for 5 GHz
- Distro packaging (SPEC files, debian/ directory)
- Shell completions (bash, zsh, fish)
- Documentation / examples

---

## Performance Tips

### Optimize for Speed

1. **Use 5GHz when possible**
   - Less interference than 2.4GHz
   - Supports higher data rates
   - Choose wide channels (40MHz or 80MHz)
   ```toml
   [hotspot]
   band = "5GHz"
   channel = 36  # or 149
   ```

2. **Choose the right channel**
   - 2.4GHz: Use 1, 6, or 11 (non-overlapping)
   - 5GHz: Use DFS channels if your adapter supports them
   - Check channel congestion:
   ```bash
   sudo iw dev wlan0 scan | grep -E "^BSS|freq:|signal:|SSID:"
   ```

3. **Enable hardware acceleration**
   - Some adapters support offloading (TSO, GSO)
   - Check with: `ethtool -k wlan1`

4. **Limit DHCP range**
   - Smaller DHCP pool = faster lookups
   ```toml
   [network]
   dhcp_range_start = "192.168.73.10"
   dhcp_range_end   = "192.168.73.30"  # Max 20 clients
   ```

### Optimize for Range

1. **Use 2.4GHz**
   - Better penetration through walls
   - Longer range than 5GHz
   ```toml
   [hotspot]
   band = "2.4GHz"
   channel = 6
   ```

2. **Position your AP**
   - Central location in the coverage area
   - Elevated position (table, shelf)
   - Away from metal objects and microwaves

3. **External antenna (if supported)**
   - Many USB adapters have detachable antennas
   - Higher dBi = longer range

### Optimize for Stability

1. **Use NetworkManager backend (Linux)**
   - Most stable and well-tested
   - Better power management
   ```toml
   [backend]
   type = "networkmanager"
   ```

2. **Set a static channel**
   - Auto-selection can cause brief disconnects
   - Stick to 1, 6, or 11 for 2.4GHz

3. **Monitor interference**
   ```bash
   sudo iw dev wlan1 survey dump
   ```

4. **Keep adapter cool**
   - Some USB adapters throttle when hot
   - Ensure good ventilation

---

## Troubleshooting

### Common Issues

#### **"Error: Root / administrator privileges required"**

Most wlanspawn commands need root to configure network interfaces:

```bash
sudo wlanspawn up
sudo wlanspawn down
sudo wlanspawn status
sudo wlanspawn clients
```

The `doctor` command doesn't need root:
```bash
wlanspawn doctor  # No sudo needed
```

#### **"sudo: wlanspawn: command not found"**

This happens when wlanspawn is installed in a virtual environment. When you run `sudo`, it uses root's PATH which doesn't include your venv.

**Solutions:**

**Option 1: Use the Python module directly (recommended for development)**
```bash
source .venv/bin/activate
sudo python3 -m wlanspawn.cli up
```

**Option 2: Use the wrapper script**
```bash
# Use the included development wrapper (works with sudo)
sudo ./wlanspawn-dev up
sudo ./wlanspawn-dev status
sudo ./wlanspawn-dev down
```

**Option 3: Use full path**
```bash
source .venv/bin/activate
sudo $(which wlanspawn) up
```

**Option 4: Install system-wide (for production)**
```bash
deactivate  # Exit venv first
sudo pip install -e .
# Now sudo wlanspawn up works
```

**Option 5: Preserve environment**
```bash
source .venv/bin/activate
sudo -E env PATH=$PATH wlanspawn up
```

#### **"No AP-capable wireless interfaces found"**

Your Wi-Fi adapter might not support AP mode. Check with:

```bash
iw list | grep -A 10 "Supported interface modes"
```

Look for `* AP` in the output. If missing, your adapter doesn't support hotspot mode.

**Solution**: Use a different Wi-Fi adapter or USB dongle that supports AP mode.

#### **"NetworkManager backend not available"**

If NetworkManager isn't running:

```bash
# Check status
systemctl status NetworkManager

# Start if needed
sudo systemctl start NetworkManager

# Enable on boot
sudo systemctl enable NetworkManager
```

Or use the hostapd backend:

```bash
sudo wlanspawn init  # Select "hostapd" when prompted for backend
```

#### **"hostapd failed to start"**

Common causes:
1. **Interface in use**: Stop NetworkManager on the AP interface:
   ```bash
   sudo nmcli device set wlan1 managed no
   ```

2. **Wrong driver**: Some drivers need special configuration. Check `dmesg` for errors:
   ```bash
   sudo dmesg | tail -50
   ```

3. **Channel not supported**: Try a different channel (1, 6, or 11 for 2.4GHz)

#### **"Cannot connect to hotspot from phone/laptop"**

1. **Check password**: Ensure it's at least 8 characters
   ```bash
   wlanspawn config show | grep password
   ```

2. **Check SSID visibility**: If hidden=true, you'll need to manually enter the SSID
   ```bash
   wlanspawn config show | grep hidden
   ```

3. **Verify hotspot is running**:
   ```bash
   sudo wlanspawn status
   ```

4. **Check firewall**: Ensure DHCP (port 67) and DNS (port 53) aren't blocked
   ```bash
   sudo firewall-cmd --list-all  # Fedora/RHEL
   sudo ufw status               # Debian/Ubuntu
   ```

#### **Connected but no internet**

1. **Verify internet interface is up**:
   ```bash
   ip addr show wlan0  # Replace wlan0 with your internet interface
   ```

2. **Check IP forwarding**:
   ```bash
   sysctl net.ipv4.ip_forward  # Should show 1
   ```

3. **Verify NAT rules**:
   ```bash
   sudo iptables -t nat -L -n -v | grep MASQUERADE
   ```

4. **Test DNS**:
   ```bash
   # From connected client
   nslookup google.com 192.168.73.1
   ```

#### **"Module 'tomllib' not found" (Python < 3.11)**

wlanspawn auto-installs `tomli` for Python < 3.11. If you see this error:

```bash
pip install tomli
```

### Getting Help

If you're still stuck:

1. **Run diagnostics**:
   ```bash
   wlanspawn doctor --verbose
   ```

2. **Check logs** (if logging enabled):
   ```bash
   tail -f ~/.local/share/wlanspawn/wlanspawn.log
   ```

3. **Report an issue**: [GitHub Issues](https://github.com/yourusername/wlanspawn/issues)
   - Include output of `wlanspawn doctor`
   - Include relevant error messages
   - Include OS/distro version (`cat /etc/os-release`)

---

## Security Considerations

- wlanspawn requires **root/administrator** privileges to configure network interfaces
- The config file (`~/.config/wlanspawn/config.toml`) stores your Wi-Fi **password in plaintext**
  — ensure appropriate file permissions (`chmod 600`)
- wlanspawn does **not** send any data to external servers
- WPA2-PSK is enforced; open (no-password) hotspots are not supported by design
- For production/shared use, consider MAC allowlisting (v0.3.0 roadmap)

To protect your config file:
```bash
chmod 600 ~/.config/wlanspawn/config.toml
```

---

## License

MIT License — see [LICENSE](LICENSE) for full text.

---

## Acknowledgments

Inspired by [linux-wifi-hotspot](https://github.com/lakinduakash/linux-wifi-hotspot),
[create_ap](https://github.com/oblique/create_ap), and the endless frustration of
having to re-type `nmcli` incantations every time.

---

<div align="center">
Made with ☕ and way too much time reading nl80211 docs.
</div>
