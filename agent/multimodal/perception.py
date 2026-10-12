"""Perception Layer (Phases 5-45 of Master Prompt 10).

A thin routing layer that delegates media understanding to Aetheros' PRODUCTION
tools (vision_tools, transcription_tools, tts_tool, aetheros_vision,
computer_use).  It never re-implements their internals; it selects the right
production surface per modality and enriches results with provenance +
confidence.

Each operation returns a plain dict with ``success`` and either an analysis
payload or an ``error`` string, so it is safe to call from CLI / API / skills.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from agent.multimodal.media_abstraction import MediaObject, MediaType
from agent.multimodal.provenance import ConfidenceTracker, ProvenanceTracker
from agent.multimodal.security import MediaRiskAssessment, assess_extracted_text

logger = logging.getLogger(__name__)

_VISION_MODALITIES = {
    MediaType.IMAGE: "vision",
    MediaType.SCREEN: "vision",
    MediaType.CAMERA: "vision",
    MediaType.VIDEO: "vision",
    MediaType.DOCUMENT: "vision",
}

_AUDIO_MODALITIES = {
    MediaType.AUDIO: "transcription",
}

_SCREEN_CAPTURE_MODES = ("full_screen", "window", "region", "multi_monitor")

_CAMERA_CAPTURE_MODES = ("still", "burst", "timelapse")


def _require_source(media: MediaObject, tool: str) -> str:
    if not media.source or not os.path.exists(media.source):
        raise FileNotFoundError(f"{tool}: source file missing: {media.source!r}")
    return media.source


# ---------------------------------------------------------------------------
# Image / Screen understanding (Phases 5, 9, 40, 42)
# ---------------------------------------------------------------------------


def analyze_image(
    media: MediaObject,
    question: str = "Describe this image in detail.",
    tracker: Optional[ProvenanceTracker] = None,
    confidence: Optional[ConfidenceTracker] = None,
) -> Dict[str, Any]:
    """Delegate image/screen understanding to the production vision tool."""
    path = _require_source(media, "analyze_image")
    try:
        from tools.vision_tools import vision_analyze_tool

        # vision_analyze_tool is async; run via asyncio in the caller's loop.
        import asyncio

        try:
            asyncio.get_running_loop()
            raise RuntimeError("must be called from non-async context")
        except RuntimeError:
            result = asyncio.run(vision_analyze_tool(path, question))
    except Exception as e:
        logger.warning("analyze_image fell back to local descriptor: %s", e)
        result = _local_image_description(path, question)

    payload = _normalize_tool_result(result)
    if tracker is not None:
        tracker.record(
            claim=payload.get("analysis", ""),
            media=media,
            processor="vision_analyze_tool",
            confidence=payload.get("confidence", 0.5),
        )
    if confidence is not None:
        confidence.set("vision", payload.get("confidence", 0.5))
    return payload


def _local_image_description(path: str, question: str) -> Dict[str, Any]:
    """Best-effort local fallback using aetheros_vision heuristics (offline mode)."""
    try:
        from aetheros_vision.images import ImageUnderstanding

        ui = ImageUnderstanding()
        result = ui.describe(path)
        text = result.get("description") or result.get("text") or ""
        return {
            "success": True,
            "analysis": f"{text}\n\nQuestion: {question}",
            "confidence": 0.4,
            "provider": "local_aetheros_vision",
            "mode": "local",
        }
    except Exception as e:
        return {"success": False, "error": f"no vision processor available: {e}"}


# ---------------------------------------------------------------------------
# Screen Capture (Phase 16)
# ---------------------------------------------------------------------------


def capture_screen(
    mode: str = "full_screen",
    output_path: Optional[str] = None,
    region: Optional[List[int]] = None,
    monitor: int = 0,
    tracker: Optional[ProvenanceTracker] = None,
    confidence: Optional[ConfidenceTracker] = None,
) -> Dict[str, Any]:
    """Capture the screen using the production screen capture runtime (Phase 16)."""
    if mode not in _SCREEN_CAPTURE_MODES:
        return {"success": False, "error": f"unknown screen capture mode: {mode}"}
    try:
        from aetheros_vision.capture import ScreenCaptureRuntime, CaptureMode
    except Exception as e:
        return {"success": False, "error": f"screen capture runtime unavailable: {e}"}

    cap = ScreenCaptureRuntime()
    if not cap.is_available():
        return {"success": False, "error": "No screen capture backend available (install Pillow or pyautogui)"}

    mode_enum = CaptureMode(mode)
    region_tuple = tuple(region) if region and len(region) == 4 else None

    try:
        result = cap.capture(mode=CaptureMode(mode), region=region_tuple, monitor=monitor, output_path=output_path)
    except Exception as e:
        return {"success": False, "error": f"screen capture failed: {e}"}

    if not result.success:
        return {"success": False, "error": result.error or "Screen capture failed"}

    payload = {
        "success": True,
        "path": result.path,
        "width": result.width,
        "height": result.height,
        "mode": result.mode.value,
        "monitor": result.monitor,
        "timestamp": result.timestamp,
    }

    if tracker is not None:
        tracker.record(
            claim=f"screen capture: {result.path} ({result.width}x{result.height})",
            media=None,
            processor="aetheros_vision.capture.ScreenCaptureRuntime",
            confidence=0.9,
        )
    if confidence is not None:
        confidence.set("screen_capture", 0.9)
    return payload


def list_screen_captures(limit: int = 50) -> Dict[str, Any]:
    """List recent screen captures from history."""
    try:
        from aetheros_vision.capture import ScreenCaptureRuntime
    except Exception as e:
        return {"success": False, "error": f"screen capture runtime unavailable: {e}"}

    cap = ScreenCaptureRuntime()
    history = cap.history_from_disk(limit=limit)
    return {"success": True, "captures": history, "count": len(history)}


# ---------------------------------------------------------------------------
# Camera Capture (Phase 17)
# ---------------------------------------------------------------------------


def capture_camera(
    mode: str = "still",
    output_path: Optional[str] = None,
    camera_index: int = 0,
    count: int = 1,
    interval: float = 0.0,
    tracker: Optional[ProvenanceTracker] = None,
    confidence: Optional[ConfidenceTracker] = None,
) -> Dict[str, Any]:
    """Capture from a camera using the production camera capture (Phase 17).

    Modes: 'still' (single frame), 'burst' (multiple frames), 'timelapse' (frames over time).
    """
    if mode not in _CAMERA_CAPTURE_MODES:
        return {"success": False, "error": f"unknown camera capture mode: {mode}"}
    try:
        from aetheros_vision.capture import CameraCaptureRuntime
    except Exception as e:
        return {"success": False, "error": f"camera capture runtime unavailable: {e}"}

    cam = CameraCaptureRuntime()
    if not cam.is_available():
        return {"success": False, "error": "No camera capture backend available (install opencv-python)"}

    paths = []
    try:
        if mode == "still":
            result = cam.capture_still(camera_index=camera_index, output_path=output_path)
            if result.success:
                paths.append(result.path)
        elif mode == "burst":
            results = cam.capture_burst(camera_index=camera_index, count=count, interval=interval)
            for r in results:
                if r.success:
                    paths.append(r.path)
        elif mode == "timelapse":
            results = cam.capture_timelapse(camera_index=camera_index, count=count, interval=interval)
            for r in results:
                if r.success:
                    paths.append(r.path)
    except Exception as e:
        return {"success": False, "error": f"camera capture failed: {e}"}

    if not paths:
        return {"success": False, "error": "No frames captured"}

    payload = {
        "success": True,
        "paths": paths,
        "count": len(paths),
        "mode": mode,
        "camera_index": camera_index,
    }

    if tracker is not None:
        tracker.record(
            claim=f"camera capture: {len(paths)} frame(s) via mode={mode}",
            media=None,
            processor="aetheros_vision.capture.CameraCaptureRuntime",
            confidence=0.85,
        )
    if confidence is not None:
        confidence.set("camera_capture", 0.85)
    return payload


def _normalize_tool_result(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        import json

        try:
            return json.loads(result)
        except Exception:
            return {"success": True, "analysis": result, "confidence": 0.5}
    return {"success": True, "analysis": str(result), "confidence": 0.5}


# ---------------------------------------------------------------------------
# OCR (Phases 11-12)
# ---------------------------------------------------------------------------


def ocr_media(
    media: MediaObject,
    language: Optional[str] = None,
    tracker: Optional[ProvenanceTracker] = None,
    confidence: Optional[ConfidenceTracker] = None,
) -> Dict[str, Any]:
    """Run OCR on an image/screen/document using the production OCR engine."""
    path = _require_source(media, "ocr_media")
    try:
        from aetheros_vision.ocr import create_ocr_engine
    except Exception as e:
        return {"success": False, "error": f"OCR engine unavailable: {e}"}

    engine = create_ocr_engine()
    if not engine.is_available():
        return {"success": False, "error": "No OCR provider available (install tesseract or configure cloud OCR)"}

    if _is_pdf(media):
        result = engine.extract_pdf(path, language=language)
    else:
        result = engine.extract(path, language=language)
    text = getattr(result, "text", "") or ""
    conf = getattr(result, "confidence", 0.5) or 0.5
    blocks = getattr(result, "blocks", []) or []
    pages = getattr(result, "pages", None) or []

    # Adversarial media defense on extracted text (Phase 66).
    risk = assess_extracted_text(str(text), media_type=media.type.value)
    if tracker is not None:
        tracker.record(
            claim=str(text)[:1000], media=media, processor="aetheros_vision.ocr",
            confidence=float(conf), page=pages[0].get("page_number") if pages else None,
        )
    if confidence is not None:
        confidence.set("ocr", float(conf))
    return {
        "success": True,
        "text": str(text),
        "confidence": float(conf),
        "blocks": [b.to_dict() if hasattr(b, "to_dict") else str(b) for b in blocks],
        "pages": pages,
        "provider": engine.provider_name(),
        "media_trust": risk.trust.value,
        "injection_findings": risk.findings,
    }


def _is_pdf(media: MediaObject) -> bool:
    return media.mime_type == "application/pdf" or (media.source or "").lower().endswith(".pdf")


# ---------------------------------------------------------------------------
# Document understanding (Phases 13-17)
# ---------------------------------------------------------------------------


def extract_document(
    media: MediaObject,
    tracker: Optional[ProvenanceTracker] = None,
    confidence: Optional[ConfidenceTracker] = None,
) -> Dict[str, Any]:
    """Extract text/tables/headings from documents via production DocumentIntelligence."""
    path = _require_source(media, "extract_document")
    try:
        from aetheros_vision.documents import DocumentIntelligence

        di = DocumentIntelligence()
        result = di.extract(path)
    except Exception as e:
        return {"success": False, "error": f"document extraction failed: {e}"}

    if isinstance(result, dict):
        payload = result
    else:
        payload = {"text": getattr(result, "text", ""), "tables": getattr(result, "tables", []),
                   "metadata": getattr(result, "metadata", {})}
    if tracker is not None:
        tracker.record(
            claim=str(payload.get("text", ""))[:1000],
            media=media,
            processor="aetheros_vision.documents.DocumentIntelligence",
            confidence=0.7,
        )
    if confidence is not None:
        confidence.set("document", 0.7)
    payload.setdefault("success", True)
    return payload


# ---------------------------------------------------------------------------
# Audio / STT / TTS (Phases 18-30)
# ---------------------------------------------------------------------------


def transcribe_audio(
    media: MediaObject,
    model: Optional[str] = None,
    tracker: Optional[ProvenanceTracker] = None,
    confidence: Optional[ConfidenceTracker] = None,
) -> Dict[str, Any]:
    """Transcribe audio via the production STT pipeline."""
    path = _require_source(media, "transcribe_audio")
    try:
        from tools.transcription_tools import transcribe_audio as _transcribe

        result = _transcribe(path, model=model)
    except Exception as e:
        return {"success": False, "error": f"transcription failed: {e}"}

    if isinstance(result, dict):
        payload = result
    else:
        payload = {"transcript": str(result), "provider": "unknown"}
    text = str(payload.get("transcript", ""))
    # Untrusted spoken input (Phase 25/69): assess for embedded instructions.
    risk = assess_extracted_text(text, media_type="audio")
    if tracker is not None:
        tracker.record(
            claim=text, media=media, processor="transcription_tools",
            confidence=payload.get("confidence", 0.5),
        )
    if confidence is not None:
        confidence.set("stt", payload.get("confidence", 0.5))
    payload["media_trust"] = risk.trust.value
    payload["injection_findings"] = risk.findings
    return payload


def synthesize_speech(
    text: str,
    voice: Optional[str] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Synthesize speech via the production TTS tool (Phase 26)."""
    try:
        from tools.tts_tool import text_to_speech_tool
    except Exception as e:
        return {"success": False, "error": f"TTS unavailable: {e}"}
    try:
        result = text_to_speech_tool(text, output_path=output_path)
    except Exception as e:
        return {"success": False, "error": f"TTS failed: {e}"}
    if isinstance(result, str):
        import json

        try:
            payload = json.loads(result)
        except Exception:
            payload = {"success": True, "output": result}
    else:
        payload = result
    return _normalize_tool_result(payload)


