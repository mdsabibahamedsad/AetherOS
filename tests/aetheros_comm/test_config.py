"""Tests for aetheros_comm.config — communication config loading and defaults."""

from __future__ import annotations

import pytest

from aetheros_comm.config import (DEFAULT_COMMUNICATION_CONFIG,
                                  load_communication_config)


class TestDefaults:
    def test_protocol_versions_present(self):
        assert DEFAULT_COMMUNICATION_CONFIG["protocol_versions"] == ["1.0"]

    def test_message_limits_present(self):
        limits = DEFAULT_COMMUNICATION_CONFIG["message_limits"]
        assert limits["max_message_bytes"] > 0

    def test_timeouts_present(self):
        assert DEFAULT_COMMUNICATION_CONFIG["timeouts"]["request_default_seconds"] > 0

    def test_authentication_defaults(self):
        auth = DEFAULT_COMMUNICATION_CONFIG["authentication"]
        assert auth["require_signature"] is True

    def test_rate_limits_present(self):
        rl = DEFAULT_COMMUNICATION_CONFIG["rate_limits"]
        assert rl["messages_per_second"] > 0

    def test_broadcast_defaults(self):
        bc = DEFAULT_COMMUNICATION_CONFIG["broadcast"]
        assert "orchestrator" in bc["allowed_agents"]


class TestLoad:
    def test_load_returns_defaults(self):
        config = load_communication_config()
        assert config["protocol_versions"] == ["1.0"]

    def test_custom_overrides_default(self, tmp_path):
        import yaml
        override = {"rate_limits": {"messages_per_second": 7}}
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"communication": override}))
        config = load_communication_config(config_path=path)
        assert config["rate_limits"]["messages_per_second"] == 7
        # untouched defaults preserved
        assert config["message_limits"]["max_message_bytes"] > 0

    def test_deep_merge_preserves_siblings(self, tmp_path):
        import yaml
        override = {"retry": {"max_attempts": 9}}
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"communication": override}))
        config = load_communication_config(config_path=path)
        assert config["retry"]["max_attempts"] == 9
        assert config["retry"]["base_delay_seconds"] == 0.2


class TestMissingConfigFile:
    def test_missing_file_uses_defaults(self, tmp_path):
        config = load_communication_config(
            config_path=tmp_path / "nope.yaml")
        assert config["protocol_versions"] == ["1.0"]