"""Backend factory and registry for wlanspawn."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wlanspawn.backends.base import HotspotBackend
    from wlanspawn.config import WlanspawnConfig


def get_backend(config: WlanspawnConfig) -> HotspotBackend:
    """Return the best available backend for the current system."""
    from wlanspawn.backends.hostapd import HostapdBackend
    from wlanspawn.backends.networkmanager import NetworkManagerBackend
    from wlanspawn.backends.windows import WindowsBackend
    from wlanspawn.detector import Detector

    backend_type = config.backend.type

    candidates = {
        "networkmanager": NetworkManagerBackend,
        "hostapd": HostapdBackend,
        "windows": WindowsBackend,
    }

    if backend_type != "auto" and backend_type in candidates:
        backend = candidates[backend_type](config)
        if not backend.is_available():
            raise RuntimeError(
                f"Configured backend '{backend_type}' is not available on this system.\n"
                "Run `wlanspawn doctor` for details."
            )
        return backend

    # Auto-detect
    det = Detector()
    preferred = det.suggest_backend()

    order = [preferred] + [k for k in candidates if k != preferred]
    for name in order:
        if name in candidates:
            b = candidates[name](config)
            if b.is_available():
                return b

    raise RuntimeError(
        "No supported backend found on this system.\n"
        "Run `wlanspawn doctor` to see what's missing."
    )
