"""wlanspawn doctor — checks all runtime dependencies and system state."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum, auto

from wlanspawn.logger import get_logger
from wlanspawn.utils.system import OS, cmd_exists, detect_os, is_root, run_output

logger = get_logger(__name__)


class CheckStatus(Enum):
    OK = auto()
    WARN = auto()
    FAIL = auto()


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    fix: str = ""

    @property
    def icon(self) -> str:
        return {"OK": "✓", "WARN": "!", "FAIL": "✗"}.get(self.status.name, "?")

    @property
    def style(self) -> str:
        return {"OK": "green", "WARN": "yellow", "FAIL": "red"}.get(self.status.name, "white")


def run_doctor(backend: str = "auto") -> list[CheckResult]:
    """Run all doctor checks and return results."""
    results: list[CheckResult] = []
    os_type = detect_os()

    # Universal checks
    results.extend(_check_universal())

    if os_type == OS.LINUX:
        results.extend(_check_linux())
        if backend in ("auto", "networkmanager"):
            results.extend(_check_networkmanager())
        if backend in ("auto", "hostapd"):
            results.extend(_check_hostapd())
    elif os_type == OS.WINDOWS:
        results.extend(_check_windows())
    else:
        results.append(
            CheckResult(
                "os",
                CheckStatus.WARN,
                f"Operating system '{sys.platform}' has limited support",
                "See https://github.com/yourusername/wlanspawn#supported-platforms",
            )
        )

    return results


def _ok(name: str, msg: str) -> CheckResult:
    return CheckResult(name, CheckStatus.OK, msg)


def _warn(name: str, msg: str, fix: str = "") -> CheckResult:
    return CheckResult(name, CheckStatus.WARN, msg, fix)


def _fail(name: str, msg: str, fix: str = "") -> CheckResult:
    return CheckResult(name, CheckStatus.FAIL, msg, fix)


def _check_universal() -> list[CheckResult]:
    results = []

    # Python version
    ver = sys.version_info
    if ver >= (3, 9):
        results.append(_ok("python", f"Python {ver.major}.{ver.minor}.{ver.micro}"))
    else:
        results.append(_fail("python", f"Python {ver.major}.{ver.minor} is too old", "Upgrade to Python 3.9+"))

    # Root / admin
    if is_root():
        results.append(_ok("privileges", "Running as root / administrator"))
    else:
        results.append(
            _fail(
                "privileges",
                "Not running as root",
                "Use: sudo wlanspawn <command>",
            )
        )

    return results


def _check_linux() -> list[CheckResult]:
    results = []

    for tool in ["ip", "iptables"]:
        if cmd_exists(tool):
            results.append(_ok(tool, f"`{tool}` found"))
        else:
            results.append(
                _fail(tool, f"`{tool}` not found", "Install: iproute2 / iptables")
            )

    # nftables as iptables alternative
    if not cmd_exists("iptables") and cmd_exists("nft"):
        results.append(_warn("nftables", "`nft` found but `iptables` preferred", "Install iptables or wlanspawn will use nft"))

    # iw
    if cmd_exists("iw"):
        results.append(_ok("iw", "`iw` found — AP capability detection available"))
    else:
        results.append(_warn("iw", "`iw` not found — AP capability detection limited", "Install: iw"))

    # Kernel IP forward
    try:
        with open("/proc/sys/net/ipv4/ip_forward") as f:
            val = f.read().strip()
        if val == "1":
            results.append(_ok("ip_forward", "IPv4 forwarding is enabled"))
        else:
            results.append(
                _warn(
                    "ip_forward",
                    "IPv4 forwarding is currently disabled",
                    "wlanspawn will enable it automatically with `wlanspawn up`",
                )
            )
    except OSError:
        results.append(_warn("ip_forward", "Could not read /proc/sys/net/ipv4/ip_forward"))

    return results


def _check_networkmanager() -> list[CheckResult]:
    results = []

    if cmd_exists("nmcli"):
        version_out = run_output(["nmcli", "--version"])
        results.append(_ok("nmcli", f"`nmcli` found: {version_out}"))
    else:
        results.append(
            _fail(
                "nmcli",
                "`nmcli` not found — NetworkManager backend unavailable",
                "Install NetworkManager or switch to hostapd backend",
            )
        )
        return results

    # Check NM is running
    nm_status = run_output(["systemctl", "is-active", "NetworkManager"])
    if nm_status == "active":
        results.append(_ok("NetworkManager", "NetworkManager service is running"))
    else:
        results.append(
            _fail(
                "NetworkManager",
                f"NetworkManager service is not active (status: {nm_status})",
                "Run: sudo systemctl start NetworkManager",
            )
        )

    return results


def _check_hostapd() -> list[CheckResult]:
    results = []

    for tool, pkg in [("hostapd", "hostapd"), ("dnsmasq", "dnsmasq")]:
        if cmd_exists(tool):
            results.append(_ok(tool, f"`{tool}` found"))
        else:
            results.append(
                _fail(
                    tool,
                    f"`{tool}` not found — hostapd backend unavailable",
                    f"Fedora: dnf install {pkg}  |  Debian: apt install {pkg}  |  Arch: pacman -S {pkg}",
                )
            )

    return results


def _check_windows() -> list[CheckResult]:
    results = []

    netsh = cmd_exists("netsh")
    if netsh:
        results.append(_ok("netsh", "`netsh` found"))
    else:
        results.append(_fail("netsh", "`netsh` not found — unusual Windows setup"))

    # Check hosted network support
    output = run_output(["netsh", "wlan", "show", "drivers"])
    if "Hosted network supported  : Yes" in output:
        results.append(_ok("hosted_network", "Hosted network (virtual AP) is supported"))
    else:
        results.append(
            _warn(
                "hosted_network",
                "Hosted network may not be supported by your Wi-Fi adapter/driver",
                "Update your Wi-Fi driver or check adapter compatibility",
            )
        )

    return results


def format_results(results: list[CheckResult]) -> None:
    """Print doctor results to the terminal using Rich."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 1))
    table.add_column("", width=3)
    table.add_column("Check", style="bold")
    table.add_column("Details")
    table.add_column("Fix", style="dim")

    for r in results:
        table.add_row(
            f"[{r.style}]{r.icon}[/]",
            r.name,
            r.message,
            r.fix,
        )

    console.print(table)

    fails = sum(1 for r in results if r.status == CheckStatus.FAIL)
    warns = sum(1 for r in results if r.status == CheckStatus.WARN)
    oks = sum(1 for r in results if r.status == CheckStatus.OK)

    console.print()
    console.print(
        f"[green]{oks} passed[/]  "
        f"[yellow]{warns} warnings[/]  "
        f"[red]{fails} failed[/]"
    )

    if fails:
        console.print(
            "\n[bold red]✗[/] Doctor found issues. Fix them before running `wlanspawn up`."
        )
    elif warns:
        console.print(
            "\n[bold yellow]![/] Doctor found warnings. wlanspawn may still work."
        )
    else:
        console.print(
            "\n[bold green]✓[/] All checks passed. You're good to go!"
        )
