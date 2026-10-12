"""Phase 2G — ActionVerifier tests: strategy resolution, no false successes.

Covers: achieved / not-achieved / ambiguous / delayed / UI-changed / timeout
shapes, unknown strategies, checker exceptions, NOT_REQUIRED passthrough, and
the passed() contract (only PASS and NOT_REQUIRED count as success).
"""

from __future__ import annotations

import pytest

from aetheros_actions.model import Action, ActionType, VerificationVerdict
from aetheros_actions.verifier import ActionVerifier, VerificationResult


def _act(strategy: str = "", expected: dict | None = None, at: ActionType = ActionType.CLICK) -> Action:
    return Action(
        action_type=at,
        target="t",
        verification_strategy=strategy,
        expected_result=expected or {},
    )


class TestVerifierStrategies:
    def test_achieved_passes(self):
        v = ActionVerifier(checkers={"element": lambda e: bool(e.get("element"))})
        res = v.verify(_act("element", {"element": "table"}))
        assert res.verdict is VerificationVerdict.PASS
        assert res.passed

    def test_not_achieved_fails(self):
        v = ActionVerifier(checkers={"element": lambda e: False})
        res = v.verify(_act("element", {"element": "table"}))
        assert res.verdict is VerificationVerdict.FAIL
        assert not res.passed

    def test_evidence_preserved(self):
        v = ActionVerifier(checkers={"url": lambda e: {"final": e.get("url")}})
        res = v.verify(_act("url", {"url": "https://x"}))
        assert res.verdict is VerificationVerdict.PASS
        assert res.evidence == {"final": "https://x"}

    def test_file_strategy(self):
        v = ActionVerifier(checkers={"file": lambda e: e.get("path") == "/tmp/out.txt"})
        res = v.verify(Action(action_type=ActionType.DOWNLOAD,
                              verification_strategy="file",
                              expected_result={"path": "/tmp/out.txt"}))
        assert res.verdict is VerificationVerdict.PASS

    def test_text_strategy(self):
        v = ActionVerifier(checkers={"text": lambda e: e.get("text") == "success"})
        assert v.verify(_act("text", {"text": "success"})).passed


class TestNoFalseSuccess:
    def test_ambiguous_empty_result_fails(self):
        # A checker that cannot confirm must not yield PASS.
        v = ActionVerifier(checkers={"element": lambda e: {}})
        assert v.verify(_act("element", {"element": "x"})).verdict is VerificationVerdict.FAIL

    def test_delayed_result_is_fail(self):
        # No polling: if the state is not there on first check, do not PASS.
        def delayed(e):
            return {"later": True} if False else False

        v = ActionVerifier(checkers={"element": delayed})
        assert v.verify(_act("element", {})).verdict is VerificationVerdict.FAIL

    def test_ui_changed_unexpectedly_fails(self):
        # UI drift surfaces as the expected element no longer matching.
        v = ActionVerifier(checkers={"element": lambda e: e.get("element") == "table"})
        assert v.verify(_act("element", {"element": "modal-overlay"})).verdict is VerificationVerdict.FAIL

    def test_checker_exception_fails(self):
        def boom(_e):
            raise RuntimeError("observation backend down")

        v = ActionVerifier(checkers={"element": boom})
        assert v.verify(_act("element", {})).verdict is VerificationVerdict.FAIL

    def test_unknown_strategy_unknown_not_pass(self):
        v = ActionVerifier()
        res = v.verify(_act("magic"))
        assert res.verdict is VerificationVerdict.UNKNOWN
        assert not res.passed

    def test_missing_strategy_default_not_required(self):
        v = ActionVerifier()
        res = v.verify(_act(""))
        assert res.verdict is VerificationVerdict.NOT_REQUIRED
        assert res.passed

    def test_screenshot_and_wait_not_required(self):
        v = ActionVerifier()
        for s in ("screenshot", "wait", "none"):
            assert v.verify(_act(s)).verdict is VerificationVerdict.NOT_REQUIRED


class TestVerificationResultContract:
    def test_passed_only_pass_and_not_required(self):
        for verdict in (VerificationVerdict.PASS, VerificationVerdict.NOT_REQUIRED):
            assert VerificationResult(verdict, _act()).passed
        for verdict in (VerificationVerdict.FAIL, VerificationVerdict.TIMEOUT,
                        VerificationVerdict.UNKNOWN):
            assert not VerificationResult(verdict, _act()).passed

    def test_to_dict_shape(self):
        res = VerificationResult(VerificationVerdict.FAIL, _act(), detail="nope")
        d = res.to_dict()
        assert d["verdict"] == "FAIL"
        assert d["detail"] == "nope"
        assert d["action"]["actionType"] == "CLICK"

    @pytest.mark.parametrize("strategy", ["   ", "none", None])
    def test_whitespace_none_strategy(self, strategy):
        a = Action(action_type=ActionType.CLICK, verification_strategy=strategy or "")
        v = ActionVerifier()
        assert v.verify(a).verdict is VerificationVerdict.NOT_REQUIRED