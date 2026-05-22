"""hostapd + dnsmasq backend.

Used on systems without NetworkManager (e.g. servers, minimal installs, Arch).
Manually handles:
  - hostapd config generation and process management
  - dnsmasq config generation for DHCP
  - iptables MASQUERADE rule for NAT
  - sysctl ip_forward toggle
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

from wlanspawn.backends.base import HotspotBackend
from wlanspawn.logger import get_logger
from wlanspawn.utils.network import Client
from wlanspawn.utils.system import cmd_exists, run, run_output

logger = get_logger(__name__)

HOSTAPD_CONF = Path("/tmp/wlanspawn-hostapd.conf")
DNSMASQ_CONF = Path("/tmp/wlanspawn-dnsmasq.conf")
HOSTAPD_PID = Path("/tmp/wlanspawn-hostapd.pid")
DNSMASQ_PID = Path("/tmp/wlanspawn-dnsmasq.pid")
DNSMASQ_LEASES = Path("/tmp/wlanspawn-dnsmasq.leases")


class HostapdBackend(HotspotBackend):
    """Hotspot via hostapd + dnsmasq + iptables."""

    name = "hostapd"

    def is_available(self) -> bool:
        return cmd_exists("hostapd") and cmd_exists("dnsmasq")

    def is_running(self) -> bool:
        if HOSTAPD_PID.exists():
            pid = _read_pid(HOSTAPD_PID)
            if pid and _pid_alive(pid):
                return True
        return False

    # ------------------------------------------------------------------ up --

    def up(self) -> None:
        cfg = self.config
        ap_iface = cfg.interfaces.ap
        internet_iface = cfg.interfaces.internet
        gw = cfg.network.gateway
        ssid = cfg.hotspot.ssid
        password = cfg.hotspot.password
        channel = cfg.hotspot.channel
        band = cfg.hotspot.band

        logger.info("Starting hotspot '%s' on %s via hostapd", ssid, ap_iface)

        if self.is_running():
            logger.warning("Hotspot already running. Run `wlanspawn down` first.")
            return

        # 1. Write hostapd config
        _write_hostapd_conf(HOSTAPD_CONF, ap_iface, ssid, password, channel, band, cfg.hotspot.hidden)

        # 2. Write dnsmasq config
        _write_dnsmasq_conf(DNSMASQ_CONF, ap_iface, gw, cfg.network.dhcp_range_start,
                            cfg.network.dhcp_range_end, DNSMASQ_LEASES, cfg.network.dns)

        # 3. Assign IP to AP interface
        run(["ip", "addr", "flush", "dev", ap_iface], check=False)
        run(["ip", "addr", "add", f"{gw}/24", "dev", ap_iface])
        run(["ip", "link", "set", ap_iface, "up"])

        # 4. Enable IP forwarding
        _set_ip_forward(True)

        # 5. Add iptables MASQUERADE
        _add_nat(internet_iface)

        # 6. Start hostapd
        proc = subprocess.Popen(
            ["hostapd", str(HOSTAPD_CONF), "-B", f"-P{HOSTAPD_PID}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        time.sleep(2)
        if proc.poll() is not None:
            err = proc.stderr.read().decode() if proc.stderr else ""
            raise RuntimeError(f"hostapd failed to start: {err}")

        # 7. Start dnsmasq
        run([
            "dnsmasq",
            f"--conf-file={DNSMASQ_CONF}",
            f"--pid-file={DNSMASQ_PID}",
        ])

        logger.info("Hotspot is up!")

    # --------------------------------------------------------------- down --

    def down(self) -> None:
        logger.info("Stopping hotspot …")
        cfg = self.config

        _kill_pid(HOSTAPD_PID, "hostapd")
        _kill_pid(DNSMASQ_PID, "dnsmasq")
        _remove_nat(cfg.interfaces.internet)
        _set_ip_forward(False)

        # Clean up config files
        for f in (HOSTAPD_CONF, DNSMASQ_CONF, HOSTAPD_PID, DNSMASQ_PID, DNSMASQ_LEASES):
            try:
                f.unlink(missing_ok=True)
            except OSError:
                pass

        logger.info("Hotspot stopped.")

    # ------------------------------------------------------------- status --

    def status(self) -> dict:
        cfg = self.config
        return {
            "backend": self.name,
            "running": self.is_running(),
            "ssid": cfg.hotspot.ssid,
            "ap_iface": cfg.interfaces.ap,
            "internet_iface": cfg.interfaces.internet,
            "gateway": cfg.network.gateway,
            "band": cfg.hotspot.band,
            "channel": cfg.hotspot.channel,
            "clients": len(self.clients()) if self.is_running() else 0,
        }

    # ------------------------------------------------------------ clients --

    def clients(self) -> list[Client]:
        from wlanspawn.utils.network import (
            _enrich_from_leases,
            _get_clients_from_arp,
            _parse_hostapd_sta,
        )
        clients: list[Client] = []

        if cmd_exists("hostapd_cli"):
            out = run_output(["hostapd_cli", "-i", self.config.interfaces.ap, "all_sta"])
            clients = _parse_hostapd_sta(out)

        if not clients:
            clients = _get_clients_from_arp(self.config.interfaces.ap)

        _enrich_from_leases(clients)
        return clients


# ---------------------------------------------------------------------------
# Config file generators
# ---------------------------------------------------------------------------

def _write_hostapd_conf(
    path: Path,
    iface: str,
    ssid: str,
    password: str,
    channel: int,
    band: str,
    hidden: bool,
) -> None:
    hw_mode = "g" if "2.4" in band else "a"
    content = f"""# wlanspawn — generated hostapd configuration
