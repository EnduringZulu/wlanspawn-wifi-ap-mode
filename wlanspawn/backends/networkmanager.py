"""NetworkManager (nmcli) backend.

Uses `nmcli connection add ... ipv4.method shared` which automatically:
  - Creates a dnsmasq-backed DHCP server for the AP subnet
  - Enables NAT / masquerading via NetworkManager's built-in firewall integration
  - Routes traffic from AP clients to the internet interface

This is the cleanest and most robust approach on modern Linux desktops.
"""

from __future__ import annotations

import time

from wlanspawn.backends.base import HotspotBackend
from wlanspawn.logger import get_logger
from wlanspawn.utils.network import Client, get_clients_networkmanager
from wlanspawn.utils.system import cmd_exists, run, run_output

logger = get_logger(__name__)

CONNECTION_NAME = "wlanspawn-hotspot"


class NetworkManagerBackend(HotspotBackend):
    """Hotspot via NetworkManager nmcli."""

    name = "networkmanager"

    def is_available(self) -> bool:
        if not cmd_exists("nmcli"):
            return False
        status = run_output(["systemctl", "is-active", "NetworkManager"])
        return status == "active"

    def is_running(self) -> bool:
        output = run_output(
            ["nmcli", "-t", "-f", "NAME,TYPE,STATE", "connection", "show", "--active"]
        )
        return CONNECTION_NAME in output

    # ------------------------------------------------------------------ up --

    def up(self) -> None:
        cfg = self.config
        iface = cfg.interfaces.ap
        ssid = cfg.hotspot.ssid
        password = cfg.hotspot.password
        band = "bg" if cfg.hotspot.band == "2.4GHz" else "a"
        channel = str(cfg.hotspot.channel)

        logger.info("Starting hotspot '%s' on %s via NetworkManager", ssid, iface)

        # Remove stale connection if present
        self._remove_connection()

        # --- Create the connection ---
        run([
            "nmcli", "connection", "add",
            "type", "wifi",
            "ifname", iface,
            "con-name", CONNECTION_NAME,
            "autoconnect", "no",
            "ssid", ssid,
            "mode", "ap",
        ])

        # --- Configure security (WPA2-AES for iOS compatibility) ---
        run([
            "nmcli", "connection", "modify", CONNECTION_NAME,
            "802-11-wireless-security.key-mgmt", "wpa-psk",
            "802-11-wireless-security.psk", password,
            "802-11-wireless-security.proto", "rsn",  # WPA2 only
            "802-11-wireless-security.pairwise", "ccmp",  # AES encryption
            "802-11-wireless-security.group", "ccmp",  # AES for group
        ])

        # --- Configure radio ---
        run([
            "nmcli", "connection", "modify", CONNECTION_NAME,
            "802-11-wireless.band", band,
            "802-11-wireless.channel", channel,
        ])

        # --- Hidden SSID ---
        if cfg.hotspot.hidden:
            run([
                "nmcli", "connection", "modify", CONNECTION_NAME,
                "802-11-wireless.hidden", "yes",
            ])

        # --- Shared IPv4 (auto DHCP + NAT) ---
        run([
            "nmcli", "connection", "modify", CONNECTION_NAME,
            "ipv4.method", "shared",
        ])

        # Override gateway if configured
        gw = cfg.network.gateway
        subnet_prefix = cfg.network.subnet.split("/")[-1]
        run([
            "nmcli", "connection", "modify", CONNECTION_NAME,
            "ipv4.addresses", f"{gw}/{subnet_prefix}",
        ])

        # --- Disable IPv6 on AP (simpler routing) ---
        run([
            "nmcli", "connection", "modify", CONNECTION_NAME,
            "ipv6.method", "disabled",
        ])

        # --- Bring it up ---
        logger.info("Activating connection %s …", CONNECTION_NAME)
        run(["nmcli", "connection", "up", CONNECTION_NAME])
        time.sleep(1)

        if self.is_running():
            logger.info("Hotspot is up!")
        else:
            raise RuntimeError(
                "nmcli reported success but connection is not active. "
                "Check `journalctl -u NetworkManager` for details."
            )

    # --------------------------------------------------------------- down --

    def down(self) -> None:
        logger.info("Stopping hotspot …")
        if not self.is_running():
            logger.info("Hotspot is not running — nothing to do.")
            return
        run(["nmcli", "connection", "down", CONNECTION_NAME], check=False)
        self._remove_connection()
        logger.info("Hotspot stopped.")

    # ------------------------------------------------------------- status --

    def status(self) -> dict:
        cfg = self.config
        active = self.is_running()

        result: dict = {
            "backend": self.name,
            "running": active,
            "ssid": cfg.hotspot.ssid,
            "ap_iface": cfg.interfaces.ap,
            "internet_iface": cfg.interfaces.internet,
            "gateway": cfg.network.gateway,
            "band": cfg.hotspot.band,
            "channel": cfg.hotspot.channel,
        }

        if active:
            result["clients"] = len(self.clients())

            # Get IP assigned to AP interface
            ip_out = run_output(["ip", "-4", "addr", "show", cfg.interfaces.ap])
            import re
            m = re.search(r"inet (\S+)", ip_out)
            if m:
                result["ap_ip"] = m.group(1)

        return result

    # ------------------------------------------------------------ clients --

    def clients(self) -> list[Client]:
        return get_clients_networkmanager(self.config.interfaces.ap)

    # ---------------------------------------------------------------- helpers --

    def _remove_connection(self) -> None:
        """Delete the wlanspawn connection profile silently."""
        run(
            ["nmcli", "connection", "delete", CONNECTION_NAME],
            check=False,
        )
