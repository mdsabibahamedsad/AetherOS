"""AetherOS Vision — image loading and understanding.

Decodes images in the supported formats (PNG, JPEG, WEBP, GIF, BMP, TIFF,
SVG, HEIC), handles multi-frame (GIF/TIFF) and multi-image inputs, resizes
large images for downstream vision APIs, and produces structured
understanding via OCR + the auxiliary vision router.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aetheros_vision.config import VisionSettings, get_aetheros_dir, load_vision_settings
from aetheros_vision.models import AnalysisResult, DetectedObject, ImageInfo, OCRExtraction

logger = logging.getLogger(__name__)


class ImageDecodeError(Exception):
    pass


def _mime_from_magic(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"BM"):
        return "image/bmp"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"II*\x00") or data.startswith(b"MM\x00*"):
        return "image/tiff"
    return ""


def detect_mime_type(path: Path) -> str:
    with path.open("rb") as f:
        header = f.read(64)
    return _mime_from_magic(header)


class ImageLoader:
    """Decodes images across the supported format set with sanitisation."""

    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()

    def load(self, source: str) -> "LoadedImage":
        return LoadedImage.from_source(source)

    def load_bytes(self, data: bytes, format_hint: Optional[str] = None) -> "LoadedImage":
        return LoadedImage.from_bytes(data, format_hint=format_hint)


@dataclass
class LoadedImage:
    """A decoded image (or first frame of a multi-frame source)."""

    path: Optional[str] = None
    data: bytes = b""
    format: str = ""
    mode: str = ""
    width: int = 0
    height: int = 0
    frames: int = 1
    mime_type: str = ""

    @classmethod
    def from_source(cls, source: str) -> "LoadedImage":
        path = Path(os.path.expanduser(source))
        if not path.is_file():
            raise ImageDecodeError(f"Image file not found: {source}")
        data = path.read_bytes()
        return cls._from_bytes(data, str(path))

    @classmethod
    def from_bytes(cls, data: bytes, format_hint: Optional[str] = None) -> "LoadedImage":
        return cls._from_bytes(data, None, format_hint)

    @classmethod
    def _from_bytes(cls, data: bytes, path: Optional[str], format_hint: Optional[str] = None) -> "LoadedImage":
        mime = _mime_from_magic(data) or format_hint or ""
        low = mime.lower()
        fmt_map = {
            "image/png": "PNG",
            "image/jpeg": "JPEG",
            "image/gif": "GIF",
            "image/bmp": "BMP",
            "image/webp": "WEBP",
            "image/tiff": "TIFF",
        }
        if low == "image/svg+xml" or (path and Path(path).suffix.lower() == ".svg"):
            # SVG must be rasterised before OCR / vision APIs can consume it.
            return _rasterize_svg(data, path, format_hint or "image/svg+xml")
        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - Pillow is a core dep
            raise ImageDecodeError("Pillow is required to decode images") from exc

        try:
            with Image.open(io.BytesIO(data)) as img:
                format_name = img.format or fmt_map.get(mime, "UNKNOWN")
                frames = getattr(img, "n_frames", 1) or 1
                img.seek(0)
                img.load()
                mode = img.mode
                width, height = img.size
                return cls(path=path, data=data, format=format_name, mode=mode, width=width, height=height, frames=frames, mime_type=mime or fmt_map.get(format_name, ""))
        except Exception as exc:  # noqa: BLE001
            raise ImageDecodeError(f"Failed to decode image: {exc}") from exc

    def to_pil(self):
        from PIL import Image
        return Image.open(io.BytesIO(self.data))

    def to_base64_data_url(self) -> str:
        mime = self.mime_type or "image/png"
        return f"data:{mime};base64,{base64.b64encode(self.data).decode('ascii')}"


def _rasterize_svg(data: bytes, path: Optional[str], mime: str) -> LoadedImage:
    """Rasterise an SVG to RGBA PNG using cairosvg if available, else Pillow fallback."""
    try:
        import cairosvg
        png = cairosvg.svg2png(bytestring=data)
        return LoadedImage.from_bytes(png, format_hint="image/png")
    except ImportError:
        pass
    try:
        from PIL import Image, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        with Image.open(io.BytesIO(data)) as img:
            img.load()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        loaded = LoadedImage.from_bytes(buf.getvalue(), format_hint="image/png")
        loaded.path = path
        return loaded
    except Exception as exc:  # noqa: BLE001
        raise ImageDecodeError(f"Failed to rasterise SVG: {exc}") from exc


def _extract_frames(path: Path, max_frames: int) -> List[ImageInfo]:
    """Extract frame info for multi-frame formats (GIF/TIFF)."""
    infos: List[ImageInfo] = []
    if path.suffix.lower() not in {".gif", ".tif", ".tiff"}:
        return infos
    try:
        from PIL import Image
        with Image.open(path) as img:
            n = getattr(img, "n_frames", 1) or 1
            for i in range(min(n, max_frames)):
                img.seek(i)
                infos.append(ImageInfo(path=str(path), width=img.width, height=img.height, format=img.format or "", mode=img.mode, size_bytes=path.stat().st_size, frames=n))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Frame extraction failed for %s: %s", path, exc)
    return infos


def _resize_for_payload(path: Path, max_bytes: int) -> Tuple[bytes, str]:
    """Downscale an oversized image to fit under ``max_bytes``. Returns (bytes, mime)."""
    from PIL import Image
    mime = detect_mime_type(path) or "image/jpeg"
    with Image.open(path) as img:
        if img.mode in {"RGBA", "P"} and mime != "image/png":
            img = img.convert("RGB")
        for _attempt in range(6):
            buf = io.BytesIO()
            save_kwargs = {"format": "PNG" if mime == "image/png" else "JPEG"}
            if "JPEG" in save_kwargs["format"]:
                save_kwargs["quality"] = 80
            img.save(buf, **save_kwargs)
            if buf.tell() <= max_bytes:
                return buf.getvalue(), mime
            w, h = img.size
            img = img.resize((max(w // 2, 64), max(h // 2, 64)))
    # Last resort: return the smallest attempt as-is.
    with Image.open(path) as img:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=50)
        return buf.getvalue(), "image/jpeg"


def prepare_image_payload(path: Path, max_bytes: int, mime: Optional[str] = None) -> Tuple[bytes, str]:
    """Return image bytes ready for a vision API, resizing if over budget."""
    size = path.stat().st_size
    mime = mime or detect_mime_type(path)
    if size <= max_bytes:
        return path.read_bytes(), mime
    return _resize_for_payload(path, max_bytes)


class ImageUnderstanding:
    """High-level image understanding combining OCR and the vision router."""

    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()

    def describe(self, path: str, question: str = "", use_ocr: bool = True) -> AnalysisResult:
        """Analyse an image locally (OCR) plus an optional VLM description."""
        import time as _t
        start = _t.perf_counter()
        result = AnalysisResult(backend="hybrid")
        loaded = LoadedImage.from_source(path)
        result.metadata["image"] = {"width": loaded.width, "height": loaded.height, "format": loaded.format, "frames": loaded.frames}

        if use_ocr:
            try:
                from aetheros_vision.ocr import create_ocr_engine
                engine = create_ocr_engine(self._settings)
                if engine.is_available():
                    ocr = engine.extract(path)
                    if ocr and ocr.success:
                        result.ocr = ocr
                        result.text = ocr.text
            except Exception as exc:  # noqa: BLE001
                logger.debug("OCR in describe() failed: %s", exc)

        result.processing_time_ms = (_t.perf_counter() - start) * 1000
        return result

    async def analyze(self, path: str, question: str = "") -> AnalysisResult:
        """Full analysis: OCR locally, then ask the vision router for a description."""
        import time as _t
        start = _t.perf_counter()
        base = self.describe(path, question=question, use_ocr=True)
        if self._settings.local_only:
            base.summary = base.text or ""
            base.caption = base.text or ""
            base.processing_time_ms = (_t.perf_counter() - start) * 1000
            return base
        try:
            from agent.auxiliary_client import async_call_llm, extract_content_or_reasoning
            from aetheros_vision.security import redact_sensitive_text
            payload = prepare_image_payload(Path(path), self._settings.max_analysis_bytes)
            mime = payload[1]
            data_url = f"data:{mime};base64,{base64.b64encode(payload[0]).decode('ascii')}"
            prompt = question.strip() or "Describe this image in detail."
            if base.text:
                prompt += f"\n\nOCR text found:\n{redact_sensitive_text(base.text)}"
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }]
            response = await async_call_llm(task="vision", messages=messages, temperature=0.1, max_tokens=2000)
            text = extract_content_or_reasoning(response)
            base.summary = text
            base.caption = text
            base.backend = "hybrid"
        except Exception as exc:  # noqa: BLE001
            logger.warning("VLM analysis failed, returning local result: %s", exc)
            base.summary = base.text or ""
            base.caption = base.text or ""
        base.processing_time_ms = (_t.perf_counter() - start) * 1000
        return base


def load_images(paths: List[str]) -> List[LoadedImage]:
    loader = ImageLoader()
    return [loader.load(p) for p in paths]
