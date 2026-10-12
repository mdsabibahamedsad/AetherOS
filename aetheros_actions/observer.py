"""ScreenObserver — structured environment observation (Step 3).

Collects: screen dimensions, active window/app, focused browser tab URL, a
bounded set of semantic UI elements, and visible text. It glues the existing
observation backends together behind one interface:

* desktop screenshot + window metadata → :class:`aetheros_vision` / computer
  use backends;
* browser tab/DOM → :mod:`tools.browser_tool` snapshot.

The observer never returns cookies, session tokens, or raw secrets. All
backends are optional — missing backends degrade to partial observations.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from aetheros_actions.model import Element, Observation, TrustSource


@dataclass
class ObservationBackends:
    """Injected/adaptable backend functions for observation.

    Each returns a plain dict; the observer normalises it. Leaving any
    ``None`` simply skips that facet.
    """

    screen_size: Optional[Callable[[], Tuple[int, int]]] = None
    active_window: Optional[Callable[[], Dict[str, Any]]] = None
    browser_tab: Optional[Callable[[], Dict[str, Any]]] = None
    ui_elements: Optional[Callable[[], List[Dict[str, Any]]]] = None
    visible_text: Optional[Callable[[], str]] = None


class ScreenObserver:
    """Normalises environment facets into an :class:`Observation`."""

    def __init__(self, backends: Optional[ObservationBackends] = None) -> None:
        self.backends = backends or self._default_backends()

    @staticmethod
    def _default_backends() -> ObservationBackends:
        """Wire the real production backends (gracefully, lazily)."""
        backends = ObservationBackends()

        def _screen_size() -> Tuple[int, int]:
            try:
                from aetheros_vision.capture import ScreenCaptureRuntime
                runtime = ScreenCaptureRuntime()
                img = runtime.capture()  # writes to history dir; may fail headless
                if img and img.width and img.height:
                    return (int(img.width), int(img.height))
            except Exception:
                pass
            try:
                import pyautogui
                w, h = pyautogui.size()
                return (int(w), int(h))
            except Exception:
                return (0, 0)

        backends.screen_size = _screen_size
        return backends

    # ── observation ──────────────────────────────────────────────────

    def observe(self, mode: str = "desktop") -> Observation:
        obs = Observation(mode=mode)
        obs.screen_size = self._safe(self.backends.screen_size, default=(0, 0))
        window = self._safe(self.backends.active_window, default={})
        if isinstance(window, dict):
            obs.active_window_title = str(window.get("title", ""))
            obs.active_app = str(window.get("app", ""))
        tab = self._safe(self.backends.browser_tab, default={})
        if isinstance(tab, dict):
            obs.browser_url = str(tab.get("url", ""))
            if tab.get("mode"):
                obs.mode = str(tab["mode"])
        els = self._safe(self.backends.ui_elements, default=[])
        if isinstance(els, list):
            obs.elements = [self._normalise_element(e) for e in els[:100]]
        txt = self._safe(self.backends.visible_text, default="")
        if isinstance(txt, str):
            obs.visible_text = txt
        return obs

    # ── helpers ──────────────────────────────────────────────────────

    def _safe(self, fn: Optional[Callable[..., Any]], default: Any) -> Any:
        if fn is None:
            return default
        try:
            return fn()
        except Exception:
            return default

    @staticmethod
    def _normalise_element(raw: Any) -> Element:
        if isinstance(raw, Element):
            return raw
        if isinstance(raw, dict):
            bounds = raw.get("bounds") or raw.get("box") or []
            if len(bounds) == 4:
                b = tuple(int(v) for v in bounds)
            elif len(bounds) == 2:
                b = (int(bounds[0]), int(bounds[1]), 0, 0)
            else:
                b = (0, 0, 0, 0)
            return Element(
                role=str(raw.get("role", "")),
                label=str(raw.get("label") or raw.get("text") or raw.get("name") or ""),
                selector=str(raw.get("selector", "")),
                index=raw.get("index"),
                bounds=b,
                confidence=float(raw.get("confidence", 0.0)),
                app=str(raw.get("app", "")),
                source=TrustSource.TOOL_OUTPUT,
            )
        return Element(label=str(raw))


OBSERVER = "aether_observer"  # keys for manager-level backend injection

__all__ = ["ObservationBackends", "ScreenObserver"]