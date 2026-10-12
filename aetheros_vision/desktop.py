"""AetherOS Vision — desktop vision & accessibility intelligence.

Understands desktop UI (windows, dialogs, menus, buttons, forms) and
web pages / accessibility trees by combining OCR of a screenshot with a
structured accessibility snapshot when available. Everything reported is
grounded in observed text or an explicit UI tree — no hallucinated
elements.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_vision.config import VisionSettings, load_vision_settings
from aetheros_vision.models import AnalysisResult, BoundingBox

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    """An element in a desktop window or web page."""

    role: str = ""
    text: str = ""
    box: Optional[BoundingBox] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "text": self.text,
            "box": self.box.to_dict() if self.box else None,
            "attributes": self.attributes,
        }


class DesktopVision:
    """Desktop window / dialog understanding via OCR + optional UI Automation."""

    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()

    def analyze_screenshot(self, path: str) -> AnalysisResult:
        from aetheros_vision.ocr import create_ocr_engine
        engine = create_ocr_engine(self._settings)
        result = AnalysisResult(backend="rule")
        result.metadata["ui_type"] = "desktop"
        elements: List[UIElement] = []
        if engine.is_available():
            ocr = engine.extract(path)
            if ocr and ocr.success:
                result.ocr = ocr
                result.text = ocr.text
                for block in ocr.blocks:
                    if not block.text.strip():
                        continue
                    elements.append(UIElement(role="text", text=block.text.strip(), box=block.box))
                result.metadata["elements"] = [e.to_dict() for e in elements]
                result.summary = _summarize_ui_elements(elements)
                result.labels = ["desktop", "ui"]
            else:
                result.success = False
                result.error = ocr.error if ocr else "OCR unavailable"
        else:
            result.success = False
            result.error = "OCR engine unavailable for desktop vision"
        return result

    def find_element(self, path: str, query: str) -> Optional[UIElement]:
        """Locate a UI element by text (button/dialog label etc.)."""
        result = self.analyze_screenshot(path)
        if not result.ocr or not result.ocr.success:
            return None
        q = query.strip().lower()
        for block in result.ocr.blocks:
            if q in block.text.strip().lower():
                return UIElement(role="interactive", text=block.text.strip(), box=block.box)
        return None

    def locate_button(self, path: str, label: str) -> Optional[BoundingBox]:
        el = self.find_element(path, label)
        return el.box if el else None


def _summarize_ui_elements(elements: List[UIElement]) -> str:
    if not elements:
        return "No UI elements detected."
    interactive = sum(1 for e in elements if e.role == "interactive")
    return f"Detected {len(elements)} UI text elements ({interactive} interactive-looking)."


class BrowserVision:
    """Web page understanding from an accessibility tree + screenshot OCR."""

    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()

    def analyze_snapshot(self, accessibility_tree: Dict[str, Any], screenshot: Optional[str] = None) -> AnalysisResult:
        """Analyse a structured accessibility tree (from browser automation).

        ``accessibility_tree`` is a nested dict like the one browser
        automation tools emit. Text content is collected recursively; roles
        and interactive elements are recorded. When a screenshot path is
        provided, OCR text is merged in too.
        """
        result = AnalysisResult(backend="rule")
        elements: List[UIElement] = []
        texts: List[str] = []

        def walk(node: Dict[str, Any]):
            if not isinstance(node, dict):
                return
            role = str(node.get("role") or node.get("tagName") or "")
            name = str(node.get("name") or node.get("text") or node.get("label") or "").strip()
            box = node.get("boundingBox") or node.get("box")
            bbox = None
            if isinstance(box, dict) and "x" in box and "y" in box:
                bbox = BoundingBox(x=box.get("x", 0), y=box.get("y", 0), width=box.get("width", 0), height=box.get("height", 0))
            if name:
                texts.append(name)
                elements.append(UIElement(role=role or "element", text=name, box=bbox))
            for child in node.get("children", []):
                walk(child)

        walk(accessibility_tree)
        result.metadata["elements"] = [e.to_dict() for e in elements]
        result.text = "\n".join(texts)
        result.metadata["ui_type"] = "browser"
        result.labels = ["browser", "web"]

        # Merge screenshot OCR when supplied.
        if screenshot:
            try:
                from aetheros_vision.ocr import create_ocr_engine
                engine = create_ocr_engine(self._settings)
                if engine.is_available():
                    ocr = engine.extract(screenshot)
                    if ocr and ocr.success:
                        result.ocr = ocr
                        if ocr.text:
                            result.text = (result.text + "\n" + ocr.text).strip()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Browser screenshot OCR failed: %s", exc)

        result.summary = f"Parsed {len(elements)} elements from the accessibility tree."
        return result
