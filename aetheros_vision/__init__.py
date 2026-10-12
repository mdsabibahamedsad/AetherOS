"""AetherOS Vision — Multimodal Intelligence Engine.

The vision runtime for AetherOS: OCR, image understanding, document
intelligence, screen capture, desktop/browser vision, chart/code/math
analysis, video understanding, multimodal context, vision memory,
accessibility intelligence, security, and performance.

Usage::

    from aetheros_vision import get_vision_runtime

    runtime = get_vision_runtime()
    runtime.initialize()
    diagnostics = runtime.diagnostics()
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

from aetheros_vision.config import (
    CaptureSettings,
    OCRSettings,
    VideoSettings,
    VisionSettings,
    load_vision_settings,
)
from aetheros_vision.capture import (
    ScreenCaptureRuntime,
    CameraCaptureRuntime,
)
from aetheros_vision.models import (
    CameraCaptureMode,
    CameraCaptureResult,
    CaptureResult,
)
from aetheros_vision.models import (
    AnalysisResult,
    BoundingBox,
    CameraCaptureMode,
    CameraCaptureResult,
    CaptureResult,
    DetectedObject,
    DocumentExtraction,
    ImageInfo,
    MediaType,
    OCRExtraction,
    VisionDiagnostics,
    VisionMemoryKind,
    VisionMemoryRecord,
)

__version__ = "1.0.0"

__all__ = [
    "get_vision_runtime",
    "VisionRuntime",
    "VisionSettings",
    "VisionDiagnostics",
    "RuntimeState",
    "HealthCheck",
    "Subsystem",
    "AnalysisResult",
    "BoundingBox",
    "CameraCaptureMode",
    "CameraCaptureResult",
    "CaptureResult",
    "DetectedObject",
    "DocumentExtraction",
    "ImageInfo",
    "MediaType",
    "OCRExtraction",
    "VisionMemoryKind",
    "VisionMemoryRecord",
    "load_vision_settings",
    "OCRSettings",
    "CaptureSettings",
    "VideoSettings",
    "__version__",
    "get_vision_runtime",
    "VisionRuntime",
    "ScreenCaptureRuntime",
    "CameraCaptureRuntime",
    "CameraCaptureMode",
]

_runtime_lock = threading.Lock()
_runtime: Optional[VisionRuntime] = None


def get_vision_runtime() -> VisionRuntime:
    """Return the process-wide vision runtime singleton (lazily constructed)."""
    global _runtime
    if _runtime is None:
        with _runtime_lock:
            if _runtime is None:
                _runtime = VisionRuntime()
    return _runtime
