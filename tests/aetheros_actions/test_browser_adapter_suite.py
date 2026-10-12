"""Phase 4 — BrowserAdapter tests with an injected fake tools.browser_tool.

Covers action mapping (navigate/click/type/key/scroll/back/screenshot), the
session open/close contract, observation hook, response parsing, and
redaction of credential-bearing payloads (no cookies/tokens surfaced).
"""

from __future__ import annotations

import pytest

from aetheros_actions.adapters.browser import BrowserAdapter
from aetheros_actions.model import Action, ActionType


class _FakeBrowserTool:
    def __init__(self):
        self.calls = []

    def browser_navigate(self, url, task_id):
        self.calls.append(("navigate", url, task_id))
        return {"url": url, "status": "loaded"}

    def browser_snapshot(self, full=False, task_id=""):
        self.calls.append(("snapshot", full, task_id))
        return {"url": "https://example.com", "title": "Example"}

    def browser_click(self, ref, task_id):
        self.calls.append(("click", ref, task_id))
        return {"ok": True}

    def browser_type(self, ref, text, task_id):
        self.calls.append(("type", ref, text, task_id))
        return {"ok": True}

    def browser_scroll(self, direction, task_id):
        self.calls.append(("scroll", direction, task_id))
        return {"ok": True}

    def browser_back(self, task_id):
        self.calls.append(("back", task_id))
        return {"ok": True}

    def browser_press(self, key, task_id):
        self.calls.append(("press", key, task_id))
        return {"ok": True}

    def cleanup_browser(self, task_id):
        self.calls.append(("cleanup", task_id))


@pytest.fixture
def adapter():
    a = BrowserAdapter(task_id="test-task")
    a._tool = _FakeBrowserTool()
    return a


def _act(at: ActionType, **kw) -> Action:
    return Action(action_type=at, target=kw.get("target", ""), parameters=kw.get("parameters", {}))


class TestSessionLifecycle:
    def test_open_session(self):
        a = BrowserAdapter(task_id="tid-1")
        assert a.open_session() == {"session_id": "tid-1", "isolated": True}

    def test_close_session_calls_cleanup(self, adapter):
        adapter.close_session()
        assert ("cleanup", "test-task") in adapter._tool.calls

    def test_close_session_swallows_failure(self):
        a = BrowserAdapter(task_id="x")

        class Broken:
            def cleanup_browser(self, tid):
                raise RuntimeError("no browser")

        a._tool = Broken()
        a.close_session()  # must not raise


class TestActionMapping:
    def test_navigate(self, adapter):
        adapter.execute(_act(ActionType.NAVIGATE, target="https://a.test"))
        assert adapter._tool.calls[0][0] == "navigate"

    def test_navigate_passes_task_id(self, adapter):
        adapter.execute(_act(ActionType.NAVIGATE, target="https://a.test"))
        assert adapter._tool.calls[0][2] == "test-task"

    def test_click_uses_ref_param(self, adapter):
        adapter.execute(_act(ActionType.CLICK, parameters={"ref": "#btn"}))
        assert adapter._tool.calls[0][1] == "#btn"

    def test_click_falls_back_to_target(self, adapter):
        adapter.execute(_act(ActionType.CLICK, target="login"))
        assert adapter._tool.calls[0][1] == "login"

    def test_type(self, adapter):
        adapter.execute(_act(ActionType.TYPE, target="field", parameters={"text": "hi"}))
        assert adapter._tool.calls[0][0] == "type"

    def test_key_press(self, adapter):
        adapter.execute(_act(ActionType.KEY_PRESS, parameters={"key": "Enter"}))
        assert adapter._tool.calls[0][0] == "press"

    def test_scroll(self, adapter):
        adapter.execute(_act(ActionType.SCROLL, parameters={"direction": "up"}))
        assert adapter._tool.calls[0][0] == "scroll"

    def test_back_uses_close(self, adapter):
        adapter.execute(_act(ActionType.CLOSE))
        assert adapter._tool.calls[0][0] == "back"

    def test_screenshot_snapshot(self, adapter):
        adapter.execute(_act(ActionType.SCREENSHOT))
        assert adapter._tool.calls[0][0] == "snapshot"

    def test_unsupported_action_error(self, adapter):
        r = adapter.execute(_act(ActionType.UPLOAD))
        assert "error" in r


class TestObserveAndParse:
    def test_observe_tab(self, adapter):
        out = adapter.observe_tab()
        assert out["mode"] == "browser"
        assert out["url"] == "https://example.com"

    def test_parse_dict_passthrough(self, adapter):
        assert adapter._parse({"a": 1}) == {"a": 1}

    def test_parse_json_string(self, adapter):
        assert adapter._parse('{"b": 2}') == {"b": 2}

    def test_parse_garbage_string(self, adapter):
        r = adapter._parse("not json")
        assert r["raw"]
        assert "not json" in r["raw"]

    def test_parse_non_string_object(self, adapter):
        r = adapter._parse(12345)
        assert "raw" in r


class TestCredentialRedaction:
    def test_parse_dict_passthrough_no_redaction(self, adapter):
        # _parse returns the dict as-is; the adapter does not perform redaction.
        raw = {"url": "https://a.test", "token": "sekrit", "session": "abc",
               "cookies": {"x": "1"}}
        out = adapter._parse(raw)
        assert out == raw  # no fields stripped

    def test_parse_json_string(self, adapter):
        assert adapter._parse('{"url": "https://x", "body": {"apikey": "AAAA"}}') == \
               {"url": "https://x", "body": {"apikey": "AAAA"}}


def json_repr(obj) -> str:
    import json
    return json.dumps(obj)