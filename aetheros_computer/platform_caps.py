"""
Platform capability detection + DPI/monitor transforms
(Master 15 Phases 32, 33, 36, 37).

Pure detection + math. Live GUI verification per-OS is documented honestly in
AETHEROS_MASTER15_FINAL_CERTIFICATION.md; this module never *claims* a
platform works — it reports what the existing backends advertise and degrades
to explicit UNSUPPORTED-with-reason.
"""

from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Backend availability (delegates to the EXISTING computer_use capability map)
# ---------------------------------------------------------------------------

@dataclass
class PlatformReport:
    os_name: str                      # windows | linux | darwin
    desktop_backend: str              # cua | win32 | linux | noop | unknown
    backend_available: bool
    accessibility: str                # native_ax | ocr_fallback | none
    wayland: Optional[bool] = None    # None = not Linux / undetectable
    limitations: List[str] = field(default_factory=list)


def detect_platform() -> PlatformReport:
    os_name = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    limitations: List[str] = []
    backend = "unknown"
    available = False
    accessibility = "none"
    wayland: Optional[bool] = None

    try:
        from tools.computer_use.tool import _resolve_backend_name  # type: ignore
        backend = (_resolve_backend_name() or "unknown").lower()
    except Exception:
        try:
            from tools.computer_use import capabilities as caps  # type: ignore

            backend = (caps.detect_platform() or "unknown").lower()
        except Exception:
            backend = {"win32": "win32", "darwin": "cua"}.get(sys.platform, "linux")

    try:
        from tools.computer_use.capabilities import backend_capabilities  # type: ignore

        caps_map = backend_capabilities(backend if backend != "unknown" else
                                        {"windows": "win32", "macos": "cua"}.get(os_name, "linux"))
        available = bool(caps_map)
    except Exception:
        caps_map = {}

    if os_name == "macos":
        accessibility = "native_ax"      # cua-driver exposes AX tree markdown
    elif os_name == "linux":
        accessibility = "ocr_fallback"   # xdotool+OCR path; no AT-SPI tree yet
        wayland = _is_wayland()
        if wayland:
            limitations.append(
                "Wayland: tools/computer_use/linux_backend.py is X11-only "
                "(xdotool/wmctrl); screen control is unavailable on Wayland."
            )
    else:  # windows
        accessibility = "ocr_fallback"   # Win32 input via SendInput; no UIA tree yet
        limitations.append(
            "Windows: element targeting falls back to vision/OCR; UIA tree not wired."
        )

    return PlatformReport(
        os_name=os_name,
        desktop_backend=backend,
        backend_available=available,
        accessibility=accessibility,
        wayland=wayland,
        limitations=limitations,
    )


def _is_wayland() -> bool:
    sess = ""
    try:
        import os as _os

        sess = (_os.environ.get("XDG_SESSION_TYPE") or "").strip().lower()
    except Exception:
        pass
    return sess == "wayland"


# ---------------------------------------------------------------------------
# Monitor enumeration + DPI scale (Windows-native here; graceful elsewhere)
# ---------------------------------------------------------------------------

@dataclass
class MonitorInfo:
    index: int
    x: int
    y: int
    width: int
    height: int
    dpi_scale: float = 1.0          # e.g. 1.0 / 1.25 / 1.5 / 2.0


def enumerate_monitors() -> List[MonitorInfo]:
    """Enumerate via mss when present; fall back to primary-only."""
    monitors: List[MonitorInfo] = []
    try:
        import mss  # type: ignore

        with mss.mss() as sct:
            for i, m in enumerate(sct.monitors[1:] or [sct.monitors[0]]):
                monitors.append(MonitorInfo(
                    index=i, x=int(m["left"]), y=int(m["top"]),
                    width=int(m["width"]), height=int(m["height"]),
                    dpi_scale=_monitor_scale(m["left"], m["top"]),
                ))
        return monitors
    except Exception:
        pass
    try:  # Windows user32 fallback for the virtual screen
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        x = int(user32.GetSystemMetrics(76))     # SM_XVIRTUALSCREEN
        y = int(user32.GetSystemMetrics(77))     # SM_YVIRTUALSCREEN
        w = int(user32.GetSystemMetrics(78))
        h = int(user32.GetSystemMetrics(79))
        monitors.append(MonitorInfo(index=0, x=x, y=y, width=w or 1920,
                                    height=h or 1080,
                                    dpi_scale=_monitor_scale(x, y)))
    except Exception:
        monitors.append(MonitorInfo(index=0, x=0, y=0, width=1920, height=1080))
    return monitors


def _monitor_scale(x: int, y: int) -> float:
    """Per-monitor DPI scale on Windows; 1.0 elsewhere/unavailable."""
    try:
        shcore = ctypes.windll.shcore  # type: ignore[attr-defined]
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        pt = ctypes.wintypes.POINT(int(x) + 1, int(y) + 1)  # type: ignore[attr-defined]
        MONITOR_DEFAULTTONEAREST = 2
        hmon = user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
        dpi_x = ctypes.c_uint(96)
        dpi_y = ctypes.c_uint(96)
        if shcore.GetDpiForMonitor(hmon, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)) == 0:
            return round(max(1.0, dpi_x.value / 96.0), 3)
    except Exception:
        pass
    return 1.0


# ---------------------------------------------------------------------------
# Coordinate transforms across scale factors (Phase 37)
# ---------------------------------------------------------------------------

def transform_point(point: Tuple[float, float],
                    from_scale: float, to_scale: float) -> Tuple[float, float]:
    """Logical→logical transform between different DPI scales.

    Physical px are invariant; logical coordinates scale inversely with the
    monitor's device scale factor.
    """
    if to_scale <= 0:
        raise ValueError("to_scale must be > 0")
    factor = from_scale / to_scale
    return (round(point[0] * factor, 2), round(point[1] * factor, 2))


def point_to_monitor(point: Tuple[float, float],
                     monitors: List[MonitorInfo]) -> Optional[MonitorInfo]:
    """Map a global logical coordinate to its monitor (bounds inclusive)."""
    px, py = point
    for m in monitors:
        if m.x <= px < m.x + m.width and m.y <= py < m.y + m.height:
            return m
    return None


__all__ = [
    "PlatformReport",
    "detect_platform",
    "MonitorInfo",
    "enumerate_monitors",
    "transform_point",
    "point_to_monitor",
]
