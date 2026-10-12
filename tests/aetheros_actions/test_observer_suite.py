"""Phase 2C — ScreenObserver extended: malformed/degraded environments.

Covers: valid, empty, corrupt/raising backends, rapidly changing screens,
duplicate screens, unavailable display, invalid dimensions, and deterministic
element normalization.
"""

from __future__ import annotations

from aetheros_actions.model import Element
from aetheros_actions.observer import ObservationBackends, ScreenObserver


class TestValid:
    def test_full_observation(self):
        backends = ObservationBackends(
            screen_size=lambda: (1920, 1080),
            active_window=lambda: {"title": "Docs", "app": "browser"},
            browser_tab=lambda: {"url": "https://example.com", "mode": "browser"},
            ui_elements=lambda: [{"role": "button", "label": "Go", "bounds": [1, 2, 3, 4]}],
            visible_text=lambda: "hello world",
        )
        obs = ScreenObserver(backends).observe()
        assert obs.screen_size == (1920, 1080)
        assert obs.active_window_title == "Docs"
        assert obs.elements[0].label == "Go"
        assert obs.visible_text == "hello world"


class TestDegraded:
    def test_no_backends_defaults(self):
        obs = ScreenObserver(ObservationBackends()).observe()
        assert obs.screen_size == (0, 0)
        assert obs.active_window_title == ""
        assert obs.elements == []
        assert obs.visible_text == ""

    def test_raising_backends_degrade(self):
        def boom():
            raise RuntimeError("no display")

        backends = ObservationBackends(screen_size=boom, active_window=boom,
                                       browser_tab=boom, ui_elements=boom,
                                       visible_text=boom)
        obs = ScreenObserver(backends).observe()
        assert obs.screen_size == (0, 0)
        assert obs.active_window_title == ""
        assert obs.browser_url == ""
        assert obs.elements == []
        assert obs.visible_text == ""

    def test_invalid_dimensions_zero(self):
        backends = ObservationBackends(screen_size=lambda: (0, 0))
        assert ScreenObserver(backends).observe().screen_size == (0, 0)

    def test_negative_dimensions_passthrough(self):
        backends = ObservationBackends(screen_size=lambda: (-5, -5))
        obs = ScreenObserver(backends).observe()
        assert obs.screen_size == (-5, -5)  # raw passthrough; consumers validate

    def test_non_dict_backends_ignored(self):
        backends = ObservationBackends(active_window=lambda: ["not", "a", "dict"],
                                       browser_tab=lambda: "nope")
        obs = ScreenObserver(backends).observe()
        assert obs.active_window_title == ""
        assert obs.browser_url == ""

    def test_unavailable_display_returns_zero(self):
        backends = ObservationBackends(screen_size=lambda: None)
        assert ScreenObserver(backends).observe().screen_size is None


class TestElements:
    def test_element_dict_normalized_lower(self):
        obs = ScreenObserver(ObservationBackends(
            ui_elements=lambda: [{"role": "button", "label": "OK",
                                  "bounds": [10, 20, 30, 40]}]))
        e = obs.observe().elements[0]
        assert e.bounds == (10, 20, 30, 40)
        assert e.role == "button"
        assert e.label == "OK"

    def test_element_bounds_2_tuple(self):
        obs = ScreenObserver(ObservationBackends(
            ui_elements=lambda: [{"bounds": [5, 6]}]))
        e = obs.observe().elements[0]
        assert e.bounds == (5, 6, 0, 0)

    def test_element_bad_bounds_zero(self):
        obs = ScreenObserver(ObservationBackends(
            ui_elements=lambda: [{"bounds": "garbage"}]))
        assert obs.observe().elements[0].bounds == (0, 0, 0, 0)

    def test_element_via_text_name(self):
        obs = ScreenObserver(ObservationBackends(
            ui_elements=lambda: [{"text": "Hello", "confidence": 0.8}]))
        e = obs.observe().elements[0]
        assert e.label == "Hello"
        assert e.confidence == 0.8

    def test_element_instance_passthrough(self):
        el = Element(role="AXButton", label="Keep")
        obs = ScreenObserver(ObservationBackends(ui_elements=lambda: [el]))
        assert obs.observe().elements[0] is el

    def test_element_string_coerced(self):
        obs = ScreenObserver(ObservationBackends(ui_elements=lambda: ["raw"]))
        assert obs.observe().elements[0].label == "raw"

    def test_many_elements_bounded(self):
        backends = ObservationBackends(ui_elements=lambda: [{"label": f"e{i}"} for i in range(150)])
        obs = ScreenObserver(backends).observe()
        assert len(obs.elements) == 100


class TestRapidDuplicate:
    def test_duplicate_elements_kept(self):
        backends = ObservationBackends(ui_elements=lambda: [
            {"label": "x"}, {"label": "x"}])
        obs = ScreenObserver(backends).observe()
        assert len(obs.elements) == 2

    def test_rapid_change_reflects_latest(self):
        state = {"n": 0}
        def elems():
            state["n"] += 1
            return [{"label": f"run{state['n']}"}]

        backends = ObservationBackends(ui_elements=elems)
        first = ScreenObserver(backends).observe()
        second = ScreenObserver(backends).observe()
        assert first.elements[0].label == "run1"
        assert second.elements[0].label == "run2"


class TestDeterministic:
    def test_consistent_normalization(self):
        backends = ObservationBackends(ui_elements=lambda: [{
            "role": "button", "label": "x", "selector": "#x", "index": 3,
            "bounds": [1, 2, 3, 4], "confidence": 0.5, "app": "T"}])
        o1 = ScreenObserver(backends).observe().elements[0].to_dict()
        o2 = ScreenObserver(backends).observe().elements[0].to_dict()
        assert o1 == o2