# ---------------------------------------------------------------------------
# Video (Phases 31-39)
# ---------------------------------------------------------------------------

_FRAME_SAMPLING_MODES = ("uniform", "scene_change", "event", "adaptive")


def extract_video_frames(
    media: MediaObject,
    max_frames: int = 24,
    mode: str = "uniform",
    tracker: Optional[ProvenanceTracker] = None,
) -> Dict[str, Any]:
    """Extract frames from a video with a sampling strategy (Phase 33)."""
    if mode not in _FRAME_SAMPLING_MODES:
        return {"success": False, "error": f"unknown sampling mode: {mode}"}
    path = _require_source(media, "extract_video_frames")
    try:
        from aetheros_vision.video import VideoUnderstanding

        vu = VideoUnderstanding()
        result = vu.extract(path, max_frames=max_frames)
    except Exception as e:
        return {"success": False, "error": f"video extraction failed: {e}"}

    frames = result.get("frames", []) if isinstance(result, dict) else getattr(result, "frames", [])
    key_moments = result.get("key_moments", []) if isinstance(result, dict) else getattr(result, "key_moments", [])
    if tracker is not None:
        tracker.record(
            claim=f"video {path}: {len(frames)} frames sampled ({mode})",
            media=media, processor="aetheros_vision.video.VideoUnderstanding", confidence=0.6,
        )
    return {
        "success": True,
        "frames": frames,
        "frame_count": len(frames),
        "key_moments": key_moments,
        "mode": mode,
        "timeline": result.get("timeline", []) if isinstance(result, dict) else [],
    }


