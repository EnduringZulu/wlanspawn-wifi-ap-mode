"""Auto-detection of OS, distro, backend, and AP-capable interfaces."""

from __future__ import annotations

from wlanspawn.logger import get_logger
from wlanspawn.utils.network import (
    Interface,
    get_ap_capable_interfaces,
    get_wireless_interfaces,
    list_interfaces,
)
from wlanspawn.utils.system import (
    OS,
    Distro,
    SystemInfo,
    cmd_exists,
    get_system_info,
)

logger = get_logger(__name__)


class Detector:
    """One-stop class for environment auto-detection."""

    def __init__(self) -> None:
        self._sys: SystemInfo | None = None

    @property
    def sys(self) -> SystemInfo:
        if self._sys is None:
            self._sys = get_system_info()
        return self._sys

    # ------------------------------------------------------------------ OS --

    def os(self) -> OS:
        return self.sys.os

    def distro(self) -> Distro:
        return self.sys.distro

    def distro_name(self) -> str:
        return self.sys.distro_name

    # ------------------------------------------------------------ Interfaces --

    def all_interfaces(self) -> list[Interface]:
        return list_interfaces()

    def wireless_interfaces(self) -> list[Interface]:
        return get_wireless_interfaces()

    def ap_capable_interfaces(self) -> list[Interface]:
        return get_ap_capable_interfaces()

    def suggest_internet_iface(self, exclude: str | None = None) -> str | None:
        """Return best guess for the internet-connected interface."""
        from wlanspawn.utils.system import run_output

        # Look at default route
        if self.sys.os == OS.LINUX:
            output = run_output(["ip", "route", "show", "default"])
            for line in output.splitlines():
                if "default" in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p == "dev" and i + 1 < len(parts):
                            iface = parts[i + 1]
                            if iface != exclude:
                                return iface
        return None

    def suggest_ap_iface(self, exclude: str | None = None) -> str | None:
        """Return best guess for an AP-capable interface that isn't the internet one."""
        candidates = [i for i in self.ap_capable_interfaces() if i.name != exclude]
        if candidates:
            return candidates[0].name
        # Fallback: any wireless that isn't excluded
        others = [i for i in self.wireless_interfaces() if i.name != exclude]
        if others:
            return others[0].name
        return None

    # ------------------------------------------------------------ Backend  --

    def suggest_backend(self) -> str:
        """Return the best available backend ID for this system."""
        if self.sys.os == OS.WINDOWS:
            return "windows"
        if self.sys.os == OS.LINUX:
            if cmd_exists("nmcli"):
                return "networkmanager"
            if cmd_exists("hostapd") and cmd_exists("dnsmasq"):
                return "hostapd"
        return "hostapd"

    # ------------------------------------------------------------ Summary  --

    def summary(self) -> dict:
        return {
            "os": self.sys.os.name,
            "distro": self.sys.distro_name or self.sys.os.name,
            "kernel": self.sys.kernel,
            "arch": self.sys.arch,
            "is_root": self.sys.is_root,
            "backend": self.suggest_backend(),
            "wireless_ifaces": [i.name for i in self.wireless_interfaces()],
            "ap_capable": [i.name for i in self.ap_capable_interfaces()],
        }
