"""Phase 2A — Action model tests: schema, validation, serialization.

Covers the full closed vocabulary (every action kind), element/observation
serialization, Action.to_dict determinism + backwards-compatible camelCase
keys, missing/malformed parameters behavior, and the step-dict → Action
deserialization surface (the planner/manager contract).
"""

from __future__ import annotations

import time

import pytest

from aetheros_actions.model import (
    Action,
    ActionStatus,
    ActionType,
    Element,
    Observation,
    RiskLevel,
    TrustSource,
    VerificationVerdict,
)

ALL_ACTION_TYPES = [
    ActionType.CLICK, ActionType.DOUBLE_CLICK, ActionType.TYPE,
    ActionType.KEY_PRESS, ActionType.SCROLL, ActionType.MOVE, ActionType.DRAG,
    ActionType.OPEN, ActionType.CLOSE, ActionType.NAVIGATE, ActionType.UPLOAD,
    ActionType.DOWNLOAD, ActionType.COPY, ActionType.PASTE,
    ActionType.SCREENSHOT, ActionType.WAIT, ActionType.WINDOW_FOCUS,
    ActionType.TAB_SWITCH, ActionType.APP_LAUNCH, ActionType.APP_CLOSE,
    ActionType.FILE_OPEN, ActionType.FILE_SAVE,
]


class TestActionVocabulary:
    def test_closed_vocabulary(self):
        # Every documented action kind round-trips through the enum; every
        # member is one of the documented kinds (closed vocabulary invariant).
        for at in ALL_ACTION_TYPES:
            assert ActionType(at.value) is at
        assert all(ActionType(m) in ALL_ACTION_TYPES for m in ActionType)

    def test_value_equals_name_for_backcompat(self):
        for at in ALL_ACTION_TYPES:
            assert at.value == at.name

    def test_unknown_type_rejected(self):
        with pytest.raises(ValueError):
            ActionType("FLY")

    def test_required_field_action_type(self):
        with pytest.raises(TypeError):
            Action()  # action_type has no default

    def test_defaults(self):
        a = Action(action_type=ActionType.CLICK)
        assert a.target == ""
        assert a.parameters == {}
        assert a.risk_level is RiskLevel.LOW
        assert a.status is ActionStatus.PENDING
        assert a.action_id  # auto-generated
        assert "sessionId" in a.to_dict()
        assert "reversibility" in a.to_dict()
        assert "traceId" in a.to_dict()


class TestActionSerialization:
    def test_camelcase_keys(self):
        a = Action(action_type=ActionType.CLICK, target="x", agent_id="a", session_id="s",
                   reason="r", expected_result={"e": 1}, verification_strategy="element")
        d = a.to_dict()
        assert set(d) == {
            "actionId", "agentId", "sessionId", "actionType", "target",
            "parameters", "riskLevel", "permission", "reason", "timestamp",
            "expectedResult", "verificationStrategy", "source", "status",
            "reversibility", "dryRun", "idempotencyKey", "traceId",
        }

    def test_deterministic_serialization(self):
        a = Action(action_type=ActionType.TYPE, target="f", parameters={"text": "hi"},
                   risk_level=RiskLevel.MEDIUM)
        assert a.to_dict() == a.to_dict()

    def test_timestamp_appears(self):
        a = Action(action_type=ActionType.CLICK)
        assert isinstance(a.to_dict()["timestamp"], float)

    def test_source_and_status_serialize(self):
        a = Action(action_type=ActionType.CLICK, source=TrustSource.WEB_CONTENT,
                   status=ActionStatus.DENIED)
        d = a.to_dict()
        assert d["source"] == "WEB_CONTENT"
        assert d["status"] == "DENIED"

    def test_step_dict_surface(self):
        # Planner/manager accept step dicts with snake_case fields.
        step = {
            "action": "click", "target": "save", "parameters": {"button": "left"},
            "reason": "save draft", "expected_result": {"element": "saved"},
            "verification_strategy": "element", "agent_id": "ag", "session_id": "ss",
        }
        a = Action(
            action_type=ActionType(step["action"].upper()),
            target=step["target"],
            parameters=dict(step.get("parameters") or {}),
            reason=str(step.get("reason", "")),
            agent_id=step.get("agent_id", ""),
            session_id=step.get("session_id", ""),
            expected_result=dict(step.get("expected_result") or {}),
            verification_strategy=str(step.get("verification_strategy", "")),
        )
        assert a.action_type is ActionType.CLICK
        assert a.to_dict()["actionType"] == "CLICK"
        assert a.to_dict()["expectedResult"] == {"element": "saved"}


