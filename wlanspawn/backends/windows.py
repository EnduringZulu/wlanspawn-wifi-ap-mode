"""Windows backend — hotspot via `netsh wlan hostednetwork`.

Uses the Windows Wireless Hosted Network feature, available since Windows 7.
Internet Connection Sharing (ICS) is managed via PowerShell / netsh.

Note: Windows 10 1703+ also supports the Mobile Hotspot API (Settings → Network → Mobile Hotspot),
but netsh gives more programmatic control and is available without UWP.

Limitations:
  - Requires a Wi-Fi adapter that supports virtual access points
  - Some Wi-Fi drivers disable hosted network; update drivers if it fails
  - 2.4 GHz only via hosted network; use Mobile Hotspot API for 5 GHz
"""

from __future__ import annotations

import subprocess
import sys

from wlanspawn.backends.base import HotspotBackend
from wlanspawn.logger import get_logger
from wlanspawn.utils.network import Client, get_clients_windows
from wlanspawn.utils.system import cmd_exists, run, run_output

logger = get_logger(__name__)


class WindowsBackend(HotspotBackend):
    """Hotspot via Windows Wireless Hosted Network (netsh wlan)."""

    name = "windows"

    def is_available(self) -> bool:
        if sys.platform != "win32":
            return False
        return cmd_exists("netsh")

    def is_running(self) -> bool:
        output = run_output(["netsh", "wlan", "show", "hostednetwork"])
        return "Status                 : Started" in output

    # ------------------------------------------------------------------ up --

    def up(self) -> None:
        cfg = self.config
        ssid = cfg.hotspot.ssid
        password = cfg.hotspot.password

        logger.info("Configuring Windows hosted network: SSID=%s", ssid)

        # Configure hosted network
        run(["netsh", "wlan", "set", "hostednetwork",
             "mode=allow",
             f"ssid={ssid}",
             f"key={password}",
             "keyusage=persistent"])

        # Start hosted network
        result = run(["netsh", "wlan", "start", "hostednetwork"], check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to start hosted network:\n{result.stdout}\n{result.stderr}\n\n"
                "Possible fixes:\n"
                "  1. Run as Administrator\n"
                "  2. Update your Wi-Fi driver\n"
                "  3. Check: netsh wlan show drivers | findstr 'Hosted network'"
            )

        # Enable ICS (Internet Connection Sharing)
        self._enable_ics(cfg.interfaces.internet)

        logger.info("Windows hotspot is up!")

    # --------------------------------------------------------------- down --

    def down(self) -> None:
        logger.info("Stopping Windows hosted network …")
        run(["netsh", "wlan", "stop", "hostednetwork"], check=False)
        logger.info("Hotspot stopped.")

    # ------------------------------------------------------------- status --

    def status(self) -> dict:
        cfg = self.config
        output = run_output(["netsh", "wlan", "show", "hostednetwork"])
        running = "Status                 : Started" in output

        return {
            "backend": self.name,
            "running": running,
            "ssid": cfg.hotspot.ssid,
            "ap_iface": cfg.interfaces.ap or "(auto)",
            "internet_iface": cfg.interfaces.internet,
            "band": "2.4GHz",
            "clients": len(self.clients()) if running else 0,
        }

    # ------------------------------------------------------------ clients --

    def clients(self) -> list[Client]:
        return get_clients_windows()

    # ---------------------------------------------------------------- ICS --

    def _enable_ics(self, internet_iface: str) -> None:
        """Enable Internet Connection Sharing via PowerShell/netsh."""
        if not internet_iface:
            logger.warning("No internet interface specified; skipping ICS setup")
            return

        ps_script = f"""
$sharing = Get-NetAdapter | Where-Object {{ $_.Name -eq '{internet_iface}' }}
if ($sharing) {{
    $sharing | Set-NetConnectionSharing -Enabled $true -ConnectionSharingType Internet
    Write-Host "ICS enabled on $($sharing.Name)"
}} else {{
    Write-Warning "Interface '{internet_iface}' not found for ICS"
}}
"""
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            logger.info("Internet Connection Sharing enabled")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(
                "Could not enable ICS automatically: %s\n"
                "Enable manually: Control Panel → Network → Right-click %s → Properties → Sharing",
                e,
                internet_iface,
            )
