"""Tests for aetheros_security policy, sandbox, privacy, network, supply_chain, threat."""

import os
import tempfile

import pytest

from aetheros_security.policy import PolicyManager
from aetheros_security.privacy import PrivacyManager
from aetheros_security.network import NetworkSecurityManager
from aetheros_security.supply_chain import SupplyChainManager
from aetheros_security.threat import ThreatDetector


class TestPolicy:
    def test_load_and_check_deny_by_default(self, tmp_path):
        policy = {
            "version": 1,
            "permissions": {
                "filesystem": {"read": True, "write": True},
                "terminal": {"execute": False},
            },
        }
        pm = PolicyManager()
        pm.load_policy("test", policy)
        assert pm.check_permission("test", "filesystem:read")
        assert pm.check_permission("test", "filesystem:write")
        assert not pm.check_permission("test", "terminal:execute")
        # Deny-by-default for unspecified category/action.
        assert not pm.check_permission("test", "network:connect")

    def test_default_policy_fallback(self):
        pm = PolicyManager()
        pm.load_policy("default", {"version": 1, "permissions": {"api": {"access": True}}})
        # Unknown policy name falls back to default.
        assert pm.check_permission("other-workspace", "api:access")

    def test_rejects_unknown_category(self):
        pm = PolicyManager()
        with pytest.raises(Exception):
            pm.load_policy("bad", {"version": 1, "permissions": {"nonsense": {"x": True}}})

    def test_load_from_yaml_file(self, tmp_path):
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(
            "version: 1\npermissions:\n  git:\n    read: true\n    push: false\n"
        )
        pm = PolicyManager()
        pm.load_policy("yaml", str(policy_file))
        assert pm.check_permission("yaml", "git:read")
        assert not pm.check_permission("yaml", "git:push")


class TestPrivacy:
    def test_all_opt_in_disabled_by_default(self, tmp_path):
        pm = PrivacyManager(settings_file=str(tmp_path / "privacy.json"))
        assert not pm.telemetry_allowed()
        assert not pm.diagnostics_allowed()
        assert not pm.crash_report_allowed()

    def test_offline_mode_blocks_egress(self, tmp_path):
        pm = PrivacyManager(settings_file=str(tmp_path / "privacy.json"))
        pm.set_offline_mode(True)
        assert pm.is_offline_mode()
        pm.set_telemetry_consent(True)  # consent is remembered but...
        assert pm.telemetry_allowed() == (not pm.is_offline_mode())

    def test_consent_persistence(self, tmp_path):
        path = tmp_path / "privacy.json"
        pm = PrivacyManager(settings_file=str(path))
        pm.set_telemetry_consent(True)
        pm2 = PrivacyManager(settings_file=str(path))
        assert pm2.telemetry_allowed()

    def test_mask_pii(self, tmp_path):
        pm = PrivacyManager(settings_file=str(tmp_path / "privacy.json"))
        text = "Contact alice@example.com or call 555-123-4567"
        masked = pm.mask_text(text)
        assert "alice@example.com" not in masked
        assert "555-123-4567" not in masked

    def test_export_data(self, tmp_path):
        pm = PrivacyManager(settings_file=str(tmp_path / "privacy.json"))
        pm.set_offline_mode(True)
        exported = pm.export_data(tmp_path / "export")
        assert exported.exists()


class TestNetworkSecurity:
    def test_allow_deny_host(self):
        nm = NetworkSecurityManager()
        nm.set_allowlist(["trusted.example.com"])
        assert nm.check_host("trusted.example.com").allowed
        assert not nm.check_host("evil.example.com").allowed

    def test_denylist_wins(self):
        nm = NetworkSecurityManager()
        nm.set_denylist(["blocked.example.com"])
        assert not nm.check_host("blocked.example.com").allowed
        assert nm.check_host("ok.example.com").allowed

    def test_block_private_ranges(self):
        nm = NetworkSecurityManager()
        nm.set_block_private_ranges(True)
        assert not nm.check_host("192.168.1.10").allowed
        assert not nm.check_host("10.0.0.5").allowed
        assert nm.check_host("93.184.216.34").allowed

    def test_port_policy(self):
        nm = NetworkSecurityManager()
        nm.set_port_allowlist([443, 80])
        assert nm.check_port(443).allowed
        assert not nm.check_port(22).allowed

    def test_connection_check(self):
        nm = NetworkSecurityManager()
        nm.set_block_private_ranges(True)
        assert nm.check_connection("example.com", 443).allowed
        assert not nm.check_connection("192.168.1.1", 8080).allowed

    def test_dns_check(self):
        nm = NetworkSecurityManager()
        nm.set_denylist(["bad.org"])
        assert not nm.check_dns("bad.org").allowed
        assert nm.check_dns("good.org").allowed


class TestSupplyChain:
    def test_sbom_generated(self):
        scm = SupplyChainManager()
        sbom = scm.generate_sbom()
        assert "bomFormat" in sbom
        assert sbom["bomFormat"] == "CycloneDX"
        assert isinstance(sbom.get("components"), list)
        # cryptography must be a listed dependency.
        names = [c["name"] for c in sbom["components"]]
        assert "cryptography" in names

    def test_signature_verification_accepts_sha256(self, tmp_path):
        import hashlib
        scm = SupplyChainManager()
        artifact = tmp_path / "artifact.bin"
        artifact.write_bytes(b"content")
        digest = hashlib.sha256(b"content").hexdigest()
        assert scm.verify_signature(str(artifact), f"sha256:{digest}")
        bad_digest = hashlib.sha256(b"tampered").hexdigest()
        assert not scm.verify_signature(str(artifact), f"sha256:{bad_digest}")

    def test_signature_rejects_unsupported_format(self, tmp_path):
        scm = SupplyChainManager()
        artifact = tmp_path / "artifact.bin"
        artifact.write_bytes(b"content")
        with pytest.raises(Exception):
            scm.verify_signature(str(artifact), "not-a-signature")


class TestThreat:
    def test_alerts_on_threshold_override(self):
        td = ThreatDetector()
        alerts = td._check_excessive_resources()
        assert isinstance(alerts, list)

    def test_record_and_analyze(self):
        td = ThreatDetector()
        td.record_activity(activity_type="auth.failed", source="192.168.1.10")
        alerts = td.analyze_activity()
        assert isinstance(alerts, list)


class TestSecurityManager:
    def test_diagnostics_and_recovery(self):
        from aetheros_security import SecurityManager
        sm = SecurityManager()
        sm.initialize()
        diag = sm.run_diagnostics()
        assert isinstance(diag, dict)
        rec = sm.recover("secrets")
        assert isinstance(rec, dict)
