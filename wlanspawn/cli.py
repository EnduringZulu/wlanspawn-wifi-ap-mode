"""wlanspawn CLI — main entry point.

All user-facing commands live here.  Rich is used throughout for
professional terminal output.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from wlanspawn import __version__
from wlanspawn.config import (
    ConfigError,
    WlanspawnConfig,
    default_config_path,
    load_config,
    run_init_wizard,
    save_config,
    validate_config,
)
from wlanspawn.logger import get_logger, setup_logging

logger = get_logger(__name__)
console = Console()
err_console = Console(stderr=True)

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(__version__, "-V", "--version", message="wlanspawn %(version)s")
@click.option("--debug", is_flag=True, envvar="WLANSPAWN_DEBUG", help="Enable debug output.")
@click.option(
    "--config", "-c",
    default=None,
    type=click.Path(path_type=Path),
    help="Path to config file (default: ~/.config/wlanspawn/config.toml)",
)
@click.pass_context
def cli(ctx: click.Context, debug: bool, config: Path | None) -> None:
    """
    \b
    ╻ ╻╻  ┏━┓┏┓╻┏━┓┏━┓┏━┓╻ ╻┏┓╻
    ┃╻┃┃  ┣━┫┃┗┫┗━┓┣━┛┣━┫┃╻┃┃┗┫
    ┗┻┛┗━╸╹ ╹╹ ╹┗━┛╹  ╹ ╹┗┻┛╹ ╹

    Turn any Wi-Fi adapter into a hotspot in seconds.

    \b
    Quick start:
      wlanspawn init      Interactive setup wizard
      wlanspawn up        Start the hotspot
      wlanspawn status    Check hotspot status
      wlanspawn clients   Show connected devices
      wlanspawn down      Stop the hotspot
      wlanspawn doctor    Check system dependencies
    """
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["config_path"] = config

    # Set up logging early so all subcommands benefit
    setup_logging(debug=debug)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_cfg(ctx: click.Context) -> WlanspawnConfig:
    path = ctx.obj.get("config_path")
    try:
        return load_config(path)
    except ConfigError as e:
        err_console.print(f"[bold red]✗[/] Config error: {e}")
        sys.exit(1)


def _banner(title: str, subtitle: str = "") -> None:
    console.print(Panel.fit(
        f"[bold cyan]{title}[/]" + (f"\n[dim]{subtitle}[/]" if subtitle else ""),
        border_style="dim",
    ))


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--force", "-f", is_flag=True, help="Re-run wizard even if config exists.")
@click.pass_context
def init(ctx: click.Context, force: bool) -> None:
    """Interactive setup wizard — configure SSID, password, and interfaces."""
    path = ctx.obj.get("config_path") or default_config_path()

    existing: WlanspawnConfig | None = None
    if path.exists() and not force:
        console.print(f"[dim]Loading existing config from {path}[/dim]")
        existing = _load_cfg(ctx)

    console.print()
    cfg = run_init_wizard(existing)

    errors = validate_config(cfg)
    if errors:
        err_console.print("[bold red]✗ Validation errors:[/]")
        for e in errors:
            err_console.print(f"  [red]•[/] {e}")
        sys.exit(1)

    saved = save_config(cfg, path)
    console.print()
    console.print(Panel.fit(
        f"[bold green]✓ Config saved[/] → [cyan]{saved}[/]\n\n"
        "Run [bold]wlanspawn up[/] to start your hotspot.",
        border_style="green",
    ))


# ---------------------------------------------------------------------------
# up
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--ssid", default=None, help="Override SSID.")
@click.option("--password", "-p", default=None, help="Override password.")
@click.option("--iface", "-i", default=None, help="Override AP interface.")
@click.pass_context
def up(ctx: click.Context, ssid: str | None, password: str | None, iface: str | None) -> None:
    """Start the hotspot / access point."""
    from wlanspawn.backends import get_backend
    from wlanspawn.utils.system import require_root

    require_root("starting a hotspot")
    cfg = _load_cfg(ctx)

    errors = validate_config(cfg)
    if errors:
        err_console.print("[bold red]✗ Configuration is incomplete:[/]")
        for e in errors:
            err_console.print(f"  [red]•[/] {e}")
        err_console.print("\nRun [bold]wlanspawn init[/] to configure.")
        sys.exit(1)

    # Apply CLI overrides
    if ssid:
        cfg.hotspot.ssid = ssid
    if password:
        cfg.hotspot.password = password
    if iface:
        cfg.interfaces.ap = iface

    console.print()
    console.print(
        f"[bold cyan]↑[/] Starting hotspot [bold]{cfg.hotspot.ssid}[/] "
        f"on [cyan]{cfg.interfaces.ap}[/] …"
    )
    console.print(
        f"  Internet source : [cyan]{cfg.interfaces.internet}[/]\n"
        f"  Band / Channel  : {cfg.hotspot.band} / ch{cfg.hotspot.channel}\n"
        f"  Gateway         : {cfg.network.gateway}\n"
        f"  Backend         : {cfg.backend.type}"
    )
    console.print()

    try:
        backend = get_backend(cfg)
        console.print(f"[dim]Using backend: {backend.name}[/dim]")
        backend.up()
    except Exception as e:
        err_console.print(f"\n[bold red]✗ Failed to start hotspot:[/] {e}")
        if ctx.obj.get("debug"):
            import traceback
            traceback.print_exc()
        sys.exit(1)

    console.print()
    console.print(Panel.fit(
        f"[bold green]✓ Hotspot is live![/]\n\n"
        f"  SSID     : [bold]{cfg.hotspot.ssid}[/]\n"
        f"  Password : [bold]{cfg.hotspot.password}[/]\n"
        f"  Gateway  : [bold]{cfg.network.gateway}[/]\n\n"
        f"[dim]Run [bold]wlanspawn status[/] or [bold]wlanspawn clients[/] to monitor.[/dim]",
        border_style="green",
    ))


# ---------------------------------------------------------------------------
# down
# ---------------------------------------------------------------------------

@cli.command()
@click.pass_context
def down(ctx: click.Context) -> None:
    """Stop the hotspot."""
    from wlanspawn.backends import get_backend
    from wlanspawn.utils.system import require_root

    require_root("stopping a hotspot")
    cfg = _load_cfg(ctx)

    console.print("[bold cyan]↓[/] Stopping hotspot …")
    try:
        backend = get_backend(cfg)
        backend.down()
    except Exception as e:
        err_console.print(f"[bold red]✗[/] {e}")
        sys.exit(1)

    console.print("[bold green]✓[/] Hotspot stopped.")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def status(ctx: click.Context, as_json: bool) -> None:
    """Show hotspot status and configuration."""
    from wlanspawn.backends import get_backend

    cfg = _load_cfg(ctx)

    try:
        backend = get_backend(cfg)
        info = backend.status()
    except Exception as e:
        err_console.print(f"[bold red]✗[/] {e}")
        sys.exit(1)

    if as_json:
        import json
        console.print(json.dumps(info, indent=2))
        return

    running = info.get("running", False)
    state_str = "[bold green]● RUNNING[/]" if running else "[bold red]○ STOPPED[/]"

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Status", state_str)
    table.add_row("SSID", info.get("ssid", "—"))
    table.add_row("Password", cfg.hotspot.password)
    table.add_row("Band / Ch", f"{info.get('band', '—')} / ch{info.get('channel', '—')}")
    table.add_row("AP Interface", info.get("ap_iface", "—"))
    table.add_row("Internet If", info.get("internet_iface", "—"))
    table.add_row("Gateway IP", info.get("gateway", "—"))
    if "ap_ip" in info:
        table.add_row("AP IP/CIDR", info["ap_ip"])
    table.add_row("Backend", info.get("backend", "—"))
    if running:
        table.add_row("Clients", str(info.get("clients", 0)))

    console.print()
    console.print(Panel(
        table,
        title="[bold]wlanspawn status[/]",
        border_style="cyan" if running else "dim",
    ))
    console.print()


# ---------------------------------------------------------------------------
# clients
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--watch", "-w", is_flag=True, help="Refresh every 5 seconds.")
@click.pass_context
def clients(ctx: click.Context, as_json: bool, watch: bool) -> None:
    """Show devices connected to the hotspot."""
    import time

    from wlanspawn.backends import get_backend

    cfg = _load_cfg(ctx)

    def _show() -> None:
        try:
            backend = get_backend(cfg)
            if not backend.is_running():
                console.print("[dim]Hotspot is not running.[/dim]")
                return
            client_list = backend.clients()
        except Exception as e:
            err_console.print(f"[bold red]✗[/] {e}")
            return

        if as_json:
            import dataclasses
            import json
            console.print(json.dumps([dataclasses.asdict(c) for c in client_list], indent=2))
            return

        table = Table(
            title=f"Connected clients ({len(client_list)})",
            box=box.ROUNDED,
            show_lines=False,
            header_style="bold cyan",
        )
        table.add_column("MAC Address", style="cyan")
        table.add_column("IP Address")
        table.add_column("Hostname")
        table.add_column("Signal", justify="right")
        table.add_column("↓ RX", justify="right", style="green")
        table.add_column("↑ TX", justify="right", style="blue")

        if not client_list:
            table.add_row("[dim]No clients connected[/dim]", "", "", "", "", "")
        else:
            for c in client_list:
                sig = f"{c.signal_dbm} dBm" if c.signal_dbm is not None else "—"
                rx = _human_bytes(c.rx_bytes) if c.rx_bytes else "—"
                tx = _human_bytes(c.tx_bytes) if c.tx_bytes else "—"
                table.add_row(c.mac, c.ip or "—", c.hostname or "—", sig, rx, tx)

        console.print()
        console.print(table)
        console.print()

    if watch:
        try:
            while True:
                console.clear()
                _show()
                console.print("[dim]Refreshing every 5s — Ctrl+C to stop[/dim]")
                time.sleep(5)
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped.[/dim]")
    else:
        _show()


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

@cli.command()
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Check system dependencies and configuration health."""
    from wlanspawn.doctor import format_results, run_doctor

    cfg = _load_cfg(ctx)

    console.print()
    console.print(Panel.fit(
        "[bold cyan]wlanspawn doctor[/]\n"
        "[dim]Checking system dependencies and configuration …[/dim]",
        border_style="cyan",
    ))
    console.print()

    results = run_doctor(backend=cfg.backend.type)
    format_results(results)

    errors = validate_config(cfg)
    if errors:
        console.print()
        console.print("[bold yellow]Configuration warnings:[/]")
        for e in errors:
            console.print(f"  [yellow]![/] {e}")

    console.print()


# ---------------------------------------------------------------------------
# config (show / edit)
# ---------------------------------------------------------------------------

@cli.group()
def config() -> None:
    """View or manage the wlanspawn configuration."""


@config.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Print the current configuration."""
    path = ctx.obj.get("config_path") or default_config_path()
    if not path.exists():
        console.print(f"[dim]No config file found at {path}. Run `wlanspawn init`.[/dim]")
        return
    from rich.syntax import Syntax
    content = path.read_text()
    console.print(Syntax(content, "toml", theme="monokai", line_numbers=True))


@config.command("path")
@click.pass_context
def config_path(ctx: click.Context) -> None:
    """Print the path to the config file."""
    path = ctx.obj.get("config_path") or default_config_path()
    console.print(str(path))


@config.command("edit")
@click.pass_context
def config_edit(ctx: click.Context) -> None:
    """Open the config file in $EDITOR."""
    path = ctx.obj.get("config_path") or default_config_path()
    if not path.exists():
        console.print("[dim]No config yet — run `wlanspawn init` first.[/dim]")
        sys.exit(1)
    click.edit(filename=str(path))


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main() -> None:
    cli(obj={})


if __name__ == "__main__":
    main()
