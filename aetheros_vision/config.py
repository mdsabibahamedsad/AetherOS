"""AetherOS Vision — configuration.

Resolves the ``vision`` block from ``config.yaml`` (and sensible defaults)
into typed settings. Reads through the same ``aetheros_cli.config`` loader
used everywhere else so profiles and user overrides behave identically.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OCRSettings:
    provider: str = "tesseract"
    language: str = "eng"
    languages: List[str] = field(default_factory=lambda: ["eng"])
    psm_mode: int = 3
    confidence_threshold: float = 0.0
    use_deskew: bool = False
    use_denoise: bool = False
    use_enhance: bool = False
    max_image_size: Optional[int] = None


@dataclass
class CaptureSettings:
    default_mode: str = "full_screen"
    monitor: int = 0
    history_dir: str = "screenshots"
    history_limit: int = 100
    format: str = "png"
    annotate: bool = False


@dataclass
class VideoSettings:
    max_frames: int = 24
    key_moment_threshold: float = 0.12
    ffmpeg_path: str = ""


@dataclass
class VisionSettings:
    enabled: bool = True
    backend: str = "hybrid"
    ocr: OCRSettings = field(default_factory=OCRSettings)
    capture: CaptureSettings = field(default_factory=CaptureSettings)
    video: VideoSettings = field(default_factory=VideoSettings)
    local_only: bool = False
    mask_secrets: bool = True
    cache_enabled: bool = True
    cache_dir: str = "cache/vision"
    memory_enabled: bool = True
    max_analysis_bytes: int = 20 * 1024 * 1024


def _read_config() -> Dict[str, Any]:
    try:
        from aetheros_cli.config import cfg_get, load_config
        cfg = load_config()
        raw = cfg_get(cfg, "vision", default=None)
        if raw is None:
            raw = {}
        return raw if isinstance(raw, dict) else {}
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not load config.yaml vision block: %s", exc)
        return {}


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str) -> str:
    return str(value) if value is not None else default


def load_vision_settings() -> VisionSettings:
    """Load vision settings from config.yaml with defaults for missing keys."""
    raw = _read_config()
    settings = VisionSettings(
        enabled=_as_bool(raw.get("enabled"), True),
        backend=_as_str(raw.get("backend"), "hybrid"),
        local_only=_as_bool(raw.get("local_only"), False),
        mask_secrets=_as_bool(raw.get("mask_secrets"), True),
        cache_enabled=_as_bool(raw.get("cache_enabled"), True),
        cache_dir=_as_str(raw.get("cache_dir"), "cache/vision"),
        memory_enabled=_as_bool(raw.get("memory_enabled"), True),
        max_analysis_bytes=_as_int(raw.get("max_analysis_bytes"), 20 * 1024 * 1024),
    )

    ocr_raw = raw.get("ocr") or {}
    settings.ocr = OCRSettings(
        provider=_as_str(ocr_raw.get("provider"), "tesseract"),
        language=_as_str(ocr_raw.get("language"), "eng"),
        languages=[str(l) for l in (ocr_raw.get("languages") or ["eng"])],
        psm_mode=_as_int(ocr_raw.get("psm_mode"), 3),
        confidence_threshold=_as_float(ocr_raw.get("confidence_threshold"), 0.0),
        use_deskew=_as_bool(ocr_raw.get("use_deskew"), False),
        use_denoise=_as_bool(ocr_raw.get("use_denoise"), False),
        use_enhance=_as_bool(ocr_raw.get("use_enhance"), False),
        max_image_size=_as_int(ocr_raw.get("max_image_size"), None),
    )

    cap_raw = raw.get("capture") or {}
    settings.capture = CaptureSettings(
        default_mode=_as_str(cap_raw.get("default_mode"), "full_screen"),
        monitor=_as_int(cap_raw.get("monitor"), 0),
        history_dir=_as_str(cap_raw.get("history_dir"), "screenshots"),
        history_limit=_as_int(cap_raw.get("history_limit"), 100),
        format=_as_str(cap_raw.get("format"), "png"),
        annotate=_as_bool(cap_raw.get("annotate"), False),
    )

    video_raw = raw.get("video") or {}
    settings.video = VideoSettings(
        max_frames=_as_int(video_raw.get("max_frames"), 24),
        key_moment_threshold=_as_float(video_raw.get("key_moment_threshold"), 0.12),
        ffmpeg_path=_as_str(video_raw.get("ffmpeg_path"), os.environ.get("FFMPEG_PATH", "")),
    )
    return settings


def get_aetheros_home() -> Path:
    """Profile-aware AETHEROS_HOME (mirrors aetheros_constants without import cost)."""
    try:
        from aetheros_constants import get_aetheros_home as _gah
        return _gah()
    except Exception:  # noqa: BLE001
        return Path(os.environ.get("AETHEROS_HOME", str(Path.home() / ".aetheros")))


def get_aetheros_dir(subpath: str) -> Path:
    """Profile-aware subdirectory under AETHEROS_HOME, created on demand."""
    try:
        from aetheros_constants import get_aetheros_dir as _gad
        return _gad(subpath, subpath)
    except Exception:  # noqa: BLE001
        path = get_aetheros_home() / subpath
        path.mkdir(parents=True, exist_ok=True)
        return path
