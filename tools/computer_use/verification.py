"""Action verification and failure recovery for computer use.

The observe → act → observe → verify loop: after a backend action, re-observe
the screen and confirm the expected state before reporting success. When an
action fails, re-capture and retry (bounded) before giving up.

All helpers are backend-agnostic — they speak only the ``ComputerUseBackend``
interface, so they work with cua-driver, Win32, Linux, or a mock in tests.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, List, Optional

from tools.computer_use.backend import (
    ActionResult,
    CaptureResult,
    ComputerUseBackend,
    UIElement,
)


class ElementNotFoundError(Exception):
    """Raised when a target element/text could not be located within timeout."""

    def __init__(self, *, label: Optional[str] = None, role: Optional[str] = None,
                 text: Optional[str] = None, timeout: float = 0.0):
        self.label = label
        self.role = role
        self.text = text
        self.timeout = timeout
        what = ", ".join(
            f"{k}={v!r}" for k, v in
            (("label", label), ("role", role), ("text", text)) if v
        )
        super().__init__(f"element not found ({what}) after {timeout:.1f}s")


class VerificationTimeoutError(Exception):
    """Raised when an action's expected state never materialises."""

    def __init__(self, action: str, timeout: float, last: Any = None):
        self.action = action
        self.timeout = timeout
        self.last = last
        super().__init__(f"action {action!r} not verified after {timeout:.1f}s")


# ---------------------------------------------------------------------------
# Element discovery helpers
# ---------------------------------------------------------------------------

def find_element(
    backend: ComputerUseBackend,
    *,
    label: Optional[str] = None,
    role: Optional[str] = None,
    app: Optional[str] = None,
    max_elements: int = 1000,
) -> Optional[UIElement]:
    """Locate the first element matching ``label`` / ``role`` in one capture.

    Uses ``backend.capture(mode="ax")`` when supported; falls back to the
    ``elements`` of a ``som`` capture otherwise. Returns None when no match.
    """
    for mode in ("ax", "som", "vision"):
        try:
            cap = backend.capture(mode=mode, app=app)
        except Exception:
            continue
        if not cap.elements:
            continue
        matched = _match_elements(cap.elements, label=label, role=role)
        if matched:
            return matched[0]
    return None


def _match_elements(
    elements: List[UIElement],
    *,
    label: Optional[str] = None,
    role: Optional[str] = None,
    max_elements: int = 1000,
) -> List[UIElement]:
    """Return elements matching an optional label substring and/or role."""
    out: List[UIElement] = []
    label_lower = label.lower() if label else None
    for e in elements[:max_elements]:
        if role and e.role.lower() != role.lower():
            continue
        if label_lower and label_lower not in e.label.lower():
            continue
        out.append(e)
    return out


def wait_for_element(
    backend: ComputerUseBackend,
    *,
    label: Optional[str] = None,
    role: Optional[str] = None,
    text: Optional[str] = None,
    app: Optional[str] = None,
    timeout: float = 15.0,
    interval: float = 0.5,
) -> UIElement:
    """Poll until an element (or OCR text) appears; raise ElementNotFoundError."""
    deadline = time.monotonic() + timeout
    last: Optional[UIElement] = None
    while time.monotonic() < deadline:
        if text is not None:
            found = find_text(backend, text, app=app)
            if found:
                return found[0]
        found = find_element(backend, label=label, role=role, app=app)
        if found is not None:
            return found
        time.sleep(max(0.0, interval))
    raise ElementNotFoundError(label=label, role=role, text=text, timeout=timeout)


def find_text(
    backend: ComputerUseBackend,
    text: str,
    app: Optional[str] = None,
) -> List[UIElement]:
    """Locate ``text`` on screen.

    Prefers ``backend.find_text`` (OCR-backed) when the backend implements it;
    otherwise falls back to matching element labels from a capture (SOM/AX
    accessibility labels).
    """
    if hasattr(backend, "find_text"):
        try:
            found = backend.find_text(text, app=app)
            if found:
                return found
        except (NotImplementedError, Exception):
            pass
    for mode in ("som", "ax", "vision"):
        try:
            cap = backend.capture(mode=mode, app=app)
        except Exception:
            continue
        if not cap.elements:
            continue
        needle = text.lower()
        matched = [e for e in cap.elements if needle in e.label.lower()]
        if matched:
            return matched
    return []


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_after_action(
    backend: ComputerUseBackend,
    action: str,
    *,
    predicate: Optional[Callable[[CaptureResult], bool]] = None,
    expected_label: Optional[str] = None,
    expected_text: Optional[str] = None,
    app: Optional[str] = None,
    timeout: float = 10.0,
    interval: float = 0.5,
) -> CaptureResult:
    """Re-observe until ``predicate`` (or element/text match) holds.

    Returns the confirming CaptureResult. Raises VerificationTimeoutError when
    the expected state does not appear within ``timeout`` seconds.

    ``predicate`` receives the latest CaptureResult and returns bool. If no
    predicate is given, at minimum a fresh capture is returned (a smoke
    verification that the screen is still readable after the action).
    """
    deadline = time.monotonic() + timeout
    last: Optional[CaptureResult] = None
    while time.monotonic() < deadline:
        cap = backend.capture(mode="som", app=app)
        last = cap
        if expected_label:
            if _match_elements(cap.elements, label=expected_label):
                return cap
        if expected_text:
            if find_text(backend, expected_text, app=app):
                return cap
        if predicate is not None and predicate(cap):
            return cap
        time.sleep(max(0.0, interval))
    raise VerificationTimeoutError(action, timeout, last)


# ---------------------------------------------------------------------------
# Failure recovery
# ---------------------------------------------------------------------------

def retry_with_reobserve(
    backend: ComputerUseBackend,
    action_fn: Callable[[], Any],
    *,
    action: str = "action",
    max_retries: int = 2,
    verify: Optional[Callable[[], bool]] = None,
    interval: float = 0.5,
) -> Any:
    """Run ``action_fn`` with bounded retries, re-capturing between attempts.

    On each failure: call ``verify`` (a plain observe, default re-capture) to
    refresh state, then retry. Returns the first non-failing result, or the
    last result after ``max_retries`` attempts.

    A "failure" is ``action_fn`` returning an ``ActionResult`` with ``ok=False``,
    a JSON string whose payload reports ``ok: false`` (the shape produced by the
    tool layer's ``_text_response``), or raising an exception.
    """
    last: Any = None
    for attempt in range(max_retries + 1):
        try:
            result = action_fn()
        except Exception:
            result = None
        last = result
        if result is not None and not _result_is_failure(result):
            return result
        if attempt < max_retries:
            if verify is not None:
                verify()
            else:
                _safe_reobserve(backend, action=action)
            time.sleep(max(0.0, interval))
    return last


def _result_is_failure(result: Any) -> bool:
    """True when a result represents a failed action.

    Covers the two failure shapes the tool layer produces: an
    ``ActionResult`` with ``ok=False``, and a JSON string whose payload is
    ``{"ok": false, ...}``. Everything else (including ``{"ok": true}`` JSON
    and capture payloads without an ``ok`` key) counts as a success.
    """
    if isinstance(result, ActionResult):
        return not result.ok
    if isinstance(result, str):
        try:
            payload = json.loads(result)
        except (TypeError, ValueError):
            return False
        if isinstance(payload, dict):
            return payload.get("ok") is False
    return False


def _safe_reobserve(backend: ComputerUseBackend, action: str = "action") -> None:
    """Best-effort re-capture to refresh state between retries."""
    try:
        backend.capture(mode="som")
    except (NotImplementedError, AttributeError):
        return
