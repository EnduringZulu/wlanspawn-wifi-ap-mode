"""System-level utilities: OS detection, privilege checks, subprocess wrapper."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto

from wlanspawn.logger import get_logger

logger = get_logger(__name__)


class OS(Enum):
    LINUX = auto()
    WINDOWS = auto()
    MACOS = auto()
    UNKNOWN = auto()


class Distro(Enum):
    FEDORA = auto()
    RHEL = auto()
    DEBIAN = auto()
    UBUNTU = auto()
    ARCH = auto()
    OPENSUSE = auto()
    GENERIC_LINUX = auto()
    NOT_LINUX = auto()


@dataclass
class SystemInfo:
    os: OS
    distro: Distro
    distro_name: str
    kernel: str
    arch: str
    is_root: bool


def detect_os() -> OS:
    system = platform.system().lower()
    if system == "linux":
        return OS.LINUX
    if system == "windows":
        return OS.WINDOWS
    if system == "darwin":
        return OS.MACOS
    return OS.UNKNOWN


def detect_distro() -> tuple[Distro, str]:
    """Return (Distro enum, human-readable name)."""
    if detect_os() != OS.LINUX:
        return Distro.NOT_LINUX, ""

    # Try /etc/os-release first (most modern distros)
    os_release: dict[str, str] = {}
    try:
        with open("/etc/os-release") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k, _, v = line.partition("=")
                    os_release[k] = v.strip('"')
    except FileNotFoundError:
        pass

    name = os_release.get("NAME", "").lower()
    distro_id = os_release.get("ID", "").lower()
    id_like = os_release.get("ID_LIKE", "").lower()
    pretty = os_release.get("PRETTY_NAME", "Linux")

    if "fedora" in distro_id or "fedora" in name:
        return Distro.FEDORA, pretty
    if distro_id in ("rhel", "centos", "rocky", "almalinux") or "rhel" in id_like:
        return Distro.RHEL, pretty
    if "arch" in distro_id or "arch" in id_like:
        return Distro.ARCH, pretty
    if distro_id in ("ubuntu",) or "ubuntu" in name:
        return Distro.UBUNTU, pretty
    if "debian" in distro_id or "debian" in id_like:
        return Distro.DEBIAN, pretty
    if "suse" in distro_id or "suse" in id_like:
        return Distro.OPENSUSE, pretty

    return Distro.GENERIC_LINUX, pretty


def get_system_info() -> SystemInfo:
    os_type = detect_os()
    distro, distro_name = detect_distro()
    return SystemInfo(
        os=os_type,
        distro=distro,
        distro_name=distro_name,
        kernel=platform.release(),
        arch=platform.machine(),
        is_root=is_root(),
    )


def is_root() -> bool:
    if sys.platform == "win32":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0  # type: ignore[attr-defined]
        except Exception:
            return False
    return os.geteuid() == 0


def require_root(action: str = "this action") -> None:
    """Raise SystemExit if not running as root/admin."""
    if not is_root():
        from rich.console import Console
        c = Console(stderr=True)
        c.print(
            f"[bold red]✗[/] [red]Root / administrator privileges required for {action}.[/]\n"
            "  Re-run with [bold]sudo wlanspawn ...[/] on Linux."
        )
        sys.exit(1)


def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run(
    args: Sequence[str],
    *,
    check: bool = True,
    capture: bool = True,
    input: str | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run a subprocess, log it, return CompletedProcess."""
    logger.debug("$ %s", " ".join(str(a) for a in args))
    return subprocess.run(
        args,
        check=check,
        capture_output=capture,
        text=True,
        input=input,
        timeout=timeout,
    )


def run_output(args: Sequence[str], **kwargs) -> str:
    """Run command and return stripped stdout, or empty string on failure."""
    try:
        result = run(args, check=True, capture=True, **kwargs)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return ""
