"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import os


@pytest.fixture
def tmp_config_path(tmp_path: Path) -> Path:
    """Return a temporary config file path."""
    return tmp_path / "config.toml"


@pytest.fixture
def minimal_config():
    """Return a minimal valid WlanspawnConfig."""
    from wlanspawn.config import WlanspawnConfig, HotspotConfig, InterfacesConfig
    cfg = WlanspawnConfig()
    cfg.hotspot = HotspotConfig(ssid="TestNet", password="test1234")
    cfg.interfaces = InterfacesConfig(internet="wlan0", ap="wlan1")
    return cfg


@pytest.fixture(autouse=True)
def no_real_commands(monkeypatch):
    """Prevent tests from running real system commands by default."""
    # Tests that need real commands should opt out with:
    #   @pytest.mark.usefixtures("no_no_real_commands")
    import subprocess
    
    original_run = subprocess.run
    
    def mock_run(*args, **kwargs):
        # Raise if a test tries to run a real command without mocking
        raise RuntimeError(
            f"Test tried to run real command: {args[0]!r}\n"
            "Mock it with: patch('wlanspawn.utils.system.run', ...)"
        )
    
    # Don't monkeypatch — tests should explicitly patch what they need
    yield
