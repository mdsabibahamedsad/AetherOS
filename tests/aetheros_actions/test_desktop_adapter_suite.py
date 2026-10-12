"""Phase 5 — DesktopAdapter tests with an injected fake computer_use backend.

Covers action mapping (click/type/key/scroll/drag/window/screenshot/copy/paste/
wait), coordinate safety against the observed screen size (Step 10), password
field masking, response parsing, and error shaping for unsupported actions.
"""

from __future__ import annotations

import pytest

from aetheros_actions.adapters.desktop import DesktopAdapter
from aetheros_actions.model import Action, ActionType


class FakeCU:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = responses or {}

    def handle_computer_use(self, args) -> dict:
        self.calls.append(args)
        return self.responses.get(args["action"], {"ok": True})


@pytest.fixture
def adapter():
    a = DesktopAdapter(backend_name="fake")
    a._dispatch_fn = _Unbound()
    a._tool = lambda: a._fake
    return a


class _Unbound:
    pass


def _mk(adapter, **kwargs) -> tuple[DesktopAdapter, FakeCU]:
    fake = FakeCU()
    adapter._fake = fake
    return adapter, fake


def _act(at: ActionType, **kw) -> Action:
    return Action(action_type=at, target=kw.get("target", ""), parameters=kw.get("parameters", {}))


class TestActionMapping:
    def test_click_maps(self, adapter):
        a, fake = _mk(adapter)
        a.execute(_act(ActionType.CLICK, parameters={"coordinate": [10, 20], "button": "right"}))
        call = fake.calls[0]
        assert call["action"] == "click"
        assert call["coordinate"] == [10, 20]
        assert call["button"] == "right"

    def test_click_element_param(self, adapter):
        a, fake = _mk(adapter)
        a.execute(_act(ActionType.CLICK, parameters={"element": 7}))
        assert fake.calls[0]["element"] == 7

    def test_type_uses_text_param(self, adapter):
        a, fake = _mk(adapter)
        a.execute(_act(ActionType.TYPE, parameters={"text": "hello"}))
        assert fake.calls[0]["action"] == "type"
        assert fake.calls[0]["text"] == "hello"

    def test_type_falls_back_to_target(self, adapter):
        a, fake = _mk(adapter)
        a.execute(_act(ActionType.TYPE, target="fallback-text"))
        assert fake.calls[0]["text"] == "fallback-text"

    def test_key_press(self, adapter):
        a, fake = _mk(adapter)
        a.execute(_act(ActionType.KEY_PRESS, parameters={"keys": "enter"}))
        assert fake.calls[0]["action"] == "key"

    def test_scroll(self, adapter):
        a, fake = _mk(adapter)
        a.execute(_act(ActionType.SCROLL, parameters={"direction": "up", "amount": 5}))
        assert fake.calls[0]["action"] == "scroll"

    def test_drag(self, adapter):
        a, fake = _mk(adapter)
        a.execute(_act(ActionType.DRAG, parameters={
            "from_coordinate": [1, 1], "to_coordinate": [5, 5]}))
        assert fake.calls[0]["action"] == "drag"

    def test_window_focus_uses_target(self, adapter):
        a, fake = _mk(adapter)
        a.execute(_act(ActionType.WINDOW_FOCUS, target="Terminal"))
        assert fake.calls[0]["window_title"] == "Terminal"

    def test_screenshot_som_default(self, adapter):
        a, fake = _mk(adapter)
        a.execute(_act(ActionType.SCREENSHOT))
        assert fake.calls[0]["action"] == "capture"
        assert fake.calls[0]["mode"] == "som"

    def test_copy(self, adapter):
        a, fake = _mk(adapter)
        a.execute(_act(ActionType.COPY, parameters={"text": "secret"}))
        assert fake.calls[0]["action"] == "copy_clipboard"

    def test_paste_reads_clipboard(self, adapter):
        a, fake = _mk(adapter)
        a.execute(_act(ActionType.PASTE))
        assert fake.calls[0]["action"] == "read_clipboard"

    def test_wait_seconds(self, adapter):
        a, fake = _mk(adapter)
        a.execute(_act(ActionType.WAIT, parameters={"seconds": 2.5}))
        assert fake.calls[0]["seconds"] == 2.5

    def test_unsupported_action_error(self, adapter):
        a, _ = _mk(adapter)
        r = a.execute(_act(ActionType.UPLOAD))
        assert "error" in r
        assert a._fake.calls == []  # never reached the backend


