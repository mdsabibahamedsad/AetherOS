"""Abstract backend interface for computer use.

Any implementation (cua-driver over MCP, pyautogui, noop, future Linux/Windows)
must return the shape described below. All methods synchronous; async is
handled inside the backend implementation if needed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class UIElement:
    """One interactable element on the current screen."""

    index: int                       # 1-based SOM index
    role: str                        # AX role (AXButton, AXTextField, ...)
    label: str = ""                  # AXTitle / AXDescription / AXValue snippet
    bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h (logical px)
    app: str = ""                    # owning bundle ID or app name
    pid: int = 0                     # owning process PID
    window_id: int = 0               # SkyLight / CG window ID
    attributes: Dict[str, Any] = field(default_factory=dict)

    def center(self) -> Tuple[int, int]:
        x, y, w, h = self.bounds
        return x + w // 2, y + h // 2


@dataclass
class CaptureResult:
    """Result of a screen capture call.

    At least one of png_b64 / elements is populated depending on capture mode:
      * mode="vision" → png_b64 only
      * mode="ax"     → elements only
      * mode="som"    → both (default): PNG already has numbered overlays
                         drawn by the backend, and `elements` holds the
                         matching index → element mapping.
    """

    mode: str
    width: int                      # screenshot width (logical px, pre-Anthropic-scale)
    height: int
    png_b64: Optional[str] = None
    elements: List[UIElement] = field(default_factory=list)
    # Optional: the target app/window the elements were captured for.
    app: str = ""
    window_title: str = ""
    # Raw bytes we sent to Anthropic, for token estimation.
    png_bytes_len: int = 0
    # Backend notes / diagnostics (e.g. element-model degradation warnings).
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    """Result of any action (click / type / scroll / drag / key / wait)."""

    ok: bool
    action: str
    message: str = ""                # human-readable summary
    # Optional trailing screenshot — set when the caller asked for a
    # post-action capture or the backend always returns one.
    capture: Optional[CaptureResult] = None
    # Arbitrary extra fields for debugging / telemetry.
    meta: Dict[str, Any] = field(default_factory=dict)


class ComputerUseBackend(ABC):
    """Lifecycle: `start()` before first use, `stop()` at shutdown."""

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the backend can be used on this host right now.

        Used by check_fn gating and by the post-setup wizard.
        """

    # ── Capture ─────────────────────────────────────────────────────
    @abstractmethod
    def capture(self, mode: str = "som", app: Optional[str] = None) -> CaptureResult: ...

    # ── Pointer actions ─────────────────────────────────────────────
    @abstractmethod
    def click(
        self,
        *,
        element: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",           # left | right | middle
        click_count: int = 1,
        modifiers: Optional[List[str]] = None,
    ) -> ActionResult: ...

    @abstractmethod
    def drag(
        self,
        *,
        from_element: Optional[int] = None,
        to_element: Optional[int] = None,
        from_xy: Optional[Tuple[int, int]] = None,
        to_xy: Optional[Tuple[int, int]] = None,
        button: str = "left",
        modifiers: Optional[List[str]] = None,
    ) -> ActionResult: ...

    @abstractmethod
    def scroll(
        self,
        *,
        direction: str,                 # up | down | left | right
        amount: int = 3,                # wheel ticks
        element: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        modifiers: Optional[List[str]] = None,
    ) -> ActionResult: ...

    # ── Keyboard ────────────────────────────────────────────────────
    @abstractmethod
    def type_text(self, text: str) -> ActionResult: ...

    @abstractmethod
    def key(self, keys: str) -> ActionResult:
        """Send a key combo, e.g. 'cmd+s', 'ctrl+alt+t', 'return'."""

    # ── Introspection ───────────────────────────────────────────────
    @abstractmethod
    def list_apps(self) -> List[Dict[str, Any]]:
        """Return running apps with bundle IDs, PIDs, window counts."""

    @abstractmethod
    def focus_app(self, app: str, raise_window: bool = False) -> ActionResult:
        """Route input to `app` (by name or bundle ID). Default: focus without raise."""

    # ── Native-value mutation ────────────────────────────────────────
    @abstractmethod
    def set_value(self, value: str, element: Optional[int] = None) -> ActionResult:
        """Set a native value on an element (e.g. AXPopUpButton selection).

        `element` is the 1-based SOM index returned by a prior capture call.
        """

    # ── Timing ──────────────────────────────────────────────────────
    def wait(self, seconds: float) -> ActionResult:
        """Default implementation: time.sleep."""
        import time
        time.sleep(max(0.0, min(seconds, 30.0)))
        return ActionResult(ok=True, action="wait", message=f"waited {seconds:.2f}s")

    # ══════════════════════════════════════════════════════════════════
    # Unified capability contract (ADDITIVE — non-breaking).
    #
    # The methods below are the *optional* extended capabilities a backend
    # may implement: clipboard, window management, hover/move, screen-size,
    # region capture, and OCR-backed element search. They exist on the ABC as
    # concrete defaults that raise NotImplementedError, so existing backends
    # (CuaDriverBackend, _NoopBackend) keep working without changes while new
    # platform adapters (Win32, Linux) provide real implementations.
    #
    # The tool layer catches NotImplementedError and returns a helpful error
    # instead of crashing, so a backend that does not support a capability
    # degrades gracefully.
    # ══════════════════════════════════════════════════════════════════

    # ── Screen geometry ──────────────────────────────────────────────
    def get_screen_size(self) -> Tuple[int, int]:
        """Return (width, height) of the full virtual screen in logical px.

        The virtual screen spans all monitors (may include negative origins
        on Windows multi-monitor layouts). Returns (0, 0) when unsupported.
        """
        raise NotImplementedError("get_screen_size not supported by this backend")

    # ── Pointer motion (hover, no click) ─────────────────────────────
    def move_mouse(self, x: int, y: int) -> ActionResult:
        """Move the pointer to logical screen coordinates (x, y) without clicking."""
        raise NotImplementedError("move_mouse not supported by this backend")

    # ── Clipboard ────────────────────────────────────────────────────
    def read_clipboard(self) -> ActionResult:
        """Return the current clipboard text (if any) in ``ActionResult.meta["text"]``."""
        raise NotImplementedError("read_clipboard not supported by this backend")

    def copy_clipboard(self, text: str) -> ActionResult:
        """Set the clipboard to ``text``."""
        raise NotImplementedError("copy_clipboard not supported by this backend")

    def clear_clipboard(self) -> ActionResult:
        """Empty the clipboard."""
        raise NotImplementedError("clear_clipboard not supported by this backend")

    # ── Window management ────────────────────────────────────────────
    def list_windows(self) -> List[Dict[str, Any]]:
        """Return visible top-level windows with title, pid, and rect."""
        raise NotImplementedError("list_windows not supported by this backend")

    def get_active_window(self) -> Dict[str, Any]:
        """Return the currently focused window (title, pid, rect) or {} if none."""
        raise NotImplementedError("get_active_window not supported by this backend")

    def focus_window(
        self,
        identifier: Optional[str] = None,
        title: Optional[str] = None,
        pid: Optional[int] = None,
    ) -> ActionResult:
        """Bring a window to the foreground.

        One of ``identifier`` (opaque window id from list_windows),
        ``title`` (case-insensitive substring match) or ``pid`` selects the
        window. Raises the window (unlike ``focus_app``, which routes input
        without stealing focus) — callers should be explicit about intent.
        """
        raise NotImplementedError("focus_window not supported by this backend")

    def minimize_window(
        self, identifier: Optional[str] = None, title: Optional[str] = None,
    ) -> ActionResult:
        """Minimize a window (iconify). Selection rules match ``focus_window``."""
        raise NotImplementedError("minimize_window not supported by this backend")

    def maximize_window(
        self, identifier: Optional[str] = None, title: Optional[str] = None,
    ) -> ActionResult:
        """Maximize (or restore) a window. Selection rules match ``focus_window``."""
        raise NotImplementedError("maximize_window not supported by this backend")
    def close_window(
        self, identifier: Optional[str] = None, title: Optional[str] = None,
    ) -> ActionResult:
        """Ask a window to close (graceful WM_CLOSE — not a force-kill)."""
        raise NotImplementedError("close_window not supported by this backend")

    # ── Region capture ───────────────────────────────────────────────
    def capture_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        mode: str = "vision",
    ) -> CaptureResult:
        """Capture a rectangular screen region at logical (x, y).

        ``mode`` is one of "vision" (plain PNG) / "som" / "ax" (both degrade
        to a plain capture when the backend has no element model for regions).
        """
        raise NotImplementedError("capture_region not supported by this backend")

    # ── OCR-backed element search ────────────────────────────────────
    def find_text(self, text: str, app: Optional[str] = None) -> List[UIElement]:
        """Locate occurrences of ``text`` on screen via OCR.

        Returns a list of UIElement whose ``label`` holds the matched text
        and whose ``bounds`` locate it in logical screen space. Empty list
        when the text is not visible.
        """
        raise NotImplementedError("find_text not supported by this backend")

    # ── App / system introspection ───────────────────────────────────
    def get_system_info(self) -> Dict[str, Any]:
        """Return OS/CPU/RAM/disk info for the host (read-only, no side effects).

        Shape: ``{"os", "os_version", "architecture", "session_type",
        "cpu_percent", "memory": {...}, "disk": {...}}``. Empty dict when
        the backend cannot report it.
        """
        raise NotImplementedError("get_system_info not supported by this backend")

    def get_capabilities(self) -> Dict[str, Any]:
        """Return the actions/capabilities this backend actually implements.

        Shape: ``{"os": str, "platform": {...}, "actions": [..]}`` — lets
        the model pick a strategy before acting.
        """
        raise NotImplementedError("get_capabilities not supported by this backend")

    # ── Application launch / close ───────────────────────────────────
    def launch_app(self, app: str, path: Optional[str] = None) -> ActionResult:
        """Launch ``app`` (by name, resolved via PATH) or the executable at
        ``path``. Returns the spawned PID in ``meta["pid"]`` when known."""
        raise NotImplementedError("launch_app not supported by this backend")

    def close_app(self, app: str, pid: Optional[int] = None) -> ActionResult:
        """Gracefully close ``app`` (by name) or the process ``pid``.

        Prefers a polite close request (WM_CLOSE / WM_DELETE_WINDOW) over a
        force-kill; force-kill is a last resort only when the app name and
        PID cannot be matched to a window.
        """
        raise NotImplementedError("close_app not supported by this backend")
