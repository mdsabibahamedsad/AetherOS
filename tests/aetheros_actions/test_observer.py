"""Tests for the observation + element-detector layer."""
from __future__ import annotations

from aetheros_actions.elements import SelectorBackends, UIElementDetector
from aetheros_actions.model import Element
from aetheros_actions.observer import ObservationBackends, ScreenObserver


class TestScreenObserver:
    def test_partial_backends(self):
        backends = ObservationBackends(
            screen_size=lambda: (1920, 1080),
            active_window=lambda: {"title": "TestWindow", "app": "TestApp"},
        )
        obs = ScreenObserver(backends).observe()
        assert obs.screen_size == (1920, 1080)
        assert obs.active_window_title == "TestWindow"
        assert obs.active_app == "TestApp"

    def test_browser_tab_facet(self):
        backends = ObservationBackends(
            browser_tab=lambda: {"url": "https://example.com", "mode": "browser"},
        )
        obs = ScreenObserver(backends).observe()
        assert obs.browser_url == "https://example.com"
        assert obs.mode == "browser"

    def test_elements_normalised(self):
        backends = ObservationBackends(
            ui_elements=lambda: [
                {"role": "AXButton", "label": "OK", "bounds": [10, 20, 30, 40],
                 "confidence": 0.9},
                Element(role="AXTextField", label="Name", bounds=(1, 1, 2, 2)),
            ],
        )
        obs = ScreenObserver(backends).observe()
        assert len(obs.elements) == 2
        assert obs.elements[0].label == "OK"
        assert obs.elements[0].bounds == (10, 20, 30, 40)

    def test_failing_backend_degrades(self):
        def boom():
            raise RuntimeError("no display")

        backends = ObservationBackends(screen_size=boom)
        obs = ScreenObserver(backends).observe()
        assert obs.screen_size == (0, 0)


class TestElementDetector:
    def test_semantic_first(self):
        backends = SelectorBackends(
            find_by_role_name=lambda role, label: [
                Element(role="AXButton", label="Go", confidence=0.9)
            ],
            find_by_ocr=lambda text: [
                Element(role="ocr", label="Go", confidence=0.5)
            ],
        )
        el = UIElementDetector(backends).resolve(label="Go")
        assert el is not None and el.role == "AXButton"

    def test_ocr_fallback_when_no_semantic(self):
        backends = SelectorBackends(
            find_by_role_name=lambda r, l: [],
            find_by_ocr=lambda text: [
                Element(role="ocr", label="Submit", confidence=0.7)
            ],
        )
        el = UIElementDetector(backends).resolve(label="Submit")
        assert el is not None and el.role == "ocr"

    def test_no_match_returns_none(self):
        backends = SelectorBackends(
            find_by_role_name=lambda r, l: [],
            find_by_ocr=lambda text: [],
        )
        assert UIElementDetector(backends).resolve(label="nothing") is None

    def test_coordinate_resolution(self):
        backends = SelectorBackends(
            find_by_coordinate=lambda xy: Element(label="at", bounds=(xy[0], xy[1], 5, 5))
        )
        el = UIElementDetector(backends).resolve_coordinate(100, 200)
        assert el is not None