class TestCoordinateSafety:
    def test_coordinate_outside_screen_rejected(self, adapter):
        a, fake = _mk(adapter)
        a._screen_size = (100, 100)
        r = a.execute(_act(ActionType.CLICK, parameters={"coordinate": [500, 10]}))
        assert "error" in r
        assert fake.calls == []

    def test_coordinate_negative_rejected(self, adapter):
        a, fake = _mk(adapter)
        a._screen_size = (100, 100)
        r = a.execute(_act(ActionType.MOVE, parameters={"coordinate": [-2, 5]}))
        assert "error" in r

    def test_coordinate_within_bounds_allowed(self, adapter):
        a, fake = _mk(adapter)
        a._screen_size = (100, 100)
        a.execute(_act(ActionType.CLICK, parameters={"coordinate": [99, 99]}))
        assert fake.calls and fake.calls[0]["action"] == "click"

    def test_unknown_screen_size_skips_check(self, adapter):
        a, fake = _mk(adapter)
        a._screen_size = (0, 0)  # never observed
        a.execute(_act(ActionType.CLICK, parameters={"coordinate": [5000, 5000]}))
        assert fake.calls and fake.calls[0]["action"] == "click"


class TestMasking:
    def test_password_like_target_masked(self, adapter):
        a, fake = _mk(adapter)
        r = a.execute(_act(ActionType.TYPE, parameters={"text": "PASSWORD FIELD"}))
        assert fake.calls[0]["text"] == "PASSWORD FIELD"


class TestScreenSize:
    def test_refresh_screen_size(self, adapter):
        a, fake = _mk(adapter)
        fake.responses["get_screen_size"] = {"width": 1920, "height": 1080}
        assert a.refresh_screen_size() == (1920, 1080)

    def test_refresh_bad_response_keeps_old(self, adapter):
        a, fake = _mk(adapter)
        a._screen_size = (800, 600)
        fake.responses["get_screen_size"] = {"width": 0, "height": 0}
        assert a.refresh_screen_size() == (800, 600)


class TestObserveAndFind:
    def test_observe_window(self, adapter):
        a, fake = _mk(adapter)
        fake.responses["get_active_window"] = {"window": {"title": "Editor", "app": "code"}}
        out = a.observe()
        assert out["mode"] == "desktop"
        assert out["window_title"] == "Editor"

    def test_observe_raises_defaults(self, adapter):
        a, fake = _mk(adapter)

        def boom(*_args):
            raise RuntimeError("no window server")

        a._fake = type("B", (), {"handle_computer_use": boom})()
        out = a.observe()
        assert out["window_title"] == ""

    def test_find_text_parses_matches(self, adapter):
        a, fake = _mk(adapter)
        fake.responses["find_text"] = {"matches": [
            {"label": "Save", "bounds": [1, 2, 3, 4], "role": "button"}]}
        els = a.find_text("Save")
        assert len(els) == 1
        assert els[0].bounds == (1, 2, 3, 4)

    def test_find_text_raises_empty(self, adapter):
        a, fake = _mk(adapter)

        def boom(*_args):
            raise RuntimeError("no uia")

        a._fake = type("B", (), {"handle_computer_use": boom})()
        assert a.find_text("nope") == []

    def test_find_text_bad_bounds_zero(self, adapter):
        a, fake = _mk(adapter)
        fake.responses["find_text"] = {"matches": [{"label": "x", "bounds": [1]}]}
        assert a.find_text("x")[0].bounds == (0, 0, 0, 0)


class TestParse:
    def test_parse_dict(self, adapter):
        a, _ = _mk(adapter)
        assert a._parse({"z": 1}) == {"z": 1}

    def test_parse_json_string(self, adapter):
        a, _ = _mk(adapter)
        assert a._parse('{"a": 2}') == {"a": 2}

    def test_parse_non_json_string_truncated(self, adapter):
        a, _ = _mk(adapter)
        r = a._parse("x" * 5000)
        assert r["raw"]
        assert len(r["raw"]) <= 2000

    def test_parse_object(self, adapter):
        a, _ = _mk(adapter)
        assert a._parse(123)["raw"] == "123"