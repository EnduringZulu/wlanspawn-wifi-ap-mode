"""Configuration management for wlanspawn.

Config is stored at:
  Linux/macOS : ~/.config/wlanspawn/config.toml
  Windows     : %APPDATA%\\wlanspawn\\config.toml

Log is stored at:
  Linux/macOS : ~/.local/share/wlanspawn/wlanspawn.log
  Windows     : %LOCALAPPDATA%\\wlanspawn\\wlanspawn.log
"""

from __future__ import annotations

import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from wlanspawn.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# TOML compatibility shim (Python 3.9/3.10 vs 3.11+)
# ---------------------------------------------------------------------------
try:
    import tomllib  # type: ignore[import]
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[import,no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

# tomli_w not needed - we use custom TOML serializer _config_to_toml


class ConfigError(RuntimeError):
    """Raised for configuration problems."""


# ---------------------------------------------------------------------------
# Config paths
# ---------------------------------------------------------------------------

def _config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "wlanspawn"


def _log_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "wlanspawn"


def default_config_path() -> Path:
    return _config_dir() / "config.toml"


def default_log_path() -> Path:
    return _log_dir() / "wlanspawn.log"


# ---------------------------------------------------------------------------
# Dataclass config schema
# ---------------------------------------------------------------------------

@dataclass
class HotspotConfig:
    ssid: str = "wlanspawn"
    password: str = "changeme!"
    band: str = "2.4GHz"           # "2.4GHz" or "5GHz"
    channel: int = 6
    hidden: bool = False


@dataclass
class InterfacesConfig:
    internet: str = ""             # Interface with internet (e.g. wlan0, eth0)
    ap: str = ""                   # Interface to use as AP (e.g. wlan1)


@dataclass
class NetworkConfig:
    gateway: str = "192.168.73.1"
    subnet: str = "192.168.73.0/24"
    dhcp_range_start: str = "192.168.73.10"
    dhcp_range_end: str = "192.168.73.100"
    dns: str = "8.8.8.8,1.1.1.1"


@dataclass
class BackendConfig:
    type: str = "auto"             # "auto" | "networkmanager" | "hostapd" | "windows"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = str(default_log_path())


@dataclass
class WlanspawnConfig:
    hotspot: HotspotConfig = field(default_factory=HotspotConfig)
    interfaces: InterfacesConfig = field(default_factory=InterfacesConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def _nested_update(base: dict, updates: dict) -> dict:
    """Recursively update base dict with updates."""
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _nested_update(base[k], v)
        else:
            base[k] = v
    return base


def load_config(path: Path | None = None) -> WlanspawnConfig:
    """Load config from TOML file, or return defaults if not found."""
    path = path or default_config_path()
    cfg = WlanspawnConfig()

    if not path.exists():
        return cfg

    if tomllib is None:
        raise ConfigError(
            "TOML library not available. Install wlanspawn with: pip install wlanspawn"
        )

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        raise ConfigError(f"Failed to parse config at {path}: {e}") from e

    # Populate dataclasses
    if "hotspot" in data:
        for k, v in data["hotspot"].items():
            if hasattr(cfg.hotspot, k):
                setattr(cfg.hotspot, k, v)
    if "interfaces" in data:
        for k, v in data["interfaces"].items():
            if hasattr(cfg.interfaces, k):
                setattr(cfg.interfaces, k, v)
    if "network" in data:
        for k, v in data["network"].items():
            if hasattr(cfg.network, k):
                setattr(cfg.network, k, v)
    if "backend" in data:
        for k, v in data["backend"].items():
            if hasattr(cfg.backend, k):
                setattr(cfg.backend, k, v)
    if "logging" in data:
        for k, v in data["logging"].items():
            if hasattr(cfg.logging, k):
                setattr(cfg.logging, k, v)

    logger.debug("Config loaded from %s", path)
    return cfg


def save_config(cfg: WlanspawnConfig, path: Path | None = None) -> Path:
    """Write config to TOML file, creating parent directories as needed."""
    path = path or default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    toml_str = _config_to_toml(cfg)

    with open(path, "w") as f:
        f.write(toml_str)

    logger.debug("Config saved to %s", path)
    return path


def _config_to_toml(cfg: WlanspawnConfig) -> str:
    """Serialize WlanspawnConfig to TOML string (without external dep)."""
    lines = [
        "# wlanspawn configuration\n",
        "# Edit this file or run `wlanspawn init` to reconfigure.\n\n",
    ]

    def section(name: str, obj) -> None:
        lines.append(f"[{name}]\n")
        for k, v in asdict(obj).items():
            if isinstance(v, bool):
                lines.append(f"{k} = {'true' if v else 'false'}\n")
            elif isinstance(v, int):
                lines.append(f"{k} = {v}\n")
            elif isinstance(v, str):
                escaped = v.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{k} = "{escaped}"\n')
        lines.append("\n")

    section("hotspot", cfg.hotspot)
    section("interfaces", cfg.interfaces)
    section("network", cfg.network)
    section("backend", cfg.backend)
    section("logging", cfg.logging)

    return "".join(lines)


# ---------------------------------------------------------------------------
# Interactive init wizard
# ---------------------------------------------------------------------------

def run_init_wizard(existing: WlanspawnConfig | None = None) -> WlanspawnConfig:
    """Interactive CLI wizard to configure wlanspawn."""
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    from wlanspawn.utils.network import get_wireless_interfaces

    console = Console()
    cfg = existing or WlanspawnConfig()

    console.print(Panel.fit(
        "[bold cyan]wlanspawn[/] configuration wizard\n"
        "[dim]Press Enter to accept the default shown in brackets.[/dim]",
        border_style="cyan",
    ))
    console.print()

    # Show available wireless interfaces
    ifaces = get_wireless_interfaces()
    if ifaces:
        table = Table(title="Detected wireless interfaces", box=None, show_header=True)
        table.add_column("Interface", style="cyan")
        table.add_column("MAC", style="dim")
        table.add_column("State")
        table.add_column("AP capable")
        for i in ifaces:
            table.add_row(
                i.name,
                i.mac,
                i.state,
                "[green]✓[/]" if i.supports_ap else "[red]✗[/]",
            )
        console.print(table)
        console.print()

    # --- Interfaces ---
    iface_names = [i.name for i in ifaces]

    default_internet = cfg.interfaces.internet or (iface_names[0] if iface_names else "wlan0")
    cfg.interfaces.internet = click.prompt(
        "  Internet source interface (has internet connection)",
        default=default_internet,
    )

    ap_default = cfg.interfaces.ap
    if not ap_default and len(iface_names) > 1:
        ap_default = next((n for n in iface_names if n != cfg.interfaces.internet), iface_names[-1])
    ap_default = ap_default or "wlan1"

    cfg.interfaces.ap = click.prompt(
        "  Hotspot AP interface (will broadcast the SSID)",
        default=ap_default,
    )

    console.print()

    # --- Hotspot ---
    cfg.hotspot.ssid = click.prompt("  SSID (network name)", default=cfg.hotspot.ssid)

    cfg.hotspot.password = click.prompt(
        "  Password (min 8 chars)",
        default=cfg.hotspot.password,
        hide_input=False,
    )
    while len(cfg.hotspot.password) < 8:
        console.print("[red]  Password must be at least 8 characters.[/]")
        cfg.hotspot.password = click.prompt(
            "  Password (min 8 chars)", hide_input=False
        )

    band = click.prompt(
        "  Frequency band",
        type=click.Choice(["2.4GHz", "5GHz"]),
        default=cfg.hotspot.band,
        show_choices=True,
    )
    cfg.hotspot.band = band

    cfg.hotspot.channel = click.prompt(
        "  Channel (2.4GHz: 1-11, 5GHz: 36-165)",
        default=cfg.hotspot.channel,
        type=int,
    )

    hidden = click.confirm("  Hide SSID?", default=cfg.hotspot.hidden)
    cfg.hotspot.hidden = hidden

    console.print()

    # --- Backend ---
    backend_choices = ["auto", "networkmanager", "hostapd", "windows"]
    cfg.backend.type = click.prompt(
        "  Backend",
        type=click.Choice(backend_choices),
        default=cfg.backend.type,
        show_choices=True,
    )

    console.print()
    console.print("[bold green]✓[/] Configuration ready.")
    return cfg


def validate_config(cfg: WlanspawnConfig) -> list[str]:
    """Return list of validation errors (empty = OK)."""
    errors = []
    if not cfg.interfaces.internet:
        errors.append("interfaces.internet is not set — run `wlanspawn init`")
    if not cfg.interfaces.ap:
        errors.append("interfaces.ap is not set — run `wlanspawn init`")
    if cfg.interfaces.internet == cfg.interfaces.ap:
        errors.append("internet and ap interfaces must be different")
    if len(cfg.hotspot.password) < 8:
        errors.append("hotspot.password must be at least 8 characters")
    if not cfg.hotspot.ssid:
        errors.append("hotspot.ssid cannot be empty")
    return errors
