"""AetherOS Vision — shared data models.

Typed dataclasses used across the vision runtime, OCR, document
intelligence, screen capture, video, and memory subsystems. Every result
type carries enough metadata to be rendered, logged, persisted, and
replayed without re-reading the source media.
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class VisionBackend(str, enum.Enum):
    """Inference backends the vision runtime can drive."""

    VLM = "vlm"            # multimodal LLM (auxiliary vision router)
    OCR = "ocr"            # local/system OCR engine
    RULE = "rule"          # deterministic / heuristic analysis
    HYBRID = "hybrid"      # OCR + rule + VLM combined


class RuntimeState(str, enum.Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class CaptureMode(str, enum.Enum):
    FULL_SCREEN = "full_screen"
    WINDOW = "window"
    REGION = "region"
    MULTI_MONITOR = "multi_monitor"


class CameraCaptureMode(str, enum.Enum):
    STILL = "still"
    BURST = "burst"
    TIMELAPSE = "timelapse"


class MediaType(str, enum.Enum):
    IMAGE = "image"
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    TXT = "txt"
    MARKDOWN = "markdown"
    HTML = "html"
    RTF = "rtf"
    VIDEO = "video"
    UNKNOWN = "unknown"


class VisionMemoryKind(str, enum.Enum):
    SCREENSHOT = "screenshot"
    OBJECT = "object"
    LAYOUT = "layout"
    UI_HISTORY = "ui_history"
    DOCUMENT = "document"
    CAPTION = "caption"
    CODE = "code"
    CHART = "chart"


@dataclass
class BoundingBox:
    x: float
    y: float
    width: float
    height: float
    label: str = ""
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "label": self.label,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class DetectedObject:
    label: str
    confidence: float
    box: BoundingBox
    kind: str = "object"


@dataclass
class OCRBlock:
    text: str
    confidence: float
    box: BoundingBox


@dataclass
class OCRExtraction:
    success: bool
    text: str = ""
    confidence: float = 0.0
    language: str = ""
    provider: str = ""
    blocks: List[OCRBlock] = field(default_factory=list)
    tables: List[List[List[str]]] = field(default_factory=list)
    processing_time_ms: float = 0.0
    error: Optional[str] = None
    pages: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ImageInfo:
    path: str
    width: int
    height: int
    format: str
    mode: str
    size_bytes: int
    mime_type: str = ""
    frames: int = 1


@dataclass
class AnalysisResult:
    """Structured output of a vision analysis pass."""

    summary: str = ""
    caption: str = ""
    objects: List[DetectedObject] = field(default_factory=list)
    text: str = ""
    ocr: Optional[OCRExtraction] = None
    labels: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""
    backend: str = VisionBackend.HYBRID.value
    processing_time_ms: float = 0.0
    error: Optional[str] = None
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "caption": self.caption,
            "objects": [o.to_dict() for o in self.objects],
            "text": self.text,
            "ocr_text": self.ocr.text if self.ocr else "",
            "labels": self.labels,
            "metadata": self.metadata,
            "backend": self.backend,
            "processing_time_ms": round(self.processing_time_ms, 3),
            "error": self.error,
            "success": self.success,
        }


@dataclass
class DocumentSection:
    heading: str = ""
    level: int = 0
    content: str = ""
    page: int = 0


@dataclass
class TableData:
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)

    def to_rows(self) -> List[List[str]]:
        return [self.headers] + self.rows if self.headers else self.rows


@dataclass
class ExtractedImage:
    index: int
    path: str = ""
    caption: str = ""
    page: int = 0
    size_bytes: int = 0


@dataclass
class DocumentExtraction:
    success: bool
    media_type: MediaType = MediaType.UNKNOWN
    text: str = ""
    title: str = ""
    author: str = ""
    created: str = ""
    modified: str = ""
    pages: int = 0
    sections: List[DocumentSection] = field(default_factory=list)
    tables: List[TableData] = field(default_factory=list)
    images: List[ExtractedImage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "media_type": self.media_type.value,
            "text": self.text,
            "title": self.title,
            "author": self.author,
            "created": self.created,
            "modified": self.modified,
            "pages": self.pages,
            "sections": [{"heading": s.heading, "level": s.level, "content": s.content, "page": s.page} for s in self.sections],
            "tables": [{"headers": t.headers, "rows": t.rows} for t in self.tables],
            "images": [{"index": i.index, "path": i.path, "caption": i.caption, "page": i.page, "size_bytes": i.size_bytes} for i in self.images],
            "metadata": self.metadata,
            "error": self.error,
            "processing_time_ms": round(self.processing_time_ms, 3),
        }


@dataclass
class CaptureResult:
    success: bool
    path: str = ""
    mode: CaptureMode = CaptureMode.FULL_SCREEN
    width: int = 0
    height: int = 0
    monitor: int = 0
    timestamp: float = field(default_factory=time.time)
    data_url: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "path": self.path,
            "mode": self.mode.value,
            "width": self.width,
            "height": self.height,
            "monitor": self.monitor,
            "timestamp": self.timestamp,
            "error": self.error,
        }


@dataclass
class CameraCaptureResult:
    success: bool
    path: str = ""
    mode: CameraCaptureMode = CameraCaptureMode.STILL
    width: int = 0
    height: int = 0
    camera_index: int = 0
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "path": self.path,
            "mode": self.mode.value,
            "width": self.width,
            "height": self.height,
            "camera_index": self.camera_index,
            "timestamp": self.timestamp,
            "error": self.error,
        }


@dataclass
class CaptureAnnotation:
    """A text/box annotation overlaid on a capture (region markers, labels)."""

    label: str
    box: Optional[BoundingBox] = None
    color: str = "#00FF00"


@dataclass
class VideoFrame:
    index: int
    timestamp_s: float
    path: str
    width: int = 0
    height: int = 0
    is_key_moment: bool = False
    caption: str = ""


@dataclass
class VideoExtraction:
    success: bool
    duration_s: float = 0.0
    fps: float = 0.0
    width: int = 0
    height: int = 0
    frame_count: int = 0
    frames: List[VideoFrame] = field(default_factory=list)
    key_moments: List[VideoFrame] = field(default_factory=list)
    subtitles: str = ""
    scene_summary: str = ""
    error: Optional[str] = None
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "duration_s": round(self.duration_s, 3),
            "fps": round(self.fps, 3),
            "width": self.width,
            "height": self.height,
            "frame_count": self.frame_count,
            "frames": [
                {"index": f.index, "timestamp_s": round(f.timestamp_s, 3), "path": f.path, "width": f.width, "height": f.height, "key_moment": f.is_key_moment, "caption": f.caption}
                for f in self.frames
            ],
            "key_moments": [f.index for f in self.key_moments],
            "subtitles": self.subtitles,
            "scene_summary": self.scene_summary,
            "error": self.error,
            "processing_time_ms": round(self.processing_time_ms, 3),
        }


@dataclass
class VisionMemoryRecord:
    kind: VisionMemoryKind
    content: str
    image_path: str = ""
    caption: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "content": self.content,
            "image_path": self.image_path,
            "caption": self.caption,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class VisionDiagnostics:
    state: RuntimeState = RuntimeState.UNINITIALIZED
    gpu_available: bool = False
    gpu_name: str = ""
    backend: str = ""
    model_loaded: bool = False
    ocr_available: bool = False
    ocr_provider: str = ""
    ocr_languages: List[str] = field(default_factory=list)
    vision_provider: str = ""
    vision_model: str = ""
    capture_available: bool = False
    uptime_s: float = 0.0
    total_requests: int = 0
    failures: int = 0
    last_error: Optional[str] = None
    checks: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "gpu_available": self.gpu_available,
            "gpu_name": self.gpu_name,
            "backend": self.backend,
            "model_loaded": self.model_loaded,
            "ocr_available": self.ocr_available,
            "ocr_provider": self.ocr_provider,
            "ocr_languages": self.ocr_languages,
            "vision_provider": self.vision_provider,
            "vision_model": self.vision_model,
            "capture_available": self.capture_available,
            "uptime_s": round(self.uptime_s, 3),
            "total_requests": self.total_requests,
            "failures": self.failures,
            "last_error": self.last_error,
            "checks": self.checks,
        }


# Canonical extensions we understand as images (Pillow-readable plus SVG/HEIC handled specially).
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".svg", ".heic", ".avif"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md", ".html", ".htm", ".rtf"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi", ".mkv", ".mpeg", ".mpg"}
