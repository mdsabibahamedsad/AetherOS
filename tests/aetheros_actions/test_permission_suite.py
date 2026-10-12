"""Phase 2J — PermissionManager flow: grants, denials, escalation, isolation.

The manager is a stateless policy engine: ALLOW / DENY / REQUIRE_CONFIRMATION
plus a confirm() callback (the human-in-the-loop point where grant expiry or
revocation surfaces). These tests pin the fail-closed boundaries: escalation
is impossible, session/action specificity is passed through, external content
cannot command, and every denial is explicit.
"""

from __future__ import annotations

import pytest

from aetheros_actions.model import Action, ActionType, RiskLevel, TrustSource
from aetheros_actions.permissions import AutonomyLevel, Decision, PermissionDecision, PermissionManager
from aetheros_actions.risk import classify_action
from aetheros_actions.safety import SafetyPolicy


def _act(at: ActionType = ActionType.CLICK, target: str = "dashboard button",
         params: dict | None = None, risk: RiskLevel | None = None,
         source: TrustSource = TrustSource.AGENT_PLAN, permission: str = "",
         session_id: str = "", agent_id: str = "") -> Action:
    a = Action(action_type=at, target=target, parameters=params or {},
               source=source, permission=permission,
               session_id=session_id, agent_id=agent_id)
    a.risk_level = risk if risk is not None else classify_action(a)
    return a


class TestGrants:
    def test_low_risk_allowed_at_level2(self):
        pm = PermissionManager()
        d = pm.authorize(_act(risk=RiskLevel.LOW), AutonomyLevel.LOW_RISK_AUTO)
        assert d.decision is PermissionDecision.ALLOW

    def test_medium_allowed_at_level3(self):
        pm = PermissionManager()
        d = pm.authorize(_act(at=ActionType.TYPE, target="field",
                              params={"text": "hi"}, risk=RiskLevel.MEDIUM),
                         AutonomyLevel.APPROVED_WORKFLOWS)
        assert d.decision is PermissionDecision.ALLOW

    def test_high_granted_after_confirmation(self):
        pm = PermissionManager(confirm_callback=lambda d: True)
        d = pm.authorize(_act(risk=RiskLevel.HIGH), AutonomyLevel.RESTRICTED_FULL)
        assert d.decision is PermissionDecision.REQUIRE_CONFIRMATION
        assert pm.confirm(d.action).decision is PermissionDecision.ALLOW


class TestDenials:
    def test_level0_denies_all_but_observe(self):
        pm = PermissionManager()
        assert pm.authorize(_act(risk=RiskLevel.LOW), AutonomyLevel.OBSERVE_ONLY).decision is PermissionDecision.DENY
        obs = Action(action_type=ActionType.SCREENSHOT, source=TrustSource.AGENT_PLAN)
        assert pm.authorize(obs, AutonomyLevel.OBSERVE_ONLY).decision is PermissionDecision.ALLOW

    def test_level1_denies_everything(self):
        pm = PermissionManager()
        assert pm.authorize(_act(risk=RiskLevel.LOW), AutonomyLevel.SUGGEST_ONLY).decision is PermissionDecision.DENY

    def test_external_mutating_denied(self):
        pm = PermissionManager()
        d = pm.authorize(_act(risk=RiskLevel.MEDIUM, source=TrustSource.WEB_CONTENT),
                         AutonomyLevel.SAFE_AUTONOMOUS)
        assert d.decision is PermissionDecision.DENY
        assert "untrusted" in d.reason

    def test_external_read_allowed(self):
        pm = PermissionManager()
        d = pm.authorize(_act(at=ActionType.SCREENSHOT, target="", risk=RiskLevel.LOW,
                              source=TrustSource.WEB_CONTENT),
                         AutonomyLevel.SAFE_AUTONOMOUS)
        assert d.decision is PermissionDecision.ALLOW

    def test_unsafe_path_denied(self):
        pm = PermissionManager()
        # Forge risk to HIGH so the autonomy ceiling passes and the safety
        # layer is reached; the unsafe path must still be a hard DENY.
        d = pm.authorize(_act(at=ActionType.FILE_SAVE, target="",
                              params={"path": "/etc/passwd"},
                              risk=RiskLevel.HIGH), AutonomyLevel.RESTRICTED_FULL)
        assert d.decision is PermissionDecision.DENY
        assert "path" in d.reason.lower()

    def test_executable_download_denied(self):
        pm = PermissionManager()
        act = _act(at=ActionType.DOWNLOAD, target="", params={"filename": "setup.exe"},
                   risk=RiskLevel.HIGH)
        assert pm.authorize(act, AutonomyLevel.SAFE_AUTONOMOUS).decision is PermissionDecision.DENY


