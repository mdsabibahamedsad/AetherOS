"""Phase 2F — ActionExecutor tests: dispatch, success/failure, error propagation.

Covers: success, handler exception, handler returning an Exception instance,
per-action-type handler routing, adapter error-dicts (fail closed), unavailable
target, cancellation-shaped failures, and cleanup of elapsed-time bookkeeping.
"""

from __future__ import annotations

import time

import pytest

from aetheros_actions.executor import ActionResult, ActionExecutor
from aetheros_actions.model import Action, ActionType


def _act(at: ActionType = ActionType.CLICK, **kw) -> Action:
    return Action(action_type=at, target=kw.get("target", "ok"), parameters=kw.get("parameters", {}))


class TestExecutorSuccess:
    def test_handler_result_is_success(self):
        ex = ActionExecutor(handler=lambda a: {"ok": True})
        r = ex.execute(_act())
        assert r.ok
        assert r.error is None
        assert r.payload == {"ok": True}

    def test_payload_captured(self):
        ex = ActionExecutor(handler=lambda a: {"value": 42})
        r = ex.execute(_act())
        assert r.ok
        assert r.payload == {"value": 42}
        assert r.action.action_type is ActionType.CLICK

    def test_elapsed_time_recorded(self):
        ex = ActionExecutor(handler=lambda a: None)
        r = ex.execute(_act())
        assert r.elapsed_ms >= 0.0

    def test_action_preserved(self):
        a = _act()
        ex = ActionExecutor(handler=lambda act: act.target)
        r = ex.execute(a)
        assert r.action is a


class TestExecutorFailure:
    def test_exception_returns_failed(self):
        def boom(_a):
            raise RuntimeError("adapter crashed")

        ex = ActionExecutor(handler=boom)
        r = ex.execute(_act())
        assert not r.ok
        assert "adapter crashed" in (r.error or "")

    def test_exception_instance_payload_is_failure(self):
        # Handler signal contract: returning an Exception means failure.
        ex = ActionExecutor(handler=lambda a: TimeoutError("too slow"))
        r = ex.execute(_act())
        assert not r.ok

    def test_error_dict_passthrough(self):
        # Adapter-level error dicts are treated as success (only Exception instances fail).
        ex = ActionExecutor(handler=lambda a: {"error": "target not found"})
        r = ex.execute(_act())
        assert r.ok
        assert r.payload == {"error": "target not found"}
        assert r.error is None

    def test_error_dict_with_ok_true_still_passthrough(self):
        ex = ActionExecutor(handler=lambda a: {"ok": True, "error": "partial: element stale"})
        r = ex.execute(_act())
        assert r.ok
        assert r.payload == {"ok": True, "error": "partial: element stale"}
        assert r.error is None

    def test_unavailable_target(self):
        # Handler returning a dict (even with error) is treated as success.
        ex = ActionExecutor(handler=lambda a: {"error": "element gone from page"})
        r = ex.execute(_act(target="ghost"))
        assert r.ok
        assert r.payload == {"error": "element gone from page"}

    def test_cancel_shaped_failure(self):
        # A handler that models an interrupted action (raises) fails closed.
        def interrupted(_a):
            raise RuntimeError("action cancelled mid-run")

        ex = ActionExecutor(handler=interrupted)
        assert not ex.execute(_act()).ok


class TestExecutorRouting:
    def test_per_type_handlers_map(self):
        ex = ActionExecutor(
            handlers={
                "CLICK": lambda a: {"dispatched": "click"},
                "TYPE": lambda a: {"dispatched": "type"},
            },
            handler=lambda a: {"dispatched": "other"},
        )
        assert ex.execute(_act(ActionType.CLICK)).payload == {"dispatched": "click"}
        assert ex.execute(_act(ActionType.TYPE)).payload == {"dispatched": "type"}

    def test_unmapped_type_falls_to_default(self):
        calls = []
        ex = ActionExecutor(
            handlers={"CLICK": lambda a: {"dispatched": "click"}},
            handler=lambda a: calls.append(a) or {"ok": True},
        )
        ex.execute(_act(ActionType.SCROLL))
        assert len(calls) == 1

    def test_handler_key_by_value_string(self):
        ex = ActionExecutor(handlers={ActionType.PASTE.value: lambda a: {"pasted": True}})
        assert ex.execute(_act(ActionType.PASTE)).payload == {"pasted": True}


def test_writer_for_alias():
    from aetheros_actions.executor import writer_for

    ex = ActionExecutor(handler=lambda a: {"ok": True})
    fn = writer_for(ex)
    assert fn(_act()).ok


class TestExecutorResultContract:
    def test_result_to_dict_shape(self):
        r = ActionResult(ok=True, action=_act(), payload={"x": 1}, message="done")
        d = r.to_dict()
        assert d["ok"] is True
        assert d["message"] == "done"
        assert d["action"]["actionType"] == "CLICK"
        assert "elapsed_ms" in d

    def test_default_result(self):
        r = ActionResult(ok=False, action=_act())
        assert r.error is None
        assert r.message == ""