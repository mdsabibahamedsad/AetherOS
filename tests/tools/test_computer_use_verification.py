"""Tests for computer_use action verification and failure recovery."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import pytest

from tools.computer_use.backend import ActionResult, CaptureResult, UIElement
from tools.computer_use.verification import (
    ElementNotFoundError,
    VerificationTimeoutError,
    find_element,
    find_text,
    retry_with_reobserve,
    verify_after_action,
    wait_for_element,
)


class MockBackend:
    """Minimal controllable ComputerUseBackend for verification tests."""

    def __init__(self):
        self.captures: List[CaptureResult] = []
        self.capture_count = 0
        self._elements_by_call: List[List[UIElement]] = []
        self._click_results: List[ActionResult] = []

    def set_capture_sequence(self, sequences):
        self._elements_by_call = list(sequences)

    def capture(self, mode="som", app=None):
        self.capture_count += 1
        if self._elements_by_call:
            elements = self._elements_by_call.pop(0)
        else:
            elements = []
        cap = CaptureResult(mode=mode, width=1024, height=768, png_b64=None,
                            elements=elements, app=app or "")
        self.captures.append(cap)
        return cap

    def click(self, **kw):
        res = self._click_results.pop(0) if self._click_results else ActionResult(ok=True, action="click")
        return res

    # unused interface methods
    def start(self): pass
    def stop(self): pass
    def is_available(self): return True
    def drag(self, **kw): return ActionResult(ok=True, action="drag")
    def scroll(self, **kw): return ActionResult(ok=True, action="scroll")
    def type_text(self, text): return ActionResult(ok=True, action="type_text")
    def key(self, keys): return ActionResult(ok=True, action="key")
    def list_apps(self): return []
    def focus_app(self, app, raise_window=False): return ActionResult(ok=True, action="focus_app")
    def set_value(self, value, element=None): return ActionResult(ok=True, action="set_value")


def _el(index, label="", role="AXButton"):
    return UIElement(index=index, role=role, label=label,
                     bounds=(10 * index, 10, 20, 20))


class TestFindElement:
    def test_find_by_label(self):
        b = MockBackend()
        b.set_capture_sequence([[_el(1, "Save"), _el(2, "Cancel")]])
        found = find_element(b, label="Save")
        assert found is not None
        assert found.label == "Save"

    def test_find_by_role(self):
        b = MockBackend()
        b.set_capture_sequence([[_el(1, "Save", "AXButton"), _el(2, "Name", "AXTextField")]])
        found = find_element(b, role="AXTextField")
        assert found is not None
        assert found.label == "Name"

    def test_no_match_returns_none(self):
        b = MockBackend()
        b.set_capture_sequence([[_el(1, "Save")]])
        assert find_element(b, label="Quit") is None

    def test_empty_capture_returns_none(self):
        b = MockBackend()
        b.set_capture_sequence([[]])
        assert find_element(b, label="Save") is None


class TestFindText:
    def test_label_match_fallback(self):
        b = MockBackend()
        b.set_capture_sequence([[_el(1, "Save Document"), _el(2, "Cancel")]])
        found = find_text(b, "Save")
        assert len(found) == 1
        assert found[0].label == "Save Document"

    def test_no_match_returns_empty(self):
        b = MockBackend()
        b.set_capture_sequence([[_el(1, "Save")]])
        assert find_text(b, "Export") == []


class TestWaitForElement:
    def test_element_appears(self):
        b = MockBackend()
        # First capture empty, second has the element.
        b.set_capture_sequence([[], [_el(1, "Save")]])
        el = wait_for_element(b, label="Save", timeout=2.0, interval=0.01)
        assert el.label == "Save"

    def test_times_out(self):
        b = MockBackend()
        b.set_capture_sequence([[]] * 50)
        with pytest.raises(ElementNotFoundError):
            wait_for_element(b, label="Save", timeout=0.1, interval=0.01)


class TestVerifyAfterAction:
    def test_predicate_confirms(self):
        b = MockBackend()
        b.set_capture_sequence([[ _el(1, "Save") ]])
        cap = verify_after_action(b, "click", predicate=lambda c: bool(c.elements),
                                  timeout=2.0, interval=0.01)
        assert cap.elements

    def test_expected_label_confirms(self):
        b = MockBackend()
        b.set_capture_sequence([[ _el(1, "Saved!") ]])
        cap = verify_after_action(b, "click", expected_label="Saved!",
                                  timeout=2.0, interval=0.01)
        assert cap.elements

    def test_timeout_raises(self):
        b = MockBackend()
        b.set_capture_sequence([[]] * 50)
        with pytest.raises(VerificationTimeoutError) as exc:
            verify_after_action(b, "click", expected_label="Never",
                                timeout=0.1, interval=0.01)
        assert exc.value.action == "click"


class TestRetryWithReobserve:
    def test_retries_failed_action(self):
        b = MockBackend()
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                return ActionResult(ok=False, action="click")
            return ActionResult(ok=True, action="click")

        res = retry_with_reobserve(b, flaky, action="click", max_retries=3, interval=0.01)
        assert res.ok is True
        assert calls["n"] == 3
        # Failed attempts trigger a re-observe.
        assert b.capture_count >= 2

    def test_returns_last_result_on_exhaustion(self):
        b = MockBackend()

        def always_fail():
            return ActionResult(ok=False, action="click")

        res = retry_with_reobserve(b, always_fail, action="click", max_retries=2, interval=0.01)
        assert res is None or res.ok is False

    def test_first_success_no_retry(self):
        b = MockBackend()
        calls = {"n": 0}

        def ok_first():
            calls["n"] += 1
            return ActionResult(ok=True, action="click")

        res = retry_with_reobserve(b, ok_first, action="click", max_retries=3, interval=0.01)
        assert res.ok is True
        assert calls["n"] == 1

    def test_json_string_ok_false_is_a_failure(self):
        """The tool layer feeds retry_with_reobserve JSON-string results; a
        payload reporting ok:false must count as a failure and be retried."""
        b = MockBackend()
        calls = {"n": 0}

        def flaky_json():
            calls["n"] += 1
            if calls["n"] == 1:
                return json.dumps({"ok": False, "action": "click"})
            return json.dumps({"ok": True, "action": "click"})

        res = retry_with_reobserve(b, flaky_json, action="click",
                                   max_retries=1, interval=0.01)
        assert json.loads(res)["ok"] is True
        assert calls["n"] == 2

    def test_json_string_ok_true_is_success(self):
        b = MockBackend()
        calls = {"n": 0}

        def ok_json():
            calls["n"] += 1
            return json.dumps({"ok": True, "action": "click"})

        res = retry_with_reobserve(b, ok_json, action="click",
                                   max_retries=3, interval=0.01)
        assert json.loads(res)["ok"] is True
        assert calls["n"] == 1

    def test_json_string_without_ok_key_is_success(self):
        """Validation errors carry no `ok` key — they must NOT be retried."""
        b = MockBackend()
        calls = {"n": 0}

        def validation_error():
            calls["n"] += 1
            return json.dumps({"error": "move_mouse requires coordinate"})

        res = retry_with_reobserve(b, validation_error, action="move_mouse",
                                   max_retries=3, interval=0.01)
        assert "error" in json.loads(res)
        assert calls["n"] == 1