interface={iface}
driver=nl80211
ssid={ssid}
hw_mode={hw_mode}
channel={channel}
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid={'1' if hidden else '0'}
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
ieee80211n=1
wmm_enabled=1
"""
    path.write_text(content)
    logger.debug("hostapd config written to %s", path)


def _write_dnsmasq_conf(
    path: Path,
    iface: str,
    gateway: str,
    dhcp_start: str,
    dhcp_end: str,
    lease_file: Path,
    dns_servers: str,
) -> None:
    dns_list = "\n".join(f"server={d.strip()}" for d in dns_servers.split(","))
    content = f"""# wlanspawn — generated dnsmasq configuration
interface={iface}
bind-interfaces
dhcp-range={dhcp_start},{dhcp_end},255.255.255.0,12h
dhcp-option=3,{gateway}
dhcp-leasefile={lease_file}
no-resolv
{dns_list}
log-dhcp
"""
    path.write_text(content)
    logger.debug("dnsmasq config written to %s", path)


# ---------------------------------------------------------------------------
# iptables / networking helpers
# ---------------------------------------------------------------------------

def _set_ip_forward(enable: bool) -> None:
    val = "1" if enable else "0"
    try:
        with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
            f.write(val)
        logger.debug("ip_forward set to %s", val)
    except OSError as e:
        logger.warning("Could not set ip_forward: %s", e)


def _add_nat(internet_iface: str) -> None:
    """Add iptables MASQUERADE rule for NAT."""
    try:
        run(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", internet_iface, "-j", "MASQUERADE"])
        run(["iptables", "-A", "FORWARD", "-i", internet_iface, "-j", "ACCEPT"])
        run(["iptables", "-A", "FORWARD", "-o", internet_iface, "-j", "ACCEPT"])
    except Exception as e:
        logger.warning("iptables NAT setup failed: %s", e)


def _remove_nat(internet_iface: str) -> None:
    """Remove iptables MASQUERADE rule."""
    try:
        run(["iptables", "-t", "nat", "-D", "POSTROUTING", "-o", internet_iface, "-j", "MASQUERADE"], check=False)
        run(["iptables", "-D", "FORWARD", "-i", internet_iface, "-j", "ACCEPT"], check=False)
        run(["iptables", "-D", "FORWARD", "-o", internet_iface, "-j", "ACCEPT"], check=False)
    except Exception:
        pass


def _read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # Exists but different user


def _kill_pid(pid_file: Path, name: str) -> None:
    pid = _read_pid(pid_file)
    if pid and _pid_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            logger.debug("Sent SIGTERM to %s (pid %d)", name, pid)
        except ProcessLookupError:
            pass
