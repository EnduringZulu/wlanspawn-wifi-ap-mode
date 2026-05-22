"""Logging configuration for wlanspawn using Rich."""

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

WLANSPAWN_THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "muted": "dim white",
        "highlight": "bold magenta",
    }
)

_console = Console(theme=WLANSPAWN_THEME)
_err_console = Console(stderr=True, theme=WLANSPAWN_THEME)


def get_console() -> Console:
    return _console


def get_err_console() -> Console:
    return _err_console


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    debug: bool = False,
) -> None:
    """Configure root wlanspawn logger with Rich handler."""
    root = logging.getLogger("wlanspawn")

    if debug:
        level = "DEBUG"

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(numeric_level)

    # Avoid duplicate handlers on re-initialisation
    if root.handlers:
        root.handlers.clear()

    rich_handler = RichHandler(
        console=_err_console,
        rich_tracebacks=True,
        show_path=debug,
        markup=True,
        log_time_format="[%H:%M:%S]",
    )
    rich_handler.setLevel(numeric_level)
    root.addHandler(rich_handler)

    if log_file:
        log_file = Path(log_file).expanduser()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
        )
        file_handler.setLevel(logging.DEBUG)
        root.addHandler(file_handler)
