"""Tests for wlanspawn.detector."""

import pytest
from unittest.mock import patch, MagicMock

from wlanspawn.detector import Detector
from wlanspawn.utils.system import OS, Distro


class TestDetector:
    def setup_method(self):
        self.det = Detector()

    def test_os_returns_os_enum(self):
        result = self.det.os()
        assert isinstance(result, OS)

    @patch("wlanspawn.utils.system.detect_os", return_value=OS.LINUX)
    @patch("wlanspawn.utils.system.detect_distro", return_value=(Distro.FEDORA, "Fedora Linux 40"))
    def test_fedora_detection(self, mock_distro, mock_os):
        det = Detector()
        det._sys = None  # Force re-detect
        # Just verify it doesn't raise
        assert det.distro_name() is not None

    @patch("wlanspawn.utils.network.list_interfaces", return_value=[])
    def test_wireless_interfaces_empty_list(self, mock_ifaces):
        result = self.det.wireless_interfaces()
        assert result == []

    @patch("wlanspawn.utils.system.cmd_exists")
    def test_suggest_backend_networkmanager(self, mock_exists):
        mock_exists.side_effect = lambda name: name == "nmcli"

        with patch("wlanspawn.utils.system.detect_os", return_value=OS.LINUX):
            with patch("wlanspawn.utils.system.run_output", return_value="active"):
                det = Detector()
                det._sys = MagicMock(os=OS.LINUX, distro=Distro.FEDORA,
                                     distro_name="Fedora", kernel="6.x", arch="x86_64", is_root=True)
                result = det.suggest_backend()
                assert result == "networkmanager"

    @patch("wlanspawn.utils.system.cmd_exists", return_value=False)
    def test_suggest_backend_no_tools(self, mock_exists):
        with patch("wlanspawn.utils.system.detect_os", return_value=OS.LINUX):
            det = Detector()
            det._sys = MagicMock(os=OS.LINUX, distro=Distro.GENERIC_LINUX,
                                 distro_name="Linux", kernel="5.x", arch="x86_64", is_root=False)
            # Should fall back gracefully
            result = det.suggest_backend()
            assert isinstance(result, str)

    def test_summary_returns_dict(self):
        with patch("wlanspawn.utils.network.list_interfaces", return_value=[]):
            summary = self.det.summary()
            assert "os" in summary
            assert "backend" in summary
            assert "wireless_ifaces" in summary
