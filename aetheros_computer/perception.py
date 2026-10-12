"""
Unified Perception Layer (Master 15 Phases 6-9).

Merges browser accessibility tree + desktop accessibility + vision OCR + screen capture
into a single perception interface with confidence scoring.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from aetheros_computer.action import ActionDomain, RiskTier, VerificationRequirement
from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


class PerceptionSource(Enum):
    """Source of perception data."""

    BROWSER_AX = "browser_ax"           # Browser accessibility tree (CDP)
    DESKTOP_AX = "desktop_ax"           # Desktop accessibility (UIA/AT-SPI/AXAPI)
    VISION_OCR = "vision_ocr"           # OCR from screenshot
    SCREEN_CAPTURE = "screen_capture"   # Raw screenshot
    VISION_UNDERSTAND = "vision_understand"  # Vision model analysis
    BROWSER_DOM = "browser_dom"         # Raw DOM (fallback)
    FILE_CONTENT = "file_content"       # File/document content


class ElementRole(Enum):
    """Standardized element roles across sources."""

    BUTTON = "button"
    LINK = "link"
    TEXT_FIELD = "text_field"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SELECT = "select"
    TEXTAREA = "textarea"
    LABEL = "label"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TAB = "tab"
    TAB_PANEL = "tab_panel"
    DIALOG = "dialog"
    ALERT = "alert"
    MENU = "menu"
    MENU_ITEM = "menu_item"
    TOOLBAR = "toolbar"
    STATUSBAR = "statusbar"
    SCROLLBAR = "scrollbar"
    SLIDER = "slider"
    SPINBUTTON = "spinbutton"
    PROGRESSBAR = "progressbar"
    IMAGE = "image"
    GENERIC = "generic"


@dataclass
class BoundingBox:
    """Normalized bounding box with DPI awareness."""

    x: float
    y: float
    width: float
    height: float
    dpi_scale: float = 1.0              # monitor DPI scale factor
    source_dpi: int = 96                # source DPI (96 = standard)

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    def to_logical(self, target_dpi: int = 96) -> "BoundingBox":
        """Convert to target DPI."""
        if self.source_dpi == target_dpi:
            return self
        scale = target_dpi / self.source_dpi
        return BoundingBox(
            x=self.x * scale,
            y=self.y * scale,
            width=self.width * scale,
            height=self.height * scale,
            dpi_scale=self.dpi_scale * scale,
            source_dpi=target_dpi,
        )

    def contains_point(self, x: float, y: float) -> bool:
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)


@dataclass
class UIElement:
    """Unified UI element across all perception sources."""

    element_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source: PerceptionSource = PerceptionSource.SCREEN_CAPTURE
    role: ElementRole = ElementRole.GENERIC
    name: str = ""                       # accessible name / button text / link text
    value: str = ""                      # current value (for inputs)
    description: str = ""                # description / placeholder
    bounds: Optional[BoundingBox] = None
    confidence: float = 1.0              # 0.0 - 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    states: Set[str] = field(default_factory=set)  # focused, selected, disabled, etc.
    children: List["UIElement"] = field(default_factory=list)
    parent_id: Optional[str] = None
    source_metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_selector(self) -> Dict[str, Any]:
        """Generate selector for targeting (Phase 8)."""
        selector = {"source": self.source.value}
        if self.source == PerceptionSource.BROWSER_AX:
            selector.update({"type": "ax_ref", "ref": self.attributes.get("ref")})
        elif self.source == PerceptionSource.BROWSER_DOM:
            selector.update({"type": "css", "selector": self.attributes.get("css_selector")})
        elif self.source in (PerceptionSource.VISION_OCR, PerceptionSource.VISION_UNDERSTAND):
            selector.update({"type": "text", "text": self.name})
        elif self.source == PerceptionSource.DESKTOP_AX:
            selector.update({"type": "ax_path", "path": self.attributes.get("ax_path")})
        else:
            selector.update({"type": "coordinate", "x": self.bounds.center[0] if self.bounds else 0,
                           "y": self.bounds.center[1] if self.bounds else 0})
        return selector

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "source": self.source.value,
            "role": self.role.value,
            "name": self.name,
            "value": self.value,
            "description": self.description,
            "bounds": self.bounds.__dict__ if self.bounds else None,
            "confidence": self.confidence,
            "attributes": self.attributes,
            "states": list(self.states),
            "children": [c.to_dict() for c in self.children],
            "parent_id": self.parent_id,
            "source_metadata": self.source_metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class PerceptionSnapshot:
    """Complete perception snapshot at a point in time."""

    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    source: PerceptionSource = PerceptionSource.SCREEN_CAPTURE
    elements: List[UIElement] = field(default_factory=list)
    screenshot_b64: Optional[str] = None
    screenshot_format: str = "png"
    viewport_bounds: Optional[BoundingBox] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_element_by_id(self, element_id: str) -> Optional[UIElement]:
        for el in self.elements:
            if el.element_id == element_id:
                return el
            found = self._find_in_children(el, element_id)
            if found:
                return found
        return None

    def _find_in_children(self, parent: UIElement, element_id: str) -> Optional[UIElement]:
        for child in parent.children:
            if child.element_id == element_id:
                return child
            found = self._find_in_children(child, element_id)
            if found:
                return found
        return None

    def find_elements_by_text(self, text: str, fuzzy: bool = True) -> List[UIElement]:
        """Find elements containing text (Phase 8 semantic targeting)."""
        results = []
        text_lower = text.lower()
        for el in self.elements:
            if self._match_element_text(el, text_lower, fuzzy):
                results.append(el)
        return results

    def _match_element_text(self, el: UIElement, text_lower: str, fuzzy: bool) -> bool:
        haystack = (el.name + " " + el.value + " " + el.description).lower()
        if fuzzy:
            return text_lower in haystack
        return text_lower == haystack

    def get_interactive_elements(self) -> List[UIElement]:
        """Get all interactive elements (buttons, links, inputs, etc.)."""
        interactive_roles = {
            ElementRole.BUTTON, ElementRole.LINK, ElementRole.TEXT_FIELD,
            ElementRole.CHECKBOX, ElementRole.RADIO, ElementRole.SELECT,
            ElementRole.TEXTAREA, ElementRole.SLIDER, ElementRole.SPINBUTTON,
            ElementRole.MENU_ITEM, ElementRole.TAB,
        }
        return [el for el in self.elements if el.role in interactive_roles]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "source": self.source.value,
            "elements": [e.to_dict() for e in self.elements],
            "has_screenshot": self.screenshot_b64 is not None,
            "viewport_bounds": self.viewport_bounds.__dict__ if self.viewport_bounds else None,
            "metadata": self.metadata,
        }


class PerceptionEngine:
    """Unified perception engine coordinating all sources."""

    def __init__(self):
        self._browser_bridge = None
        self._desktop_backend = None
        self._vision_engine = None
        self._capture_engine = None
        self._last_snapshot: Optional[PerceptionSnapshot] = None

    def set_browser_bridge(self, bridge: Any) -> None:
        """Inject browser bridge (from browser_tool.py)."""
        self._browser_bridge = bridge

    def set_desktop_backend(self, backend: Any) -> None:
        """Inject desktop backend (computer_use_tool backend)."""
        self._desktop_backend = backend

    def set_vision_engine(self, engine: Any) -> None:
        """Inject vision engine (from vision_tools)."""
        self._vision_engine = engine

    def set_capture_engine(self, engine: Any) -> None:
        """Inject capture engine (ScreenCaptureRuntime)."""
        self._capture_engine = engine

    async def capture_browser_ax(self, session_key: str) -> PerceptionSnapshot:
        """Capture browser accessibility tree via CDP."""
        if not self._browser_bridge:
            raise RuntimeError("Browser bridge not configured")
        # Delegate to browser_tool's snapshot logic
        from tools.browser_tool import browser_snapshot
        import json
        result = browser_snapshot(action="snapshot", session_id=session_key)
        data = json.loads(result)
        if not data.get("success"):
            raise RuntimeError(f"Browser snapshot failed: {data.get('error')}")

        snapshot = self._parse_browser_snapshot(data.get("snapshot", {}), session_key)
        self._last_snapshot = snapshot
        return snapshot

    def _parse_browser_snapshot(self, data: Dict[str, Any], session_key: str) -> PerceptionSnapshot:
        """Parse browser snapshot into unified elements."""
        snapshot = PerceptionSnapshot(
            source=PerceptionSource.BROWSER_AX,
            metadata={"session_key": session_key}
        )

        # Parse frame tree
        frame_tree = data.get("frame_tree", {})
        self._parse_frame(frame_tree, snapshot.elements)

        # Add pending dialogs as alert elements
        for dialog in data.get("pending_dialogs", []):
            alert = UIElement(
                source=PerceptionSource.BROWSER_AX,
                role=ElementRole.ALERT,
                name=dialog.get("message", ""),
                attributes={"dialog_type": dialog.get("type"), "dialog_id": dialog.get("id")},
                confidence=0.9,
            )
            snapshot.elements.append(alert)

        return snapshot

    def _parse_frame(self, frame: Dict[str, Any], parent_elements: List[UIElement], parent_id: str = None):
        """Recursively parse CDP frame tree into UIElements."""
        ax_node = frame.get("ax_node")
        if not ax_node:
            return

        # Parse this node and its children
        children = ax_node.get("children", [])
        for child in children:
            el = self._ax_node_to_element(child, parent_id)
            if el:
                parent_elements.append(el)
                # Recurse into children
                if "children" in child:
                    self._parse_frame({"ax_node": child}, el.children, el.element_id)

    def _ax_node_to_element(self, node: Dict[str, Any], parent_id: str = None) -> Optional[UIElement]:
        """Convert AX node to UIElement."""
        role_str = node.get("role", "").lower()
        try:
            role = ElementRole(role_str.replace("role_", "").upper())
        except ValueError:
            role = ElementRole.GENERIC

        # Filter out non-interactive/non-content elements
        if role == ElementRole.GENERIC and not node.get("name") and not node.get("value"):
            return None

        bounds = None
        if "bounds" in node:
            b = node["bounds"]
            bounds = BoundingBox(
                x=b.get("x", 0), y=b.get("y", 0),
                width=b.get("width", 0), height=b.get("height", 0),
            )

        el = UIElement(
            source=PerceptionSource.BROWSER_AX,
            role=role,
            name=node.get("name", ""),
            value=node.get("value", ""),
            description=node.get("description", ""),
            bounds=bounds,
            confidence=0.95,  # AX tree is authoritative
            attributes={
                "ref": node.get("ref"),
                "role_raw": node.get("role"),
                "focused": node.get("focused", False),
                "editable": node.get("editable", False),
            },
            states=set(node.get("states", [])),
        )

        # Add children
        for child in node.get("children", []):
            child_el = self._ax_node_to_element(child, el.element_id)
            if child_el:
                child_el.parent_id = el.element_id
                el.children.append(child_el)

        return el

    async def capture_desktop_ax(self) -> PerceptionSnapshot:
        """Capture desktop accessibility tree (platform-specific)."""
        if not self._desktop_backend:
            raise RuntimeError("Desktop backend not configured")

        # This would call the computer_use backend's AX tree capture
        # For now, return empty snapshot with vision fallback
        return await self.capture_vision_understand()

    async def capture_vision_understand(self) -> PerceptionSnapshot:
        """Capture and understand screen via vision model."""
        if not self._vision_engine and not self._capture_engine:
            raise RuntimeError("Vision engine or capture engine not configured")

        # Capture screenshot
        if self._capture_engine:
            from aetheros_vision.capture import ScreenCaptureRuntime
            capture = self._capture_engine
            img_path = capture.capture()
        else:
            raise RuntimeError("No capture engine available")

        # Analyze with vision
        if self._vision_engine:
            # Use vision_understand tool
            from tools.vision_tools import _handle_screen_understand
            import json
            result = _handle_screen_understand({
                "image_path": img_path,
                "query": "Identify all interactive UI elements: buttons, links, inputs, buttons, menus, etc.",
            })
            data = json.loads(result)
            return self._parse_vision_understand(data, img_path)

        return PerceptionSnapshot(source=PerceptionSource.SCREEN_CAPTURE)

    def _parse_vision_understand(self, data: Dict[str, Any], img_path: str) -> PerceptionSnapshot:
        """Parse vision_understand output into unified elements."""
        snapshot = PerceptionSnapshot(
            source=PerceptionSource.VISION_UNDERSTAND,
            metadata={"image_path": img_path}
        )

        # Load image for base64
        with open(img_path, "rb") as f:
            snapshot.screenshot_b64 = base64.b64encode(f.read()).decode()

        # Parse elements from vision output
        elements_data = data.get("elements", [])
        for ed in elements_data:
            bounds = None
            if "bounds" in ed:
                b = ed["bounds"]
                bounds = BoundingBox(
                    x=b.get("x", 0), y=b.get("y", 0),
                    width=b.get("width", 0), height=b.get("height", 0),
                )

            role_str = ed.get("role", "generic").lower()
            try:
                role = ElementRole(role_str)
            except ValueError:
                role = ElementRole.GENERIC

            el = UIElement(
                source=PerceptionSource.VISION_UNDERSTAND,
                role=role,
                name=ed.get("text", ""),
                value=ed.get("value", ""),
                description=ed.get("description", ""),
                bounds=bounds,
                confidence=ed.get("confidence", 0.7),
                attributes={
                    "element_type": ed.get("element_type"),
                    "selector": ed.get("selector"),
                },
            )
            snapshot.elements.append(el)

        return snapshot

    async def get_merged_snapshot(self, session_key: str = None) -> PerceptionSnapshot:
        """Get merged perception from all available sources."""
        snapshots = []

        # Try browser first (most structured)
        if session_key and self._browser_bridge:
            try:
                browser_snap = await self.capture_browser_ax(session_key)
                snapshots.append(browser_snap)
            except Exception as e:
                logger.warning(f"Browser AX capture failed: {e}")

        # Try vision understanding
        try:
            vision_snap = await self.capture_vision_understand()
            snapshots.append(vision_snap)
        except Exception as e:
            logger.warning(f"Vision understand failed: {e}")

        # Merge snapshots
        return self._merge_snapshots(snapshots)

    # Phase 6 (cert): explicit ordered fallback chain.
    FALLBACK_ORDER = (PerceptionSource.BROWSER_AX,
                      PerceptionSource.DESKTOP_AX,
                      PerceptionSource.VISION_UNDERSTAND)

    async def perceive_with_fallback(
        self, session_key: str = None
    ) -> Tuple[PerceptionSnapshot, str]:
        """Try sources in FALLBACK_ORDER; return (snapshot, source_used).

        Never raises while at least one source succeeds; raises only when all
        configured sources fail, so callers can surface a real error instead
        of silently acting on nothing.
        """
        errors: List[str] = []
        for source in self.FALLBACK_ORDER:
            try:
                if source == PerceptionSource.BROWSER_AX:
                    snap = await self.capture_browser_ax(session_key or "")
                elif source == PerceptionSource.DESKTOP_AX:
                    snap = await self.capture_desktop_ax()
                else:
                    snap = await self.capture_vision_understand()
                if snap is not None and (snap.elements or snap.screenshot_b64):
                    return snap, source.value
                errors.append(f"{source.value}: empty snapshot")
            except Exception as exc:
                errors.append(f"{source.value}: {exc}")
        raise RuntimeError("all perception sources failed: " + "; ".join(errors))

    def _merge_snapshots(self, snapshots: List[PerceptionSnapshot]) -> PerceptionSnapshot:
        """Merge multiple perception snapshots, deduplicating by text/position."""
        if not snapshots:
            return PerceptionSnapshot()

        if len(snapshots) == 1:
            return snapshots[0]

        merged = PerceptionSnapshot(
            source=PerceptionSource.SCREEN_CAPTURE,  # merged
            metadata={"merged_from": [s.source.value for s in snapshots]}
        )

        # Simple merge: prefer higher confidence, deduplicate by text+position
        seen: Dict[str, UIElement] = {}

        for snap in snapshots:
            for el in snap.elements:
                key = self._element_key(el)
                if key not in seen or el.confidence > seen[key].confidence:
                    seen[key] = el

        merged.elements = list(seen.values())
        return merged

    def _element_key(self, el: UIElement) -> str:
        """Generate deduplication key for element."""
        if el.bounds:
            pos = f"{int(el.bounds.x)},{int(el.bounds.y)}"
        else:
            pos = "nopos"
        text = (el.name + el.value).strip()[:50]
        return f"{el.source.value}:{pos}:{text}"


# Global instance
_perception_engine: Optional[PerceptionEngine] = None


def get_perception_engine() -> PerceptionEngine:
    global _perception_engine
    if _perception_engine is None:
        _perception_engine = PerceptionEngine()
    return _perception_engine


# =============================================================================
# VISUAL TARGETING (Phase 8)
# =============================================================================

@dataclass
class VisualTarget:
    """Target for visual interaction with confidence."""

    element: UIElement
    confidence: float
    method: str  # "semantic", "css", "ax_ref", "text", "coordinate"
    alternatives: List[UIElement] = field(default_factory=list)

    def to_action_params(self) -> Dict[str, Any]:
        """Convert to action parameters for execution."""
        selector = self.element.to_selector()
        params = {"method": self.method, "confidence": self.confidence}

        if self.method == "coordinate" and self.element.bounds:
            params["coordinate"] = [self.element.bounds.center[0], self.element.bounds.center[1]]
        elif self.method in ("ax_ref", "css", "text"):
            params["selector"] = selector
        elif self.method == "semantic":
            params["text"] = self.element.name
            if self.element.attributes.get("ref"):
                selector["ref"] = self.element.attributes["ref"]

        return params


class VisualTargeter:
    """Find and rank visual targets for interaction (Phase 8)."""

    def __init__(self, perception_engine: PerceptionEngine = None):
        self.engine = perception_engine or get_perception_engine()

    async def find_target(
        self,
        description: str,
        snapshot: PerceptionSnapshot = None,
        require_confidence: float = 0.7,
        hints: Optional[List[str]] = None,
    ) -> Optional[VisualTarget]:
        """Find best matching target for description (Phase 8 semantic targeting).

        ``hints`` are MASTER 14 knowledge-bridge candidate strings (DATA only):
        they add search candidates AFTER the live snapshot match, and a hint
        can never click by itself — the winning element must still exist on
        the CURRENT screen with sufficient confidence.
        """
        if snapshot is None:
            snapshot = await self.engine.get_merged_snapshot()

        # Try semantic match first (button text, link text, label)
        candidates = snapshot.find_elements_by_text(description, fuzzy=True)

        # Knowledge hints (Phase 3 wiring): candidate texts only.
        for hint in (hints or []):
            if not hint or hint.startswith("[knowledge entry withheld"):
                continue
            for el in snapshot.find_elements_by_text(hint, fuzzy=True):
                if el not in candidates:
                    candidates.append(el)

        if not candidates:
            # Fallback: search in attributes
            candidates = [
                el for el in snapshot.elements
                if description.lower() in str(el.attributes).lower()
            ]

        if not candidates:
            return None

        # Rank by confidence and role relevance
        interactive_roles = {
            ElementRole.BUTTON, ElementRole.LINK, ElementRole.TEXT_FIELD,
            ElementRole.CHECKBOX, ElementRole.RADIO, ElementRole.SELECT,
            ElementRole.TEXTAREA, ElementRole.SLIDER, ElementRole.MENU_ITEM,
        }

        scored = []
        for c in candidates:
            score = c.confidence
            if c.role in interactive_roles:
                score += 0.1
            if c.role == ElementRole.BUTTON and "button" in description.lower():
                score += 0.2
            if c.role == ElementRole.LINK and "link" in description.lower():
                score += 0.2
            scored.append((score, c))

        scored.sort(reverse=True, key=lambda x: x[0])
        best_score, best = scored[0]

        if best_score < require_confidence:
            logger.warning(f"Low confidence target: {best_score:.2f} for '{description}'")
            return None

        # Determine targeting method
        method = "semantic"
        if best.source == PerceptionSource.BROWSER_AX and best.attributes.get("ref"):
            method = "ax_ref"
        elif best.source == PerceptionSource.BROWSER_DOM and best.attributes.get("css_selector"):
            method = "css"
        elif best.source in (PerceptionSource.VISION_OCR, PerceptionSource.VISION_UNDERSTAND):
            method = "text"
        else:
            method = "coordinate"

        return VisualTarget(
            element=best,
            confidence=best_score,
            method=method,
            alternatives=[c for _, c in scored[1:3]],
        )

    async def find_all_targets(
        self,
        description: str,
        snapshot: PerceptionSnapshot = None,
        max_results: int = 5,
    ) -> List[VisualTarget]:
        """Find all matching targets (for ambiguous queries)."""
        if snapshot is None:
            snapshot = await self.engine.get_merged_snapshot()

        candidates = snapshot.find_elements_by_text(description, fuzzy=True)
        scored = [(c.confidence + (0.1 if c.role in {ElementRole.BUTTON, ElementRole.LINK} else 0), c)
                  for c in candidates]
        scored.sort(reverse=True, key=lambda x: x[0])

        targets = []
        for score, c in scored[:max_results]:
            method = "semantic"
            if c.source == PerceptionSource.BROWSER_AX and c.attributes.get("ref"):
                method = "ax_ref"
            elif c.source == PerceptionSource.BROWSER_DOM and c.attributes.get("css_selector"):
                method = "css"
            elif c.source in (PerceptionSource.VISION_OCR, PerceptionSource.VISION_UNDERSTAND):
                method = "text"
            else:
                method = "coordinate"
            targets.append(VisualTarget(element=c, confidence=score, method=method))

        return targets


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "PerceptionSource",
    "ElementRole",
    "BoundingBox",
    "UIElement",
    "PerceptionSnapshot",
    "PerceptionEngine",
    "VisualTarget",
    "VisualTargeter",
    "get_perception_engine",
]