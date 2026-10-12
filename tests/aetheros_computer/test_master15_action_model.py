"""Master 15: Universal Computer Action Model + Unified Approval Engine tests.

Behavior contracts (not snapshots):
- Canonical action registry keys ("<domain>.<short>") resolve to correct risk/verification.
- Hardline blocklist blocks unconditionally (rm -rf /), even at R0 declared risk.
- Dangerous terminal patterns gate approval; non-interactive context denies.
- Safe/read-only actions pass without approval.
- Execution plan derives max-risk + approval-required from step definitions.
- Form-field classification routes credential/financial/sensitive names correctly.
- Approval requests expire and never execute after expiry (Phase 56).
- Action metadata survives dict round-trip (audit persistence contract).
"""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ---------------------------------------------------------------------------
# Action registry (Phases 1-3)
# ---------------------------------------------------------------------------

class TestActionRegistry:
    def test_canonical_keys_exist(self):
        from aetheros_computer.action import ALL_ACTIONS

        assert "browser.navigate" in ALL_ACTIONS
        assert "desktop.click" in ALL_ACTIONS
        assert "terminal.execute" in ALL_ACTIONS
        assert "filesystem.read" in ALL_ACTIONS

    def test_risk_lookup_by_canonical_name(self):
        from aetheros_computer.action import RiskTier, get_action_risk

        assert get_action_risk("browser.snapshot") == RiskTier.R0_INFORMATIONAL
        assert get_action_risk("browser.click") == RiskTier.R2_MODERATE
        assert get_action_risk("browser.submit") == RiskTier.R3_HIGH
        assert get_action_risk("filesystem.delete") == RiskTier.R3_HIGH
        assert get_action_risk("terminal.sudo") == RiskTier.R3_HIGH

    def test_unknown_action_defaults_safe(self):
        from aetheros_computer.action import RiskTier, get_action_risk

        # Fail-safe: unknown action treated as informational by lookup,
        # gating happens at execution layer via dangerous-pattern scan.
        assert get_action_risk("browser.does_not_exist") == RiskTier.R0_INFORMATIONAL

    def test_verification_requirements(self):
        from aetheros_computer.action import VerificationRequirement, get_action_verification

        assert get_action_verification("browser.submit") == VerificationRequirement.DOMAIN_CONFIRMATION
        assert get_action_verification("filesystem.write") == VerificationRequirement.IDEMPOTENCY_CHECK
        assert get_action_verification("vision.capture") == VerificationRequirement.NONE


class TestActionMetadata:
    def test_dict_roundtrip(self):
        from aetheros_computer.action import ActionDomain, ActionMetadata, RiskTier

        md = ActionMetadata(
            action_type="browser.navigate",
            target="https://example.com",
            domain=ActionDomain.BROWSER,
            risk_level=RiskTier.R1_LOW,
            intent="open page",
        )
        rt = ActionMetadata.from_dict(md.to_dict())
        assert rt.action_type == md.action_type
        assert rt.domain == md.domain
        assert rt.risk_level == md.risk_level
        assert rt.target == md.target


class TestFieldClassification:
    def test_credential_fields(self):
        from aetheros_computer.action import FieldClassification, classify_field

        assert classify_field("password") == FieldClassification.CREDENTIAL
        assert classify_field("api_key") == FieldClassification.CREDENTIAL

    def test_financial_fields(self):
        from aetheros_computer.action import FieldClassification, classify_field

        assert classify_field("credit_card_number") == FieldClassification.FINANCIAL
        assert classify_field("routing_number") == FieldClassification.FINANCIAL

    def test_sensitive_and_public(self):
        from aetheros_computer.action import FieldClassification, classify_field

        assert classify_field("ssn") == FieldClassification.SENSITIVE
        assert classify_field("search_query") == FieldClassification.PUBLIC


# ---------------------------------------------------------------------------
# Unified approval engine (Phases 3-5, 54-57)
# ---------------------------------------------------------------------------

