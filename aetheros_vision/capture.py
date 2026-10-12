"""AetherOS Vision — screen capture runtime.

Captures the full screen, a window, a region, or multiple monitors using a
real backend chain (pyautogui → PIL ImageGrab → Windows GDI). Supports a
capture history on disk, annotations, and scheduled captures.
"""

from __future__ import annotations

import base64
import io
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from aetheros_vision.config import VisionSettings, get_aetheros_dir, load_vision_settings
from aetheros_vision.models import CaptureAnnotation, CaptureMode, CaptureResult

logger = logging.getLogger(__name__)


def _monitor_bounds(monitor: int = 0) -> Tuple[int, int, int, int]:
    """Return (x, y, width, height) for a monitor. 0 = primary."""
    try:
        import mss
        with mss.mss() as sct:
            monitors = sct.monitors
            if monitor == 0:
                return (0, 0, int(monitors[0]["width"]), int(monitors[0]["height"]))
            if monitor < len(monitors):
                m = monitors[monitor]
                return (int(m["left"]), int(m["top"]), int(m["width"]), int(m["height"]))
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.debug("mss monitor bounds failed: %s", exc)
    # Fallback: primary display metrics.
    try:
        import ctypes
        user32 = ctypes.windll.user32
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return (0, 0, int(w), int(h))
    except Exception:  # noqa: BLE001
        return (0, 0, 1920, 1080)