def analyze_video(
    media: MediaObject,
    question: str = "Describe what happens in this video.",
    tracker: Optional[ProvenanceTracker] = None,
    confidence: Optional[ConfidenceTracker] = None,
) -> Dict[str, Any]:
    """Analyze a video via the production video_analyze tool (Phase 31)."""
    path = _require_source(media, "analyze_video")
    try:
        from tools.vision_tools import video_analyze_tool

        import asyncio

        try:
            asyncio.get_running_loop()
            raise RuntimeError("must be called from non-async context")
        except RuntimeError:
            result = asyncio.run(video_analyze_tool(path, question))
    except Exception as e:
        return {"success": False, "error": f"video analysis failed: {e}"}
    payload = _normalize_tool_result(result)
    if tracker is not None:
        tracker.record(
            claim=payload.get("analysis", ""), media=media,
            processor="video_analyze_tool", confidence=payload.get("confidence", 0.5),
        )
    if confidence is not None:
        confidence.set("video", payload.get("confidence", 0.5))
    return payload


# ---------------------------------------------------------------------------
# Screen Understanding Pipeline (Phase 20)
# ---------------------------------------------------------------------------


def understand_screen(
    media: MediaObject,
    question: str = "What is on this screen?",
    tracker: Optional[ProvenanceTracker] = None,
    confidence: Optional[ConfidenceTracker] = None,
) -> Dict[str, Any]:
    """Understand screen content via production screen_understand tool (Phase 20).

    Uses the production screen_understand tool for UI element detection,
    text reading, and workflow analysis.
    """
    path = _require_source(media, "understand_screen")
    try:
        from tools.vision_tools import screen_understand_tool
    except Exception as e:
        return {"success": False, "error": f"screen_understand tool unavailable: {e}"}

    try:
        result = asyncio.run(screen_understand_tool(path, question))
    except Exception as e:
        logger.warning("understand_screen fell back to local descriptor: %s", e)
        result = _local_screen_description(path, question)

    payload = _normalize_tool_result(result)
    if tracker is not None:
        tracker.record(
            claim=payload.get("analysis", ""),
            media=media,
            processor="screen_understand_tool",
            confidence=payload.get("confidence", 0.5),
        )
    if confidence is not None:
        confidence.set("screen_understand", payload.get("confidence", 0.5))
    return payload