class TestRiskLevelOps:
    def test_ordering(self):
        assert RiskLevel.LOW < RiskLevel.MEDIUM < RiskLevel.HIGH < RiskLevel.CRITICAL
        assert RiskLevel.CRITICAL > RiskLevel.LOW
        assert RiskLevel.MEDIUM <= RiskLevel.MEDIUM
        assert RiskLevel.HIGH >= RiskLevel.MEDIUM

    def test_rank(self):
        assert RiskLevel.LOW.rank == 0
        assert RiskLevel.CRITICAL.rank == 3

    def test_enum_values(self):
        assert RiskLevel.HIGH.value == "HIGH"


class TestElementSerialization:
    def test_element_to_dict(self):
        e = Element(role="AXButton", label="OK", selector="#ok", index=2,
                    bounds=(1, 2, 3, 4), center=(3, 4), confidence=0.9, app="Test")
        d = e.to_dict()
        assert d["role"] == "AXButton"
        assert d["label"] == "OK"
        assert d["selector"] == "#ok"
        assert d["index"] == 2
        assert d["bounds"] == [1, 2, 3, 4]
        assert d["center"] == [3, 4]
        assert d["confidence"] == 0.9
        assert d["app"] == "Test"

    def test_element_center_none(self):
        d = Element(role="AXTextField", label="Name").to_dict()
        assert d["center"] is None
        assert d["index"] is None

    def test_element_defaults(self):
        e = Element()
        assert e.bounds == (0, 0, 0, 0)
        assert e.confidence == 0.0


class TestObservationSerialization:
    def test_summarize_contract(self):
        obs = Observation(screen_size=(800, 600), active_window_title="Win",
                          active_app="App", browser_url="https://x", mode="browser",
                          elements=[Element(label="a"), Element(label="b")],
                          visible_text="hello")
        s = obs.summarize()
        assert s["screen_size"] == [800, 600]
        assert s["active_window"] == "Win"
        assert s["active_app"] == "App"
        assert s["browser_url"] == "https://x"
        assert s["mode"] == "browser"
        assert s["element_count"] == 2
        assert s["visible_text_snippet"] == "hello"

    def test_visible_text_bounded_snippet(self):
        obs = Observation(visible_text="x" * 2000)
        assert len(obs.summarize()["visible_text_snippet"]) <= 500

    def test_observation_defaults(self):
        obs = Observation()
        assert obs.screen_size == (0, 0)
        assert obs.elements == []
        assert obs.mode == "desktop"


class TestEnums:
    def test_action_status_lifecycle_invariant(self):
        # Two discrete halves: pre-execution planning states vs outcome states.
        planning = {ActionStatus.PENDING, ActionStatus.AUTHORIZED,
                    ActionStatus.WAITING_CONFIRMATION, ActionStatus.EXECUTING,
                    ActionStatus.VERIFYING, ActionStatus.RECOVERING}
        outcomes = {ActionStatus.SUCCEEDED, ActionStatus.FAILED,
                    ActionStatus.CANCELLED, ActionStatus.DENIED}
        assert not planning & outcomes

    def test_verification_verdict_includes_fail_closed(self):
        assert VerificationVerdict.FAIL.value == "FAIL"
        assert VerificationVerdict.TIMEOUT.value == "TIMEOUT"

    def test_trust_source_lowest(self):
        assert TrustSource.lowest_trust() is TrustSource.MODEL_OUTPUT
        assert TrustSource.MODEL_OUTPUT.trust_rank() == 6
        assert TrustSource.USER_INSTRUCTION.trust_rank() == 0