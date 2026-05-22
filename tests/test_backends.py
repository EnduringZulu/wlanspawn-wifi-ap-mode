"""Tests for wlanspawn backends."""

import pytest
from unittest.mock import patch, MagicMock, call
import subprocess

from wlanspawn.config import WlanspawnConfig, HotspotConfig, InterfacesConfig, BackendConfig


@pytest.fixture
def nm_config():
    cfg = WlanspawnConfig()
    cfg.hotspot = HotspotConfig(ssid="TestNet", password="test1234", band="2.4GHz", channel=6)
    cfg.interfaces = InterfacesConfig(internet="wlan0", ap="wlan1")
    cfg.backend = BackendConfig(type="networkmanager")
    return cfg


@pytest.fixture
def hostapd_config():
    cfg = WlanspawnConfig()
    cfg.hotspot = HotspotConfig(ssid="TestNet", password="test1234", band="2.4GHz", channel=6)
    cfg.interfaces = InterfacesConfig(internet="wlan0", ap="wlan1")
    cfg.backend = BackendConfig(type="hostapd")
    return cfg


class TestNetworkManagerBackend:
    def test_is_available_no_nmcli(self, nm_config):
        from wlanspawn.backends.networkmanager import NetworkManagerBackend
        with patch("wlanspawn.backends.networkmanager.cmd_exists", return_value=False):
            b = NetworkManagerBackend(nm_config)
            assert not b.is_available()

    def test_is_available_with_nmcli_active(self, nm_config):
        from wlanspawn.backends.networkmanager import NetworkManagerBackend
        with patch("wlanspawn.backends.networkmanager.cmd_exists", return_value=True):
            with patch("wlanspawn.backends.networkmanager.run_output", return_value="active"):
                b = NetworkManagerBackend(nm_config)
                assert b.is_available()

    def test_is_running_false_when_not_in_active(self, nm_config):
        from wlanspawn.backends.networkmanager import NetworkManagerBackend
        with patch("wlanspawn.backends.networkmanager.run_output", return_value="other-connection:wifi:activated"):
            b = NetworkManagerBackend(nm_config)
            assert not b.is_running()

    def test_is_running_true_when_connection_active(self, nm_config):
        from wlanspawn.backends.networkmanager import NetworkManagerBackend
        with patch("wlanspawn.backends.networkmanager.run_output", return_value="wlanspawn-hotspot:wifi:activated"):
            b = NetworkManagerBackend(nm_config)
            assert b.is_running()

    def test_status_not_running(self, nm_config):
        from wlanspawn.backends.networkmanager import NetworkManagerBackend
        b = NetworkManagerBackend(nm_config)
        with patch.object(b, "is_running", return_value=False):
            status = b.status()
            assert status["running"] is False
            assert status["ssid"] == "TestNet"
            assert status["backend"] == "networkmanager"

    def test_status_running(self, nm_config):
        from wlanspawn.backends.networkmanager import NetworkManagerBackend
        b = NetworkManagerBackend(nm_config)
        with patch.object(b, "is_running", return_value=True):
            with patch.object(b, "clients", return_value=[]):
                with patch("wlanspawn.utils.system.run_output", return_value="    inet 192.168.73.1/24"):
                    status = b.status()
                    assert status["running"] is True
                    assert status["clients"] == 0


class TestHostapdBackend:
    def test_is_available_missing_tools(self, hostapd_config):
        from wlanspawn.backends.hostapd import HostapdBackend
        with patch("wlanspawn.backends.hostapd.cmd_exists", return_value=False):
            b = HostapdBackend(hostapd_config)
            assert not b.is_available()

    def test_is_available_both_tools(self, hostapd_config):
        from wlanspawn.backends.hostapd import HostapdBackend
        with patch("wlanspawn.backends.hostapd.cmd_exists", return_value=True):
            b = HostapdBackend(hostapd_config)
            assert b.is_available()

    def test_is_running_no_pid_file(self, hostapd_config):
        from wlanspawn.backends.hostapd import HostapdBackend
        b = HostapdBackend(hostapd_config)
        with patch("pathlib.Path.exists", return_value=False):
            assert not b.is_running()

    def test_write_hostapd_conf_contents(self, tmp_path):
        from wlanspawn.backends.hostapd import _write_hostapd_conf
        conf = tmp_path / "hostapd.conf"
        _write_hostapd_conf(conf, "wlan1", "TestNet", "password1", 6, "2.4GHz", False)
        content = conf.read_text()
        assert "interface=wlan1" in content
        assert "ssid=TestNet" in content
        assert "wpa_passphrase=password1" in content
        assert "channel=6" in content
        assert "hw_mode=g" in content

    def test_write_hostapd_conf_5ghz(self, tmp_path):
        from wlanspawn.backends.hostapd import _write_hostapd_conf
        conf = tmp_path / "hostapd.conf"
        _write_hostapd_conf(conf, "wlan1", "TestNet", "password1", 36, "5GHz", False)
        content = conf.read_text()
        assert "hw_mode=a" in content
        assert "channel=36" in content

    def test_write_hostapd_conf_hidden(self, tmp_path):
        from wlanspawn.backends.hostapd import _write_hostapd_conf
        conf = tmp_path / "hostapd.conf"
        _write_hostapd_conf(conf, "wlan1", "TestNet", "password1", 6, "2.4GHz", True)
        content = conf.read_text()
        assert "ignore_broadcast_ssid=1" in content

    def test_write_hostapd_conf_strong_encryption(self, tmp_path):
        from wlanspawn.backends.hostapd import _write_hostapd_conf
        conf = tmp_path / "hostapd.conf"
        _write_hostapd_conf(conf, "wlan1", "TestNet", "password1", 6, "2.4GHz", False)
        content = conf.read_text()
        # Ensure WPA2 with AES/CCMP (not weak TKIP)
        assert "wpa=2" in content  # WPA2 only
        assert "wpa_pairwise=CCMP" in content  # AES encryption
        assert "rsn_pairwise=CCMP" in content  # WPA2-AES
        assert "TKIP" not in content  # No weak TKIP encryption

    def test_write_dnsmasq_conf_contents(self, tmp_path):
        from wlanspawn.backends.hostapd import _write_dnsmasq_conf
        conf = tmp_path / "dnsmasq.conf"
        leases = tmp_path / "leases"
        _write_dnsmasq_conf(conf, "wlan1", "192.168.73.1",
                            "192.168.73.10", "192.168.73.100", leases, "8.8.8.8,1.1.1.1")
        content = conf.read_text()
        assert "interface=wlan1" in content
        assert "192.168.73.10,192.168.73.100" in content
        assert "server=8.8.8.8" in content
        assert "server=1.1.1.1" in content


class TestBackendFactory:
    def test_get_backend_explicit_nm(self, nm_config):
        from wlanspawn.backends import get_backend
        from wlanspawn.backends.networkmanager import NetworkManagerBackend
        with patch.object(NetworkManagerBackend, "is_available", return_value=True):
            b = get_backend(nm_config)
            assert isinstance(b, NetworkManagerBackend)

    def test_get_backend_unavailable_raises(self, nm_config):
        from wlanspawn.backends import get_backend
        from wlanspawn.backends.networkmanager import NetworkManagerBackend
        with patch.object(NetworkManagerBackend, "is_available", return_value=False):
            with pytest.raises(RuntimeError, match="not available"):
                get_backend(nm_config)
