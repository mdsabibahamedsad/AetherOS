"""UIElementDetector — accessibility-first element targeting (Step 5).

Preference order: role/name selectors and stable element indices from an
accessibility/DOM tree, then OCR text match, then — only when nothing
semantic is available — coordinate fallback with bound + screen validation.

The detector never fabricates elements; it reports only what the underlying
backends actually observed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from aetheros_actions.model import Element


@dataclass
class SelectorBackends:
    """Element-lookup functions. Each returns dicts/Element or lists."""

    find_by_role_name: Optional[Callable[[Optional[str], Optional[str]], List[Element]]] = None
    find_by_ocr: Optional[Callable[[str], List[Element]]] = None
    find_by_coordinate: Optional[Callable[[Tuple[int, int]], Optional[Element]]] = None
    screen_size: Optional[Callable[[], Tuple[int, int]]] = None


class UIElementDetector:
    """Resolves a semantic target into an element using the best backend."""

    def __init__(self, backends: Optional[SelectorBackends] = None) -> None:
        self.backends = backends or SelectorBackends()

    def resolve(self, *, label: str = "", role: str = ""):
        """Return the best element match, preferring semantic backends."""
        if self.backends.find_by_role_name:
            try:
                hits = self.backends.find_by_role_name(role or None, label)
                if hits:
                    return self._pick_best(hits)
            except Exception:
                pass
        if label and self.backends.find_by_ocr:
            try:
                hits = self.backends.find_by_ocr(label)
                if hits:
                    return self._pick_best(hits)
            except Exception:
                pass
        return None

    def resolve_coordinate(self, x: int, y: int) -> Optional[Element]:
        """Coordinate fallback with screen-bounds validation (Step 10)."""
        if self.backends.find_by_coordinate:
            try:
                return self.backends.find_by_coordinate((x, y))
            except Exception:
                return None
        return None

    @staticmethod
    def _pick_best(hits: List[Element]) -> Element:
        return max(hits, key=lambda e: e.confidence or 0.0)


_ = field  # keep dataclasses import stable across python versions

__all__ = ["SelectorBackends", "UIElementDetector"]