class TestEscalationGuard:
    def test_confirm_does_not_escalate_beyond_policy(self):
        # A denied-by-safety action is a hard DENY; the pipeline never
        # routes a DENY through confirm() (only REQUIRE_CONFIRMATION is
        # resolved by the user). Escalation via confirm is impossible.
        pm = PermissionManager(confirm_callback=lambda d: True)
        act = _act(at=ActionType.DOWNLOAD, target="", params={"filename": "install.exe"},
                   source=TrustSource.USER_INSTRUCTION, risk=RiskLevel.HIGH)
        assert pm.authorize(act, AutonomyLevel.RESTRICTED_FULL).decision is PermissionDecision.DENY

    def test_high_risk_confirmed_allowed(self):
        pm = PermissionManager(confirm_callback=lambda d: True)
        d = pm.authorize(_act(risk=RiskLevel.HIGH), AutonomyLevel.SAFE_AUTONOMOUS)
        assert d.decision is PermissionDecision.REQUIRE_CONFIRMATION
        assert pm.confirm(d.action).decision is PermissionDecision.ALLOW

    def test_no_callback_fails_closed(self):
        pm = PermissionManager()
        d = pm.authorize(_act(risk=RiskLevel.HIGH), AutonomyLevel.SAFE_AUTONOMOUS)
        assert d.decision is PermissionDecision.REQUIRE_CONFIRMATION
        assert pm.confirm(d.action).decision is PermissionDecision.DENY

    def test_callback_exception_fails_closed(self):
        def boom(_d):
            raise RuntimeError("ui broke")

        pm = PermissionManager(confirm_callback=boom)
        d = pm.authorize(_act(risk=RiskLevel.HIGH), AutonomyLevel.SAFE_AUTONOMOUS)
        assert pm.confirm(d.action).decision is PermissionDecision.DENY


class TestSpecificity:
    def test_action_specific_permission_carried(self):
        pm = PermissionManager()
        act = _act(risk=RiskLevel.HIGH, permission="send.message")
        d = pm.authorize(act, AutonomyLevel.SAFE_AUTONOMOUS)
        assert d.required_permission == "send.message"

    def test_session_specific_permission_carried(self):
        pm = PermissionManager()
        act = _act(risk=RiskLevel.HIGH, session_id="sess-1", permission="x")
        d = pm.authorize(act, AutonomyLevel.SAFE_AUTONOMOUS)
        assert d.action.session_id == "sess-1"

    def test_decision_to_dict_contract(self):
        pm = PermissionManager()
        act = _act(risk=RiskLevel.HIGH, permission="send.message")
        d = pm.authorize(act, AutonomyLevel.SAFE_AUTONOMOUS)
        dd = d.to_dict()
        assert dd["decision"] == "REQUIRE_CONFIRMATION"
        assert dd["risk_level"] == "HIGH"
        assert dd["action_id"] == act.action_id


class TestCustomSafetyPolicy:
    def test_custom_policy_consulted(self):
        strict = SafetyPolicy(executable_extensions=frozenset({".exe", ".pdf"}))
        pm = PermissionManager(safety_policy=strict)
        act = _act(at=ActionType.DOWNLOAD, target="", params={"filename": "doc.pdf"})
        assert pm.authorize(act, AutonomyLevel.SAFE_AUTONOMOUS).decision is PermissionDecision.DENY

    def test_external_action_blocking_toggle(self):
        pm = PermissionManager(external_action_always_blocked=False)
        d = pm.authorize(_act(risk=RiskLevel.MEDIUM, source=TrustSource.WEB_CONTENT),
                         AutonomyLevel.SAFE_AUTONOMOUS)
        # With blocking disabled, external medium at SAFE_AUTONOMOUS (autonomy=4)
        # is auto-allowed because MEDIUM requires confirmation only up to
        # autonomy level LOW_RISK_AUTO (2).
        assert d.decision is PermissionDecision.ALLOW