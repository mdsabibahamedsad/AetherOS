"""Tests for permission authorization, autonomy levels, and loop detection."""

from __future__ import annotations

import pytest

from aetheros_actions.loops import LoopDetector
from aetheros_actions.model import Action, ActionType, RiskLevel, TrustSource
from aetheros_actions.permissions import (
    AutonomyLevel,
    Decision,
    PermissionDecision,
    PermissionManager,
)
from aetheros_actions.risk import classify_action


def _click(risk=None, **kw):
    act = Action(
        action_type=ActionType.CLICK,
        target=kw.get("target", "dashboard button"),
        parameters=kw.get("parameters", {}),
        source=kw.get("source", TrustSource.AGENT_PLAN),
    )
    act.risk_level = risk or classify_action(act)
    return act


class TestPermissionManager:
    def test_low_risk_auto_allows_at_level2(self):
        pm = PermissionManager()
        d = pm.authorize(_click(risk=RiskLevel.LOW), AutonomyLevel.LOW_RISK_AUTO)
        assert d.decision is PermissionDecision.ALLOW

    def test_high_risk_requires_confirmation_at_level5(self):
        pm = PermissionManager()
        d = pm.authorize(_click(risk=RiskLevel.HIGH), AutonomyLevel.RESTRICTED_FULL)
        assert d.decision is PermissionDecision.REQUIRE_CONFIRMATION

    def test_high_risk_denied_without_callback(self):
        pm = PermissionManager()
        d = pm.authorize(_click(risk=RiskLevel.HIGH), AutonomyLevel.RESTRICTED_FULL)
        assert d.decision is PermissionDecision.REQUIRE_CONFIRMATION
        # No callback attached → resolving the confirmation fails closed to DENY.
        resolved = pm.confirm(d.action)
        assert resolved.decision is PermissionDecision.DENY

    def test_confirmed_high_risk_allowed(self):
        pm = PermissionManager(confirm_callback=lambda d: True)
        d = pm.authorize(_click(risk=RiskLevel.HIGH), AutonomyLevel.RESTRICTED_FULL)
        assert d.decision is PermissionDecision.REQUIRE_CONFIRMATION
        assert pm.confirm(d.action).decision is PermissionDecision.ALLOW

    def test_denied_confirmation(self):
        pm = PermissionManager(confirm_callback=lambda d: False)
        d = pm.authorize(_click(risk=RiskLevel.HIGH), AutonomyLevel.RESTRICTED_FULL)
        assert pm.confirm(d.action).decision is PermissionDecision.DENY

    def test_callback_exception_fails_closed(self):
        def boom(_d):
            raise RuntimeError("UI exploded")

        pm = PermissionManager(confirm_callback=boom)
        d = pm.authorize(_click(risk=RiskLevel.HIGH), AutonomyLevel.RESTRICTED_FULL)
        assert pm.confirm(d.action).decision is PermissionDecision.DENY

    def test_observe_only_level0(self):
        pm = PermissionManager()
        d = pm.authorize(_click(risk=RiskLevel.LOW), AutonomyLevel.OBSERVE_ONLY)
        assert d.decision is PermissionDecision.DENY

    def test_suggest_only_level1(self):
        pm = PermissionManager()
        d = pm.authorize(_click(risk=RiskLevel.LOW), AutonomyLevel.SUGGEST_ONLY)
        assert d.decision is PermissionDecision.DENY

    def test_medium_above_ceiling_at_level2(self):
        # Level 2 ceiling = MEDIUM → medium is allowed... but at LOW_RISK_AUTO
        # (level 2) any medium risk requires confirmation.
        pm = PermissionManager(confirm_callback=lambda d: True)
        d = pm.authorize(_click(risk=RiskLevel.MEDIUM), AutonomyLevel.LOW_RISK_AUTO)
        assert d.decision is PermissionDecision.REQUIRE_CONFIRMATION

    def test_medium_allowed_at_level3_with_callback(self):
        pm = PermissionManager(confirm_callback=lambda d: True)
        d = pm.authorize(_click(risk=RiskLevel.MEDIUM), AutonomyLevel.APPROVED_WORKFLOWS)
        assert d.decision is PermissionDecision.ALLOW

    def test_external_source_mutating_blocked(self):
        pm = PermissionManager()
        act = _click(risk=RiskLevel.MEDIUM, source=TrustSource.WEB_CONTENT)
        d = pm.authorize(act, AutonomyLevel.SAFE_AUTONOMOUS)
        assert d.decision is PermissionDecision.DENY
        assert "untrusted" in d.reason

    def test_executable_download_denied(self):
        pm = PermissionManager()
        act = Action(
            action_type=ActionType.DOWNLOAD,
            target="installer",
            parameters={"filename": "setup.exe"},
        )
        act.risk_level = classify_action(act)
        d = pm.authorize(act, AutonomyLevel.SAFE_AUTONOMOUS)
        assert d.decision is PermissionDecision.DENY

    def test_unsafe_path_blocked(self):
        pm = PermissionManager()
        act = Action(
            action_type=ActionType.FILE_SAVE,
            target="../../etc/passwd",
            parameters={"path": "../../etc/passwd"},
        )
        d = pm.authorize(act, AutonomyLevel.SAFE_AUTONOMOUS)
        assert d.decision is PermissionDecision.DENY


class TestLoopDetector:
    def test_repeated_same_action(self):
        ld = LoopDetector(repeat_threshold=3)
        for _ in range(3):
            ld.record(_click(risk=RiskLevel.LOW), failed=False)
        info = ld.detect()
        assert info is not None
        assert info.kind == "repeat"

    def test_repeated_failures(self):
        ld = LoopDetector(failure_threshold=3)
        for _ in range(3):
            ld.record(_click(risk=RiskLevel.LOW), failed=True)
        info = ld.detect()
        assert info is not None and info.kind == "repeated_failure"

    def test_oscillation_ab(self):
        ld = LoopDetector()
        a = _click(risk=RiskLevel.LOW, target="A")
        b = _click(risk=RiskLevel.LOW, target="B")
        for _ in range(8):
            ld.record(a, failed=False)
            ld.record(b, failed=False)
        info = ld.detect()
        assert info is not None and info.kind == "oscillation"

    def test_no_loop_normal(self):
        ld = LoopDetector(repeat_threshold=5)
        for i in range(5):
            ld.record(_click(risk=RiskLevel.LOW, target=f"btn{i}"), failed=False)
        assert ld.detect() is None