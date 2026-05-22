# wlanspawn — Architecture Document

## Design Goals

1. **No magic** — every action wlanspawn takes maps to a documented system call or tool invocation
2. **Modular backends** — adding a new platform requires only one new file
3. **Fail loudly with fixes** — every error includes a human-readable suggestion
4. **Minimal footprint** — no persistent daemons, no kernel modules, no C extensions

---

## Component Map

```
┌─────────────────────────────────────────────┐
│                  CLI (cli.py)               │
│  init · up · down · status · clients ·      │
│  doctor · config show/edit/path             │
└─────────────┬───────────────────────────────┘
              │ calls
   ┌──────────▼───────────┐
   │  backends/__init__.py │  get_backend() factory
   └──────────┬────────────┘
              │ selects
   ┌──────────▼────────────────────────────────┐
   │          HotspotBackend (abstract)         │
   │  is_available  is_running  up  down        │
   │  status  clients                           │
   └──────────┬────────────────────────────────┘
              │ concrete implementations
   ┌──────────▼──────────┐ ┌─────────────┐ ┌──────────┐
   │ NetworkManagerBackend│ │HostapdBackend│ │WindowsBackend│
   │  nmcli + NM shared  │ │hostapd+dnsmasq│ │netsh + ICS  │
   └─────────────────────┘ └─────────────┘ └──────────┘
              │
   ┌──────────▼──────────┐   ┌─────────────┐
   │   utils/network.py  │   │utils/system.py│
   │  interface listing  │   │ OS detection  │
   │  ARP / client parse │   │ subprocess    │
   │  hostapd_cli        │   │ root check    │
   └─────────────────────┘   └─────────────┘
```

---

## Backend Selection Flow

```
wlanspawn up
     │
     ├─ config.backend.type = "networkmanager" ──► NetworkManagerBackend
     ├─ config.backend.type = "hostapd"        ──► HostapdBackend
     ├─ config.backend.type = "windows"        ──► WindowsBackend
     └─ config.backend.type = "auto"
              │
              ├─ OS=Linux AND nmcli available AND NM active ──► NetworkManagerBackend
              ├─ OS=Linux AND hostapd+dnsmasq available     ──► HostapdBackend
              └─ OS=Windows                                 ──► WindowsBackend
```

---

## NetworkManager Backend — What Actually Happens

The `ipv4.method shared` option in NetworkManager is the linchpin. It automatically:

1. Calls `dnsmasq` (bundled with NM) to serve DHCP on the AP subnet
2. Writes iptables MASQUERADE rules via NetworkManager's firewall plugin
3. Enables `/proc/sys/net/ipv4/ip_forward`
4. Assigns the gateway IP to the AP interface

wlanspawn's role is to build and activate the connection profile via `nmcli`.

```
nmcli connection add type wifi ifname wlan1 con-name wlanspawn-hotspot ssid MyHotspot mode ap
nmcli connection modify wlanspawn-hotspot 802-11-wireless-security.key-mgmt wpa-psk ...
nmcli connection modify wlanspawn-hotspot ipv4.method shared ipv4.addresses 192.168.73.1/24
nmcli connection up wlanspawn-hotspot
```

Teardown is clean: `nmcli connection down` + `nmcli connection delete` restores all state.

---

## hostapd Backend — What Actually Happens

For systems without NetworkManager, wlanspawn manually orchestrates:

```
                ┌──────────────────────────┐
wlan0 (internet)│          Host            │ wlan1 (AP)
── dhcp client ─┤  ip_forward = 1         ├── hostapd (AP daemon)
                │  iptables MASQUERADE    ├── dnsmasq (DHCP server)
                │  wlan1 ip: 192.168.73.1 │
                └──────────────────────────┘
```

1. Generates `/tmp/wlanspawn-hostapd.conf` (SSID, channel, WPA2 config)
2. Generates `/tmp/wlanspawn-dnsmasq.conf` (DHCP range, DNS, gateway)
3. Assigns gateway IP to AP interface via `ip addr add`
4. Enables IP forwarding via `/proc/sys/net/ipv4/ip_forward`
5. Adds iptables MASQUERADE on the internet interface
6. Starts `hostapd` in background mode with a PID file
7. Starts `dnsmasq` with the generated config

`wlanspawn down` reverses all steps, removes temp files, kills processes.

---

## Config Format (TOML)

TOML was chosen over JSON/YAML/INI because:
- Human-readable and editable without a serializer
- Native Python 3.11+ support (`tomllib`)
- Clean section-based hierarchy maps to dataclasses
- Comments supported (unlike JSON)
- Less ambiguous than YAML

The config is deserialized into frozen dataclasses for type safety.

---

## Security Model

| Concern | Mitigation |
|---|---|
| Plaintext password in config | File permissions enforced (0600 recommended), documented |
| Root privilege escalation | `require_root()` guards all state-changing commands; checks are explicit, not ambient |
| Open APs | WPA2-PSK is hardcoded; no open hotspot mode by design |
| Arbitrary shell injection | All subprocess calls use list form (no shell=True) |
| DHCP server exposure | dnsmasq/NM DHCP binds only to AP interface |

---

## Future Scalability

### Plugin system (v0.4+)

```python
# Entry point in pyproject.toml:
[project.entry-points."wlanspawn.backends"]
mybackend = "my_package.backend:MyBackend"
```

### Profile system (v0.3+)

```toml
# ~/.config/wlanspawn/config.toml
[profiles.home]
ssid = "HomeNet"
password = "homepass"

[profiles.travel]
ssid = "TravelAP"
channel = 11
```

```
wlanspawn profile list
wlanspawn up --profile travel
```

### TUI dashboard (v1.0+)

`wlanspawn tui` — a Textual-based terminal dashboard showing live client graph, traffic sparklines, signal heatmap.

---

## Testing Strategy

| Layer | Approach |
|---|---|
| Unit | Pure Python logic (config, detection, parsing) |
| Integration | Mock `subprocess.run`; verify nmcli/iptables args |
| System | Real hardware CI on self-hosted runner (future) |
| Windows | GitHub Actions windows-latest smoke tests |

Avoid testing system state directly; test the commands wlanspawn would issue.
