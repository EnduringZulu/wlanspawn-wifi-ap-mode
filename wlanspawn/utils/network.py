"""Network utilities: interface listing, AP capability, ARP table, client info."""

from __future__ import annotations

import re
from dataclasses import dataclass

from wlanspawn.logger import get_logger
from wlanspawn.utils.system import OS, cmd_exists, detect_os, run_output

logger = get_logger(__name__)


@dataclass
class Interface:
    name: str
    mac: str = ""
    ipv4: str = ""
    state: str = "unknown"
    is_wireless: bool = False
    supports_ap: bool = False
    driver: str = ""


@dataclass
class Client:
    mac: str
    ip: str = ""
    hostname: str = ""
    signal_dbm: int | None = None
    tx_bytes: int = 0
    rx_bytes: int = 0


def list_interfaces() -> list[Interface]:
    """Return a list of network interfaces with metadata."""
    os_type = detect_os()
    if os_type == OS.LINUX:
        return _list_interfaces_linux()
    if os_type == OS.WINDOWS:
        return _list_interfaces_windows()
    return []


def _list_interfaces_linux() -> list[Interface]:
    interfaces: list[Interface] = []
    try:
        import os as _os
        net_path = "/sys/class/net"
        for iface in sorted(_os.listdir(net_path)):
            iface_path = f"{net_path}/{iface}"
            mac = _read_file(f"{iface_path}/address") or ""
            operstate = _read_file(f"{iface_path}/operstate") or "unknown"

            # Check if wireless
            is_wireless = _os.path.isdir(f"{iface_path}/wireless") or _os.path.islink(
                f"{iface_path}/phy80211"
            )

            # Get IPv4
            ipv4 = _get_ipv4(iface)

            # Get driver
            driver = ""
            driver_link = f"{iface_path}/device/driver"
            if _os.path.islink(driver_link):
                driver = _os.path.basename(_os.readlink(driver_link))

            iface_obj = Interface(
                name=iface,
                mac=mac,
                ipv4=ipv4,
                state=operstate,
                is_wireless=is_wireless,
                driver=driver,
            )
            if is_wireless:
                iface_obj.supports_ap = _check_ap_support_linux(iface)

            interfaces.append(iface_obj)
    except Exception as e:
        logger.debug("Interface listing error: %s", e)
    return interfaces


def _list_interfaces_windows() -> list[Interface]:
    """Best-effort interface listing on Windows."""
    interfaces = []
    output = run_output(["netsh", "wlan", "show", "interfaces"])
    # Parse netsh output blocks
    name = ""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("Name") and ":" in line:
            name = line.split(":", 1)[1].strip()
        if name:
            interfaces.append(Interface(name=name, is_wireless=True))
            name = ""
    return interfaces


def _get_ipv4(iface: str) -> str:
    """Get IPv4 address for a Linux interface via ip command."""
    output = run_output(["ip", "-4", "addr", "show", iface])
    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", output)
    return m.group(1) if m else ""


def _read_file(path: str) -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def _check_ap_support_linux(iface: str) -> bool:
    """Check if an interface supports AP mode via iw."""
    if not cmd_exists("iw"):
        return True  # Assume capable if iw not available

    output = run_output(["iw", iface, "info"])
    if "AP" in output:
        return True

    # Try checking phy modes
    output2 = run_output(["iw", "list"])
    # Look for "AP" in Supported interface modes block
    in_modes_block = False
    for line in output2.splitlines():
        if "Supported interface modes" in line:
            in_modes_block = True
        elif in_modes_block:
            if line.strip().startswith("*"):
                if "AP" in line:
                    return True
            elif not line.startswith(" ") and not line.startswith("\t"):
                in_modes_block = False
    return False


def get_wireless_interfaces() -> list[Interface]:
    """Return only wireless interfaces."""
    return [i for i in list_interfaces() if i.is_wireless]


def get_ap_capable_interfaces() -> list[Interface]:
    """Return wireless interfaces that support AP mode."""
    return [i for i in get_wireless_interfaces() if i.supports_ap]


def get_clients_networkmanager(ap_iface: str) -> list[Client]:
    """Get connected clients via hostapd_cli + ARP."""
    clients: list[Client] = []

    # Try hostapd_cli
    if cmd_exists("hostapd_cli"):
        output = run_output(["hostapd_cli", "-i", ap_iface, "all_sta"])
        clients = _parse_hostapd_sta(output)

    # Fallback: read ARP table for the subnet
    if not clients:
        clients = _get_clients_from_arp(ap_iface)

    # Try to resolve IPs from dnsmasq leases
    _enrich_from_leases(clients)
    return clients


def _parse_hostapd_sta(output: str) -> list[Client]:
    clients = []
    current_mac = ""
    for line in output.splitlines():
        line = line.strip()
        mac_match = re.match(r"^([0-9a-f:]{17})$", line)
        if mac_match:
            current_mac = mac_match.group(1)
            clients.append(Client(mac=current_mac))
        elif current_mac and "=" in line:
            k, _, v = line.partition("=")
            c = clients[-1]
            if k == "signal":
                try:
                    c.signal_dbm = int(v)
                except ValueError:
                    pass
            elif k == "rx_bytes":
                try:
                    c.rx_bytes = int(v)
                except ValueError:
                    pass
            elif k == "tx_bytes":
                try:
                    c.tx_bytes = int(v)
                except ValueError:
                    pass
    return clients


def _get_clients_from_arp(iface: str) -> list[Client]:
    """Read /proc/net/arp and filter by iface."""
    clients = []
    try:
        with open("/proc/net/arp") as f:
            next(f)  # skip header
            for line in f:
                parts = line.split()
                if len(parts) >= 6 and parts[5] == iface:
                    ip = parts[0]
                    mac = parts[3]
                    if mac != "00:00:00:00:00:00":
                        clients.append(Client(mac=mac, ip=ip))
    except OSError:
        pass
    return clients


def _enrich_from_leases(clients: list[Client]) -> None:
    """Try to fill in IP/hostname from dnsmasq lease file."""
    lease_files = [
        "/var/lib/misc/dnsmasq.leases",
        "/var/lib/dnsmasq/dnsmasq.leases",
        "/tmp/dnsmasq.leases",
    ]
    leases: dict[str, tuple[str, str]] = {}
    for lf in lease_files:
        try:
            with open(lf) as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4:
                        mac, ip, host = parts[1], parts[2], parts[3]
                        leases[mac.lower()] = (ip, host)
            break
        except OSError:
            continue

    for c in clients:
        info = leases.get(c.mac.lower())
        if info:
            if not c.ip:
                c.ip = info[0]
            if not c.hostname:
                c.hostname = info[1] if info[1] != "*" else ""


def get_clients_windows() -> list[Client]:
    """Get connected clients via netsh on Windows."""
    output = run_output(["netsh", "wlan", "show", "hostednetwork"])
    clients = []
    for line in output.splitlines():
        m = re.search(r"([0-9a-f:]{17})", line.lower())
        if m:
            clients.append(Client(mac=m.group(1)))
    return clients


def interface_exists(name: str) -> bool:
    return any(i.name == name for i in list_interfaces())


def get_gateway_ip(subnet: str = "192.168.73") -> str:
    return f"{subnet}.1"