def _local_screen_description(path: str, question: str) -> Dict[str, Any]:
    """Best-effort local fallback for screen understanding (offline mode)."""
    try:
        from aetheros_vision.screen import ScreenUnderstanding
    except Exception as e:
        return {"success": False, "error": f"no screen understanding processor: {e}"}

    try:
        su = ScreenUnderstanding()
        result = su.understand(path, question)
        text = result.get("analysis") or result.get("description") or ""
        return {
            "success": True,
            "analysis": f"{text}\n\nQuestion: {question}",
            "confidence": 0.35,
            "provider": "local_aetheros_vision",
            "mode": "local",
        }
    except Exception as e:
        return {"success": False, "error": f"local screen understanding failed: {e}"}


# ---------------------------------------------------------------------------
# Camera Understanding Pipeline (Phase 21)
# ---------------------------------------------------------------------------


def understand_camera(
    media: MediaObject,
    question: str = "What does the camera see?",
    tracker: Optional[ProvenanceTracker] = None,
    confidence: Optional[ConfidenceTracker] = None,
) -> Dict[str, Any]:
    """Understand camera feed via production vision tool (Phase 21).

    Analyzes camera frames for objects, scenes, activities, and text.
    """
    path = _require_source(media, "understand_camera")
    try:
        from tools.vision_tools import vision_analyze_tool
    except Exception as e:
        return {"success": False, "error": f"vision_analyze tool unavailable: {e}"}

    try:
        result = asyncio.run(vision_analyze_tool(path, question))
    except Exception as e:
        logger.warning("understand_camera fell back to local descriptor: %s", e)
        result = _local_camera_description(path, question)

    payload = _normalize_tool_result(result)
    if tracker is not None:
        tracker.record(
            claim=payload.get("analysis", ""),
            media=media,
            processor="vision_analyze_tool",
            confidence=payload.get("confidence", 0.5),
        )
    if confidence is not None:
        confidence.set("camera_understand", payload.get("confidence", 0.5))
    return payload


