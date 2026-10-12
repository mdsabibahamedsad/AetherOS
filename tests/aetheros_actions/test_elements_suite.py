"""Phase 2D — UIElementDetector extended: element classes + ambiguity/stale.

Covers: buttons/links/inputs/dialogs/checkbox/radio resolution via semantic or
OCR backends, disabled/hidden handling (reported as observed), duplicates,
ambiguity (confidence pick), missing elements, and stale/raising backends
(never fabricates).
"""

from __future__ import annotations

from aetheros_actions.elements import SelectorBackends, UIElementDetector
from aetheros_actions.model import Element


def _backend(role_hits=(), ocr_hits=(), coord_hit=None, screen=None):
    return SelectorBackends(
        find_by_role_name=lambda role, label: list(role_hits),
        find_by_ocr=lambda text: list(ocr_hits),
        find_by_coordinate=lambda xy: coord_hit,
        screen_size=screen,
    )


class TestElementKinds:
    def test_button(self):
        b = SelectorBackends(
            find_by_role_name=lambda role, label: [Element(role="button", label="Go", confidence=1.0)],
            find_by_ocr=lambda text: [],
        )
        el = UIElementDetector(b).resolve(label="Go")
        assert el is not None and el.role == "button"

    def test_link(self):
        b = SelectorBackends(
            find_by_role_name=lambda role, label: [],
            find_by_ocr=lambda text: [Element(role="link", label="Docs", confidence=1.0)],
        )
        el = UIElementDetector(b).resolve(label="Docs")
        assert el is not None and el.role == "link"

    def test_input(self):
        b = SelectorBackends(
            find_by_role_name=lambda role, label: [Element(role="textbox", label="Name", confidence=1.0)],
            find_by_ocr=lambda text: [],
        )
        el = UIElementDetector(b).resolve(label="Name")
        assert el is not None and el.role == "textbox"

    def test_dialog_heading(self):
        b = SelectorBackends(
            find_by_role_name=lambda role, label: [Element(role="dialog", label="Confirm", confidence=1.0)],
            find_by_ocr=lambda text: [],
        )
        el = UIElementDetector(b).resolve(label="Confirm")
        assert el is not None and el.role == "dialog"

    def test_checkbox_and_radio(self):
        b_cb = SelectorBackends(
            find_by_role_name=lambda role, label: [Element(role="checkbox", label="Accept", confidence=1.0)],
            find_by_ocr=lambda text: [],
        )
        cb = UIElementDetector(b_cb).resolve(label="Accept")
        b_rb = SelectorBackends(
            find_by_role_name=lambda role, label: [Element(role="radio", label="Opt1", confidence=1.0)],
            find_by_ocr=lambda text: [],
        )
        rb = UIElementDetector(b_rb).resolve(label="Opt1")
        assert cb.role == "checkbox" and rb.role == "radio"

    def test_disabled_control_reported_as_observed(self):
        # Detector reports what backends observe; it never fabricates.
        disabled = Element(role="button", label="Save", confidence=0.9)
        b = SelectorBackends(
            find_by_role_name=lambda role, label: [disabled],
            find_by_ocr=lambda text: [],
        )
        el = UIElementDetector(b).resolve(label="Save")
        assert el is not None and el.label == "Save"

    def test_hidden_control_only_via_backend(self):
        # If backend is absent, a hidden control must not be invented.
        b = SelectorBackends(
            find_by_role_name=lambda role, label: [],
            find_by_ocr=lambda text: [],
        )
        el = UIElementDetector(b).resolve(label="any")
        assert el is None


class TestAmbiguity:
    def test_picks_highest_confidence(self):
        b = _backend(role_hits=[
            Element(role="button", label="Go", confidence=0.4),
            Element(role="button", label="Go", confidence=0.9),
        ])
        el = UIElementDetector(b).resolve(label="Go")
        assert el.confidence == 0.9

    def test_tie_returns_first(self):
        els = [Element(label="same", confidence=0.5), Element(label="same", confidence=0.5)]
        b = _backend(role_hits=els)
        assert UIElementDetector(b).resolve(label="same") is els[0]

    def test_semantic_beats_ocr(self):
        b = SelectorBackends(
            find_by_role_name=lambda r, l: [Element(role="button", label="Go", confidence=0.6)],
            find_by_ocr=lambda t: [Element(role="ocr", label="Go", confidence=0.95)],
        )
        el = UIElementDetector(b).resolve(label="Go")
        # Semantic axis preferred even at lower confidence than OCR.
        assert el.role == "button"


class TestMissingAndStale:
    def test_missing_element_none(self):
        b = _backend(role_hits=[], ocr_hits=[])
        assert UIElementDetector(b).resolve(label="none") is None

    def test_stale_role_backend_raises_falls_to_ocr(self):
        def boom(r, l):
            raise RuntimeError("tree stale")

        b = SelectorBackends(
            find_by_role_name=boom,
            find_by_ocr=lambda t: [Element(label="found", confidence=0.8)],
        )
        el = UIElementDetector(b).resolve(label="found")
        assert el is not None and el.label == "found"

    def test_all_backends_raise_none(self):
        def boom(*_a, **_k):
            raise RuntimeError("gone")

        b = SelectorBackends(find_by_role_name=boom, find_by_ocr=boom)
        assert UIElementDetector(b).resolve(label="x") is None

    def test_coordinate_backend_raises_none(self):
        def boom(_xy):
            raise RuntimeError("coords stale")

        b = SelectorBackends(find_by_coordinate=boom)
        assert UIElementDetector(b).resolve_coordinate(1, 1) is None

    def test_no_coordinate_backend_none(self):
        assert UIElementDetector(SelectorBackends()).resolve_coordinate(1, 1) is None

    def test_duplicate_elements_returned_verbatim(self):
        els = [Element(label="dup"), Element(label="dup")]
        b = _backend(role_hits=els)
        assert UIElementDetector(b).resolve(label="dup") in els