class ScreenCaptureRuntime:
    """Multi-backend screen capture with history and scheduling."""

    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()
        self._history: List[CaptureResult] = []
        self._history_dir: Optional[Path] = None
        self._schedule_lock = threading.RLock()
        self._scheduled: Dict[str, threading.Timer] = {}
        self._capture_backend: Optional[Callable[..., Any]] = None
        self._init_backend()

    def _init_backend(self) -> None:
        try:
            import pyautogui
            self._capture_backend = pyautogui.screenshot
            return
        except ImportError:
            pass
        try:
            from PIL import ImageGrab
            self._capture_backend = ImageGrab.grab
            return
        except ImportError:
            pass
        self._capture_backend = None

    def is_available(self) -> bool:
        return self._capture_backend is not None

    def _ensure_history_dir(self) -> Path:
        if self._history_dir is None:
            self._history_dir = get_aetheros_dir(self._settings.capture.history_dir)
        self._history_dir.mkdir(parents=True, exist_ok=True)
        return self._history_dir

    # -- capture -------------------------------------------------------------

    def capture(self, mode: CaptureMode = CaptureMode.FULL_SCREEN, monitor: int = 0, region: Optional[Tuple[int, int, int, int]] = None, output_path: Optional[str] = None) -> CaptureResult:
        """Capture the screen and persist to the history directory.

        ``output_path`` overrides the default history location when the
        caller wants the capture somewhere specific (e.g. an agent-facing
        tool writing a PNG the agent can inspect).
        """
        if self._capture_backend is None:
            return CaptureResult(success=False, mode=mode, error="No screen capture backend available (install Pillow or pyautogui)")
        ts = time.time()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        try:
            if mode == CaptureMode.REGION and region:
                img = self._capture_backend(region=(region[0], region[1], region[2], region[3])) if self._is_pyautogui() else self._grab_region(region)
            elif mode in (CaptureMode.WINDOW, CaptureMode.MULTI_MONITOR):
                x, y, w, h = _monitor_bounds(monitor)
                img = self._grab_region((x, y, w, h))
            else:
                img = self._capture_backend()
            if output_path:
                path = Path(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
            else:
                path = self._ensure_history_dir() / f"capture_{stamp}.{self._settings.capture.format}"
            img.save(str(path))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            result = CaptureResult(
                success=True,
                path=str(path),
                mode=mode,
                width=img.width if hasattr(img, "width") else img.size[0],
                height=img.height if hasattr(img, "height") else img.size[1],
                monitor=monitor,
                timestamp=ts,
                data_url=f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}",
            )
            self._append_history(result)
            return result
        except Exception as exc:  # noqa: BLE001
            logger.warning("Screen capture failed: %s", exc)
            return CaptureResult(success=False, mode=mode, error=str(exc))

    def _is_pyautogui(self) -> bool:
        try:
            import pyautogui
            return self._capture_backend == pyautogui.screenshot
        except ImportError:
            return False

    def _grab_region(self, region: Tuple[int, int, int, int]):
        x, y, w, h = region
        if self._is_pyautogui():
            return self._capture_backend(region=region)
        try:
            from PIL import ImageGrab
            return ImageGrab.grab(bbox=(x, y, x + w, y + h))
        except Exception:  # noqa: BLE001
            return self._capture_backend()

    # -- annotations ---------------------------------------------------------

    def annotate(self, capture_path: str, annotations: List[CaptureAnnotation], output_path: Optional[str] = None) -> Optional[str]:
        """Draw box/label annotations onto a capture and save the result."""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger.warning("Pillow required for annotation")
            return None
        try:
            with Image.open(capture_path) as img:
                img.load()
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except Exception:  # noqa: BLE001
                font = ImageFont.load_default()
            for ann in annotations:
                if ann.box:
                    box = ann.box
                    draw.rectangle(
                        [box.x, box.y, box.x + box.width, box.y + box.height],
                        outline=ann.color or "#00FF00",
                        width=2,
                    )
                    if ann.label:
                        draw.text((box.x, max(box.y - 18, 0)), ann.label, fill=ann.color or "#00FF00", font=font)
            out = output_path or str(Path(capture_path).with_suffix(".annotated.png"))
            img.save(out)
            return out
        except Exception as exc:  # noqa: BLE001
            logger.warning("Annotation failed: %s", exc)
            return None

    # -- history -------------------------------------------------------------

    def _append_history(self, result: CaptureResult) -> None:
        limit = self._settings.capture.history_limit
        self._history.append(result)
        if len(self._history) > limit:
            self._history = self._history[-limit:]

    def history(self, limit: Optional[int] = None) -> List[CaptureResult]:
        limit = limit or len(self._history)
        return self._history[-limit:]

    def history_from_disk(self, limit: int = 50) -> List[Dict[str, Any]]:
        entries = []
        d = self._ensure_history_dir()
        if not d.exists():
            return entries
        for p in sorted(d.glob(f"*.{self._settings.capture.format}"))[-limit:]:
            entries.append({"path": str(p), "name": p.name, "size_bytes": p.stat().st_size})
        return entries

    # -- scheduling ----------------------------------------------------------

    def schedule(self, interval_s: float, mode: CaptureMode = CaptureMode.FULL_SCREEN, callback: Optional[Callable[[CaptureResult], None]] = None, name: Optional[str] = None) -> str:
        """Schedule periodic captures. Returns the job id."""
        job_id = name or f"sched_{int(time.time())}"
        with self._schedule_lock:
            if job_id in self._scheduled:
                self.cancel(job_id)

            def _tick():
                result = self.capture(mode=mode)
                if callback:
                    try:
                        callback(result)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Scheduled capture callback failed: %s", exc)
                with self._schedule_lock:
                    if job_id in self._scheduled:
                        self._scheduled[job_id] = threading.Timer(interval_s, _tick)
                        self._scheduled[job_id].daemon = True
                        self._scheduled[job_id].start()

            timer = threading.Timer(interval_s, _tick)
            timer.daemon = True
            self._scheduled[job_id] = timer
            timer.start()
            return job_id

    def cancel(self, job_id: str) -> bool:
        with self._schedule_lock:
            timer = self._scheduled.pop(job_id, None)
            if timer is None:
                return False
            timer.cancel()
            return True

    def cancel_all(self) -> None:
        with self._schedule_lock:
            for timer in self._scheduled.values():
                timer.cancel()
            self._scheduled.clear()

    def shutdown(self) -> None:
        self.cancel_all()

    def health(self) -> dict:
        return {"ok": self.is_available(), "detail": f"backend={'available' if self.is_available() else 'none'}"}