class TestHardlineBlocklist:
    def test_rm_rf_root_blocked_unconditionally(self):
        from aetheros_computer.approval import check_hardline_block

        assert check_hardline_block("sudo rm -rf /") is not None
        assert check_hardline_block("rm -rf /") is not None

    def test_benign_command_passes(self):
        from aetheros_computer.approval import check_hardline_block

        assert check_hardline_block("ls -la /tmp") is None

    def test_shutdown_blocked(self):
        from aetheros_computer.approval import check_hardline_block

        assert check_hardline_block("shutdown now") is not None


class TestDangerousPatterns:
    def test_service_control_detected(self):
        from aetheros_computer.approval import check_dangerous_pattern

        assert check_dangerous_pattern("systemctl stop nginx") is not None

    def test_force_push_detected(self):
        from aetheros_computer.approval import check_dangerous_pattern

        assert check_dangerous_pattern("git push --force origin main") is not None

    def test_normal_command_clean(self):
        from aetheros_computer.approval import check_dangerous_pattern

        assert check_dangerous_pattern("git status") is None


class TestApprovalEngineDecisions:
    def _engine(self):
        from aetheros_computer.approval import UnifiedApprovalEngine

        return UnifiedApprovalEngine({})

    def test_hardline_blocks_even_declared_low_risk(self):
        import aetheros_computer.action as act

        engine = self._engine()
        ok, reason = engine.check_and_request_approval(
            act.ActionMetadata(
                domain=act.ActionDomain.TERMINAL,
                action_type="terminal.execute",
                target="rm -rf /",
                risk_level=act.RiskTier.R0_INFORMATIONAL,
            ),
            session_key="s1",
        )
        assert ok is False
        assert "Hardline" in reason

    def test_read_only_action_allowed_without_approval(self):
        import aetheros_computer.action as act

        engine = self._engine()
        ok, _ = engine.check_and_request_approval(
            act.ActionMetadata(
                domain=act.ActionDomain.BROWSER,
                action_type="browser.snapshot",
                risk_level=act.RiskTier.R0_INFORMATIONAL,
            ),
            session_key="s1",
        )
        assert ok is True

    def test_high_risk_denied_in_non_interactive_context(self):
        """No gateway, no CLI -> fail-closed deny (never silent-execute)."""
        import aetheros_computer.action as act

        engine = self._engine()
        ok, reason = engine.check_and_request_approval(
            act.ActionMetadata(
                domain=act.ActionDomain.DESKTOP,
                action_type="desktop.close_app",
                target="Terminal",
                risk_level=act.RiskTier.R3_HIGH,
            ),
            session_key="s1",
        )
        assert ok is False
        assert "no interactive context" in reason.lower()

    def test_gateway_approval_flow_approves(self):
        import aetheros_computer.action as act
        from aetheros_computer.approval import ApprovalState

        engine = self._engine()

        captured = {}

        def fake_notify(session_key, payload):
            captured["session"] = session_key
            captured["payload"] = payload

        engine.set_gateway_notify(fake_notify)
        # Force gateway-context path
        engine._is_gateway_context = lambda: True

        ok, reason = engine.check_and_request_approval(
            act.ActionMetadata(
                domain=act.ActionDomain.BROWSER,
                action_type="browser.submit",
                target="https://shop.example/checkout",
                risk_level=act.RiskTier.R3_HIGH,
            ),
            session_key="gw1",
            wait=False,
        )
        # Queued immediately: not executed, request id surfaced
        assert ok is False
        assert reason.startswith("PENDING:")
        # Should be queued, not executed yet
        pending = engine.get_pending_approvals("gw1")
        assert len(pending) == 1
        request_id = pending[0].request_id
        assert captured["payload"]["action"] == "browser.submit"

        resolved = engine.resolve_gateway_approval(request_id, approve=True)
        assert resolved is True
        # Session-scoped: same action now pre-approved
        ok2, _ = engine.check_and_request_approval(
            act.ActionMetadata(
                domain=act.ActionDomain.BROWSER,
                action_type="browser.submit",
                target="https://other.example/x",
                risk_level=act.RiskTier.R3_HIGH,
            ),
            session_key="gw1",
        )
        assert ok2 is True

    def test_expired_approval_never_executes(self):
        """Phase 56: expired approvals resolve to denied."""
        import aetheros_computer.action as act
        from aetheros_computer.approval import ApprovalState

        engine = self._engine()
        engine._approval_timeout = 0.05
        engine._is_gateway_context = lambda: True
        engine.set_gateway_notify(lambda *a: None)

        engine.check_and_request_approval(
            act.ActionMetadata(
                domain=act.ActionDomain.BROWSER,
                action_type="browser.submit",
                target="https://x.example",
                risk_level=act.RiskTier.R3_HIGH,
            ),
            session_key="exp1",
            wait=False,
        )
        rid = engine.get_pending_approvals("exp1")[0].request_id
        time.sleep(0.08)

        # Late resolution must be refused
        assert engine.resolve_gateway_approval(rid, approve=True) is False

        removed = engine.cleanup_expired()
        assert removed >= 1
        # Swept out of pending map entirely
        assert rid not in engine._pending

    def test_yolo_mode_auto_allows_with_session_scope(self):
        import aetheros_computer.action as act

        engine = self._engine()
        engine.set_session_yolo("y1", True)
        ok, _ = engine.check_and_request_approval(
            act.ActionMetadata(
                domain=act.ActionDomain.DESKTOP,
                action_type="desktop.close_app",
                target="X",
                risk_level=act.RiskTier.R3_HIGH,
            ),
            session_key="y1",
        )
        assert ok is True
        # But hardline still wins over yolo
        ok2, why2 = engine.check_and_request_approval(
            act.ActionMetadata(
                domain=act.ActionDomain.TERMINAL,
                action_type="terminal.execute",
                target="mkfs.ext4 /dev/sda1",
                risk_level=act.RiskTier.R3_HIGH,
            ),
            session_key="y1",
        )
        assert ok2 is False


