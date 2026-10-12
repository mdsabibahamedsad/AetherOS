"""Tests for the unified aetheros_actions model + risk + safety primitives."""

from __future__ import annotations

import pytest

from aetheros_actions.model import Action, ActionType, RiskLevel, TrustSource
from aetheros_actions.risk import allowed_max_risk, classify_action, risk_for_inputs
from aetheros_actions.safety import SafetyPolicy


class TestRiskClassification:
    def test_read_actions_are_low(self):
        assert risk_for_inputs(ActionType.SCREENSHOT) is RiskLevel.LOW
        assert risk_for_inputs(ActionType.WAIT) is RiskLevel.LOW
        assert risk_for_inputs(ActionType.SCROLL) is RiskLevel.LOW

    def test_typing_plain_text_is_medium(self):
        act = Action(action_type=ActionType.TYPE, target="note",
                     parameters={"text": "hello world"})
        assert classify_action(act) is RiskLevel.MEDIUM

    def test_payment_target_is_high(self):
        act = Action(action_type=ActionType.CLICK, target="checkout",
                     parameters={"coordinate": [100, 100]})
        assert classify_action(act) is RiskLevel.HIGH

    def test_security_settings_target_is_critical(self):
        act = Action(action_type=ActionType.CLICK,
                     target="security settings",
                     parameters={"coordinate": [100, 100]})
        assert classify_action(act) is RiskLevel.CRITICAL

    def test_transfer_is_critical(self):
        act = Action(action_type=ActionType.TYPE,
                     target="transfer to bob",
                     parameters={"text": "send money"})
        assert classify_action(act) is RiskLevel.CRITICAL

    def test_password_typing_is_critical(self):
        act = Action(action_type=ActionType.TYPE,
                     target="password field",
                     parameters={"text": "hunter2"})
        assert classify_action(act) is RiskLevel.CRITICAL

    def test_executable_download_is_high(self):
        act = Action(action_type=ActionType.DOWNLOAD,
                     target="installer",
                     parameters={"filename": "setup.exe"})
        assert classify_action(act) is RiskLevel.HIGH

    def test_plain_download_is_medium(self):
        act = Action(action_type=ActionType.DOWNLOAD,
                     target="report",
                     parameters={"filename": "report.pdf"})
        assert classify_action(act) is RiskLevel.MEDIUM

    def test_delete_is_high(self):
        act = Action(action_type=ActionType.CLICK,
                     target="delete file",
                     parameters={})
        assert classify_action(act) is RiskLevel.HIGH

    def test_navigate_is_medium(self):
        act = Action(action_type=ActionType.NAVIGATE,
                     target="https://example.com/report")
        assert classify_action(act) is RiskLevel.MEDIUM

    def test_autonomy_ceiling_map(self):
        assert allowed_max_risk(0) is RiskLevel.LOW
        assert allowed_max_risk(1) is RiskLevel.MEDIUM
        assert allowed_max_risk(2) is RiskLevel.MEDIUM
        assert allowed_max_risk(3) is RiskLevel.HIGH
        assert allowed_max_risk(5) is RiskLevel.HIGH


class TestSafetyPolicy:
    def test_executable_extensions(self):
        p = SafetyPolicy()
        assert p.is_executable("install.exe")
        assert p.is_executable("script.sh")
        assert not p.is_executable("report.pdf")
        assert p.is_executable("")  # unknown destination → unsafe

    def test_upload_confirmation_required_for_secrets(self):
        p = SafetyPolicy()
        assert p.upload_requires_confirmation("secrets.env", "site.com")
        assert p.upload_requires_confirmation("backup.zip", "site.com")
        assert not p.upload_requires_confirmation("report.pdf", "site.com")

    def test_clipboard_withheld_without_auth(self):
        p = SafetyPolicy()
        out = p.clipboard_text_for_model("secret-token-abc", authorized=False)
        assert "secret-token-abc" not in out
        assert p.clipboard_text_for_model("visible", authorized=True) == "visible"

    def test_password_masking(self):
        p = SafetyPolicy()
        assert p.mask_secret_input("hunter2") == "PASSWORD FIELD"

    def test_path_traversal_blocked(self):
        p = SafetyPolicy()
        assert not p.is_safe_path("../../etc/passwd")
        assert not p.is_safe_path("/etc/shadow")
        assert not p.is_safe_path("~/.ssh/id_rsa")
        assert not p.is_safe_path("")
        assert p.is_safe_path("/home/user/documents/report.txt")


class TestTrustSource:
    def test_external_detection(self):
        assert TrustSource.is_external(TrustSource.WEB_CONTENT)
        assert TrustSource.is_external(TrustSource.DOCUMENT_CONTENT)
        assert TrustSource.is_external(TrustSource.MODEL_OUTPUT)
        assert not TrustSource.is_external(TrustSource.USER_INSTRUCTION)
        assert not TrustSource.is_external(TrustSource.SECURITY_POLICY)

    def test_trust_ordering(self):
        assert TrustSource.USER_INSTRUCTION.outranks(TrustSource.WEB_CONTENT)
        assert TrustSource.SECURITY_POLICY.outranks(TrustSource.MODEL_OUTPUT)
        assert not TrustSource.WEB_CONTENT.outranks(TrustSource.SECURITY_POLICY)


class TestActionRecord:
    def test_full_record_fields(self):
        a = Action(
            action_type=ActionType.CLICK,
            target="login button",
            agent_id="agent-1",
            session_id="sess-1",
            reason="log in",
            expected_result={"element": "dashboard"},
            verification_strategy="element",
        )
        d = a.to_dict()
        assert d["actionId"]
        assert d["agentId"] == "agent-1"
        assert d["sessionId"] == "sess-1"
        assert d["actionType"] == "CLICK"
        assert d["riskLevel"] == "LOW"
        assert d["verificationStrategy"] == "element"
        assert d["expectedResult"] == {"element": "dashboard"}