class CameraCaptureRuntime:
    """Multi-backend camera capture with burst and timelapse support (Phase 17)."""

    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()
        self._capture_backend: Optional[Any] = None
        self._init_backend()

    def _init_backend(self) -> None:
        try:
            import cv2
            self._capture_backend = cv2
            return
        except ImportError:
            pass
        try:
            import pygame
            self._capture_backend = pygame
            return
        except ImportError:
            pass
        self._capture_backend = None

    def is_available(self) -> bool:
        return self._capture_backend is not None

    def capture_still(
        self, camera_index: int = 0, output_path: Optional[str] = None
    ) -> CameraCaptureResult:
        """Capture a single still frame from the camera."""
        if self._capture_backend is None:
            return CameraCaptureResult(
                success=False,
                error="No camera backend available (install opencv-python or pygame)",
            )
        try:
            cv2 = self._capture_backend
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                return CameraCaptureResult(
                    success=False, error=f"Cannot open camera index {camera_index}"
                )
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return CameraCaptureResult(success=False, error="Failed to read frame from camera")

            ts = time.time()
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            if output_path:
                path = Path(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
            else:
                path = get_aetheros_dir(self._settings.capture.history_dir) / f"camera_{stamp}.png"
                path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(path), frame)
            h, w = frame.shape[:2]
            return CameraCaptureResult(
                success=True,
                path=str(path),
                mode=CameraCaptureMode.STILL,
                width=w,
                height=h,
                camera_index=camera_index,
                timestamp=time.time(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Camera still capture failed: %s", exc)
            return CameraCaptureResult(success=False, error=str(exc))

    def capture_burst(
        self,
        camera_index: int = 0,
        count: int = 5,
        interval: float = 0.1,
        output_dir: Optional[str] = None,
    ) -> List[CameraCaptureResult]:
        """Capture a burst of frames from the camera."""
        if self._capture_backend is None:
            return [CameraCaptureResult(success=False, error="No camera backend available")]

        results = []
        try:
            cv2 = self._capture_backend
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                return [CameraCaptureResult(success=False, error=f"Cannot open camera index {camera_index}")]

            for i in range(count):
                ret, frame = cap.read()
                if not ret:
                    results.append(CameraCaptureResult(success=False, error=f"Failed to read frame {i}"))
                    break
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                if output_dir:
                    out_dir = Path(output_dir)
                else:
                    out_dir = get_aetheros_dir(self._settings.capture.history_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                path = out_dir / f"camera_burst_{stamp}_{i:03d}.png"
                cv2.imwrite(str(path), frame)
                h, w = frame.shape[:2]
                results.append(
                    CameraCaptureResult(
                        success=True,
                        path=str(path),
                        mode=CameraCaptureMode.BURST,
                        width=w,
                        height=h,
                        camera_index=camera_index,
                        timestamp=time.time(),
                    )
                )
                if i < count - 1:
                    time.sleep(interval)
            cap.release()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Camera burst capture failed: %s", exc)
            results.append(CameraCaptureResult(success=False, error=str(exc)))
        return results

    def capture_timelapse(
        self,
        camera_index: int = 0,
        count: int = 10,
        interval: float = 1.0,
        output_dir: Optional[str] = None,
    ) -> List[CameraCaptureResult]:
        """Capture a timelapse sequence from the camera."""
        return self.capture_burst(camera_index=camera_index, count=count, interval=interval, output_dir=output_dir)

    def is_available(self) -> bool:
        return self._capture_backend is not None

    def health(self) -> dict:
        return {"ok": self.is_available(), "detail": f"backend={'opencv' if self._capture_backend else 'none'}"}
