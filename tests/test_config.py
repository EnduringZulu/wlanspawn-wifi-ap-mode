"""Tests for wlanspawn.config."""

import pytest
from pathlib import Path

from wlanspawn.config import (
    WlanspawnConfig,
    HotspotConfig,
    InterfacesConfig,
    NetworkConfig,
    BackendConfig,
    LoggingConfig,
    load_config,
    save_config,
    validate_config,
    _config_to_toml,
    default_config_path,
)


class TestDefaults:
    def test_default_hotspot(self):
        cfg = WlanspawnConfig()
        assert cfg.hotspot.ssid == "wlanspawn"
        assert len(cfg.hotspot.password) >= 8
        assert cfg.hotspot.band in ("2.4GHz", "5GHz")

    def test_default_interfaces_empty(self):
        cfg = WlanspawnConfig()
        assert cfg.interfaces.internet == ""
        assert cfg.interfaces.ap == ""

    def test_default_backend_auto(self):
        cfg = WlanspawnConfig()
        assert cfg.backend.type == "auto"

    def test_default_gateway(self):
        cfg = WlanspawnConfig()
        assert cfg.network.gateway.startswith("192.168.")


class TestValidation:
    def test_valid_config(self, minimal_config):
        errors = validate_config(minimal_config)
        assert errors == []

    def test_missing_internet_iface(self, minimal_config):
        minimal_config.interfaces.internet = ""
        errors = validate_config(minimal_config)
        assert any("internet" in e for e in errors)

    def test_missing_ap_iface(self, minimal_config):
        minimal_config.interfaces.ap = ""
        errors = validate_config(minimal_config)
        assert any("ap" in e for e in errors)

    def test_same_interfaces(self, minimal_config):
        minimal_config.interfaces.ap = minimal_config.interfaces.internet
        errors = validate_config(minimal_config)
        assert any("different" in e for e in errors)

    def test_short_password(self, minimal_config):
        minimal_config.hotspot.password = "short"
        errors = validate_config(minimal_config)
        assert any("password" in e for e in errors)

    def test_empty_ssid(self, minimal_config):
        minimal_config.hotspot.ssid = ""
        errors = validate_config(minimal_config)
        assert any("ssid" in e for e in errors)


class TestSaveLoad:
    def test_roundtrip(self, tmp_config_path, minimal_config):
        save_config(minimal_config, tmp_config_path)
        assert tmp_config_path.exists()

        loaded = load_config(tmp_config_path)
        assert loaded.hotspot.ssid == minimal_config.hotspot.ssid
        assert loaded.hotspot.password == minimal_config.hotspot.password
        assert loaded.interfaces.internet == minimal_config.interfaces.internet
        assert loaded.interfaces.ap == minimal_config.interfaces.ap

    def test_load_missing_returns_defaults(self, tmp_path):
        path = tmp_path / "nonexistent.toml"
        cfg = load_config(path)
        assert isinstance(cfg, WlanspawnConfig)
        assert cfg.hotspot.ssid == "wlanspawn"

    def test_save_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c" / "config.toml"
        cfg = WlanspawnConfig()
        save_config(cfg, deep_path)
        assert deep_path.exists()

    def test_toml_output_contains_sections(self, minimal_config):
        toml = _config_to_toml(minimal_config)
        assert "[hotspot]" in toml
        assert "[interfaces]" in toml
        assert "[network]" in toml
        assert "[backend]" in toml
        assert "[logging]" in toml

    def test_toml_bool_values(self):
        cfg = WlanspawnConfig()
        cfg.hotspot.hidden = True
        toml = _config_to_toml(cfg)
        assert "hidden = true" in toml

    def test_toml_escapes_special_chars(self):
        cfg = WlanspawnConfig()
        cfg.hotspot.password = 'pass"word'
        toml = _config_to_toml(cfg)
        # Should not contain unescaped double quote inside value
        assert 'password = "pass\\"word"' in toml

    def test_channel_persists(self, tmp_config_path, minimal_config):
        minimal_config.hotspot.channel = 11
        save_config(minimal_config, tmp_config_path)
        loaded = load_config(tmp_config_path)
        assert loaded.hotspot.channel == 11

    def test_band_persists(self, tmp_config_path, minimal_config):
        minimal_config.hotspot.band = "5GHz"
        save_config(minimal_config, tmp_config_path)
        loaded = load_config(tmp_config_path)
        assert loaded.hotspot.band == "5GHz"


class TestConfigPath:
    def test_default_path_is_absolute(self):
        p = default_config_path()
        assert p.is_absolute()

    def test_default_path_ends_toml(self):
        p = default_config_path()
        assert p.suffix == ".toml"
