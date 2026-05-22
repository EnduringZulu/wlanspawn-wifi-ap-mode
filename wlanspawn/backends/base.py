"""Abstract base class for hotspot backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from wlanspawn.config import WlanspawnConfig
from wlanspawn.utils.network import Client


class HotspotBackend(ABC):
    """All hotspot backends implement this interface."""

    #: Human-readable backend identifier
    name: str = "base"

    def __init__(self, config: WlanspawnConfig) -> None:
        self.config = config

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this backend's dependencies are present."""

    @abstractmethod
    def is_running(self) -> bool:
        """Return True if a hotspot managed by this backend is active."""

    @abstractmethod
    def up(self) -> None:
        """Start the hotspot. Must raise RuntimeError on failure."""

    @abstractmethod
    def down(self) -> None:
        """Stop the hotspot. Must raise RuntimeError on failure."""

    @abstractmethod
    def status(self) -> dict:
        """Return a dict with status fields (ssid, clients, ip, etc.)."""

    @abstractmethod
    def clients(self) -> list[Client]:
        """Return list of currently connected clients."""