def _local_camera_description(path: str, question: str) -> Dict[str, Any]:
    """Best-effort local fallback for camera understanding (offline mode)."""
    try:
        from aetheros_vision.camera import CameraUnderstanding
    except Exception as e:
        return {"success": False, "error": f"no camera understanding processor: {e}"}

    try:
        cu = CameraUnderstanding()
        result = cu.understand(path, question)
        text = result.get("analysis") or result.get("description") or ""
        return {
            "success": True,
            "analysis": f"{text}\n\nQuestion: {question}",
            "confidence": 0.3,
            "provider": "local_aetheros_vision",
            "mode": "local",
        }
    except Exception as e:
        return {"success": False, "error": f"local camera understanding failed: {e}"}


# ---------------------------------------------------------------------------
# Unified entry point (Phase 46/83: modality -> tool routing)
# ---------------------------------------------------------------------------


def perceive(
    media: MediaObject,
    question: str = "",
    trackers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Route a media object to the right perception tool by modality.

    ``trackers`` may carry ``provenance`` and ``confidence`` trackers.
    """
    trackers = trackers or {}
    pt: Optional[ProvenanceTracker] = trackers.get("provenance")
    ct: Optional[ConfidenceTracker] = trackers.get("confidence")

    if media.type in _VISION_MODALITIES:
        if media.type == MediaType.VIDEO:
            return analyze_video(media, question or "Describe this video.", pt, ct)
        if media.type == MediaType.SCREEN:
            return understand_screen(media, question or "What is on this screen?", pt, ct)
        if media.type == MediaType.CAMERA:
            return understand_camera(media, question or "What does the camera see?", pt, ct)
        return analyze_image(media, question or "Describe this image.", pt, ct)
    if media.type in _AUDIO_MODALITIES:
        return transcribe_audio(media, tracker=pt, confidence=ct)
    if media.type == MediaType.DOCUMENT:
        return extract_document(media, pt, ct)
    if media.type == MediaType.TEXT:
        return {"success": True, "analysis": str(media.metadata.get("content", "")), "confidence": 1.0}
    if media.type == MediaType.STRUCTURED_DATA:
        return {"success": True, "analysis": str(media.metadata.get("data", "")), "confidence": 1.0}
    return {"success": False, "error": f"no perception path for modality: {media.type.value}"}