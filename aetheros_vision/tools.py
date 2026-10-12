"""AetherOS Vision — vision tool calling for agents.

Sync/async entry points that agents (and the gateway RPC layer) use to
inspect screenshots, read UI, locate buttons, verify workflows, and guide
automation. Each function returns plain dicts so it serialises cleanly for
both tool-result envelopes and JSON-RPC responses.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from aetheros_vision.config import VisionSettings, load_vision_settings
from aetheros_vision.models import (
    AnalysisResult,
    CaptureMode,
    OCRExtraction,
)

logger = logging.getLogger(__name__)


def _result_or_error(result: Any, error_key: str = "error") -> Dict[str, Any]:
    if hasattr(result, "to_dict"):
        return result.to_dict()
    return {error_key: str(result)}


def ocr_image(path: str, language: Optional[str] = None) -> Dict[str, Any]:
    from aetheros_vision.ocr import create_ocr_engine
    engine = create_ocr_engine()
    if not engine.is_available():
        return {"success": False, "error": "No OCR provider available"}
    return _ocr_to_dict(engine.extract(path, language=language))


def _ocr_to_dict(ocr) -> Dict[str, Any]:
    return {
        "success": ocr.success,
        "text": ocr.text,
        "confidence": round(ocr.confidence, 4),
        "language": ocr.language,
        "provider": ocr.provider,
        "processing_time_ms": round(ocr.processing_time_ms, 3),
        "error": ocr.error,
        "pages": ocr.pages,
        "blocks": [{"text": b.text, "confidence": round(b.confidence, 4), "box": b.box.to_dict() if hasattr(b, "box") and b.box else None} for b in ocr.blocks],
    }


def ocr_pdf(path: str) -> Dict[str, Any]:
    from aetheros_vision.ocr import create_ocr_engine
    engine = create_ocr_engine()
    if not engine.is_available():
        return {"success": False, "error": "No OCR provider available"}
    return _ocr_to_dict(engine.extract_pdf(path))


def ocr_languages() -> Dict[str, Any]:
    from aetheros_vision.ocr import create_ocr_engine
    engine = create_ocr_engine()
    return {"success": True, "provider": engine.provider_name(), "languages": engine.list_languages()}


def screen_capture(mode: str = "full_screen", monitor: int = 0, region: Optional[List[int]] = None) -> Dict[str, Any]:
    from aetheros_vision.capture import ScreenCaptureRuntime
    cap = ScreenCaptureRuntime()
    if not cap.is_available():
        return {"success": False, "error": "No screen capture backend available"}
    cap_mode = CaptureMode(mode) if mode in {m.value for m in CaptureMode} else CaptureMode.FULL_SCREEN
    region_tuple = tuple(region) if region and len(region) == 4 else None
    result = cap.capture(mode=cap_mode, monitor=monitor, region=region_tuple)
    return result.to_dict()


def analyze_screenshot(path: str, question: str = "") -> Dict[str, Any]:
    from aetheros_vision.images import ImageUnderstanding
    result = ImageUnderstanding().describe(path, question=question)
    return result.to_dict()


async def analyze_screenshot_async(path: str, question: str = "") -> Dict[str, Any]:
    from aetheros_vision.images import ImageUnderstanding
    result = await ImageUnderstanding().analyze(path, question=question)
    return result.to_dict()


def analyze_chart(path: str, question: str = "") -> Dict[str, Any]:
    from aetheros_vision.charts import ChartAnalyzer
    return ChartAnalyzer().analyze(path, question).to_dict()


def analyze_code_screenshot(path: str) -> Dict[str, Any]:
    from aetheros_vision.code import CodeScreenshotAnalyzer
    return CodeScreenshotAnalyzer().analyze(path).to_dict()


def analyze_math(path: str) -> Dict[str, Any]:
    from aetheros_vision.math import MathAnalyzer
    return MathAnalyzer().analyze(path).to_dict()


def extract_document(path: str) -> Dict[str, Any]:
    from aetheros_vision.documents import DocumentIntelligence
    return DocumentIntelligence().extract(path).to_dict()


def extract_video(path: str, max_frames: Optional[int] = None) -> Dict[str, Any]:
    from aetheros_vision.video import VideoUnderstanding
    return VideoUnderstanding().extract(path, max_frames=max_frames).to_dict()


def describe_ui(path: str) -> Dict[str, Any]:
    from aetheros_vision.desktop import DesktopVision
    return DesktopVision().analyze_screenshot(path).to_dict()


def locate_ui_element(path: str, query: str) -> Dict[str, Any]:
    from aetheros_vision.desktop import DesktopVision
    el = DesktopVision().find_element(path, query)
    if el is None:
        return {"success": False, "error": f"Element '{query}' not found"}
    return {"success": True, "element": el.to_dict()}


def vision_status() -> Dict[str, Any]:
    from aetheros_vision.runtime import VisionRuntime
    rt = VisionRuntime()
    rt.initialize()
    return rt.diagnostics().to_dict()