class TestExecutionPlan:
    def test_plan_derives_max_risk_and_approval(self):
        from aetheros_computer.approval import build_execution_plan

        plan = build_execution_plan("Publish report", [
            {"action": "browser.navigate", "intent": "open console", "target": "https://x", "estimated_time": 5},
            {"action": "browser.submit", "intent": "publish", "target": "#submit", "estimated_time": 10},
        ])
        assert len(plan.steps) == 2
        assert plan.approval_required is True
        assert plan.max_risk == "R3_HIGH"
        assert plan.steps[1].requires_approval is True
        assert plan.total_estimated_time == 15.0

    def test_preview_is_ascii_safe(self):
        """Windows cp1252 consoles crash on emoji — preview must stay ASCII."""
        from aetheros_computer.approval import build_execution_plan

        plan = build_execution_plan("Risky task", [
            {"action": "terminal.sudo", "intent": "elevated op", "target": "apt install x"},
        ])
        text = plan.to_user_preview()
        text.encode("cp1252")  # raises if any non-latin1 char present
        assert "APPROVAL REQUIRED" in text


class TestSubmissionConfirmation:
    def test_sensitive_submission_flags_consequence(self):
        import aetheros_computer.action as act
        from aetheros_computer.approval import UnifiedApprovalEngine

        engine = UnifiedApprovalEngine({})
        md = act.ActionMetadata(
            action_type="browser.submit",
            target="https://pay.example/card",
            risk_level=act.RiskTier.R3_HIGH,
        )
        summary = engine.create_submission_confirmation(
            md,
            form_data={"card_number": "4111111111111111", "name": "Test User"},
            account="user@x",
            destination="https://pay.example/card",
        )
        assert "SENSITIVE" in summary.consequence.upper()
        msg = summary.to_user_message()
        msg.encode("cp1252")  # ascii-safe for consoles
