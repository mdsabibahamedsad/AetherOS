"""AetherOS Vision — OCR engine facade.

Wraps ``aetheros_ocr.OCREngine`` with preprocessing (deskew/denoise/
enhance), multi-language support, table extraction, and PDF OCR. The facade
is what the rest of the multimodal runtime talks to.
"""

from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from aetheros_ocr.engine import OCREngine
from aetheros_ocr.providers.base import OCRProvider, OCRProviderType, OCRResult
from aetheros_vision.config import VisionSettings, load_vision_settings
from aetheros_vision.models import BoundingBox, OCRExtraction

logger = logging.getLogger(__name__)


def create_ocr_engine(settings: Optional[VisionSettings] = None) -> "VisionOCREngine":
    settings = settings or load_vision_settings()
    return VisionOCREngine(settings)


class VisionOCREngine:
    """Preprocessing-aware OCR facade over the provider registry."""

    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()
        ocr_cfg = self._settings.ocr
        self._engine = OCREngine()
        self._engine._config.provider = ocr_cfg.provider
        self._engine._config.language = ocr_cfg.language
        self._engine._config.confidence_threshold = ocr_cfg.confidence_threshold
        self._engine._config.psm_mode = ocr_cfg.psm_mode
        self._engine._config.use_deskew = ocr_cfg.use_deskew
        self._engine._config.use_denoise = ocr_cfg.use_denoise
        self._engine._config.use_enhance = ocr_cfg.use_enhance
        self._register_builtin_providers()

    def _register_builtin_providers(self) -> None:
        try:
            from aetheros_ocr.providers.tesseract import TesseractProvider
            self._engine.register_provider("tesseract", TesseractProvider())
        except Exception:  # noqa: BLE001
            pass
        try:
            from aetheros_ocr.providers.windows_ocr import WindowsOCRProvider
            self._engine.register_provider("windows_ocr", WindowsOCRProvider())
        except Exception:  # noqa: BLE001
            pass
        try:
            from aetheros_ocr.providers.cloud import CloudOCRProvider
            self._engine.register_provider("cloud_azure", CloudOCRProvider(provider_name="azure"))
        except Exception:  # noqa: BLE001
            pass

    # -- provider surface ---------------------------------------------------

    def is_available(self) -> bool:
        return self._engine._get_provider() is not None

    def provider_name(self) -> str:
        provider = self._engine._get_provider()
        return provider.name if provider else ""

    def provider_type(self) -> str:
        provider = self._engine._get_provider()
        return provider.provider_type.value if provider else ""

    def list_languages(self) -> List[str]:
        provider = self._engine._get_provider()
        if provider is None:
            return []
        try:
            langs = provider.list_supported_languages() or []
            return [str(l) for l in langs]
        except Exception:  # noqa: BLE001
            return []

    def set_provider(self, name: str) -> bool:
        return self._engine.set_provider(name)

    def set_language(self, language: str) -> None:
        self._engine._config.language = language

    # -- OCR entry points ---------------------------------------------------

    def extract(self, image_path: str, language: Optional[str] = None) -> OCRExtraction:
        """OCR a single image, applying preprocessing per config."""
        start = time.perf_counter()
        lang = language or self._settings.ocr.language
        prepped_path = self._maybe_preprocess(image_path)
        try:
            result = self._engine.ocr_image(prepped_path, language=lang)
        finally:
            self._cleanup_temp(prepped_path, image_path)
        return self._map_result(result, start)

    def extract_bytes(self, image_data: bytes, language: Optional[str] = None) -> OCRExtraction:
        start = time.perf_counter()
        lang = language or self._settings.ocr.language
        provider = self._engine._get_provider()
        if provider is None:
            return OCRExtraction(success=False, error="No OCR provider available", processing_time_ms=(time.perf_counter() - start) * 1000)
        data = self._maybe_preprocess_bytes(image_data)
        result = self._engine.ocr_bytes(data, language=lang)
        return self._map_result(result, start)

    def extract_pdf(self, pdf_path: str, language: Optional[str] = None) -> OCRExtraction:
        """OCR a PDF page-by-page. Uses pdf2image when available, else
        falls back to any provider that can handle PDF directly."""
        start = time.perf_counter()
        lang = language or self._settings.ocr.language
        provider = self._engine._get_provider()
        if provider is None:
            return OCRExtraction(success=False, error="No OCR provider available", processing_time_ms=(time.perf_counter() - start) * 1000)

        if provider.can_handle_pdf():
            result = self._engine.ocr_pdf(pdf_path, language=lang)
            return self._map_result(result, start)

        pages = self._pdf_to_images(pdf_path)
        if not pages:
            return OCRExtraction(success=False, error="Could not rasterize PDF (pdf2image/Poppler unavailable)", processing_time_ms=(time.perf_counter() - start) * 1000)

        all_text: List[str] = []
        all_blocks: List[Any] = []
        pages_out: List[dict] = []
        for page_no, page_path in enumerate(pages, start=1):
            page_result = self._engine.ocr_image(page_path, language=lang)
            all_text.append(page_result.text or "")
            if page_result.blocks:
                all_blocks.extend(page_result.blocks)
            pages_out.append({"page_number": page_no, "text": page_result.text or "", "confidence": page_result.confidence})
            self._cleanup_temp(page_path, page_path)

        return OCRExtraction(
            success=True,
            text="\n\n".join(t for t in all_text if t),
            confidence=sum(p["confidence"] for p in pages_out) / len(pages_out) if pages_out else 0.0,
            language=lang,
            provider=provider.name,
            blocks=[self._to_block(b) for b in all_blocks],
            pages=pages_out,
            processing_time_ms=(time.perf_counter() - start) * 1000,
        )

    def extract_table(self, image_path: str) -> List[List[List[str]]]:
        """Extract tabular structure from an image using tesseract's TSV
        output and spatial clustering into rows/cells. Returns a list of
        tables (each a list of rows of cell strings)."""
        provider = self._engine._get_provider()
        if provider is None:
            return []
        if provider.name != "tesseract":
            logger.debug("Table extraction requires tesseract; provider is %s", provider.name)
            return []
        try:
            import csv
            import io as _io
            import pytesseract
            from PIL import Image as _PIL
            from aetheros_ocr.preprocessing import preprocess
            img = _PIL.open(image_path)
            img = preprocess(img, use_deskew=True, use_enhance=True, binarize_output=True)
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            words = []
            for i in range(len(data.get("text", []))):
                t = (data["text"][i] or "").strip()
                if not t:
                    continue
                words.append((int(data["left"][i]), int(data["top"][i]), int(data["width"][i]), int(data["height"][i]), t))
            if not words:
                return []
            rows: dict[int, List[tuple]] = {}
            for x, y, w, h, t in words:
                row_key = y // max((h or 10) // 2, 8)
                rows.setdefault(row_key, []).append((x, t))
            table: List[List[str]] = []
            for row_key in sorted(rows):
                cells = sorted(rows[row_key], key=lambda c: c[0])
                table.append([c[1] for c in cells])
            return [table]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Table extraction failed: %s", exc)
            return []

    # -- internals ----------------------------------------------------------

    def _maybe_preprocess(self, image_path: str) -> str:
        cfg = self._settings.ocr
        if not (cfg.use_deskew or cfg.use_denoise or cfg.use_enhance):
            return image_path
        try:
            from PIL import Image
            from aetheros_ocr.preprocessing import preprocess
            with Image.open(image_path) as img:
                img.load()
            out = preprocess(img, use_deskew=cfg.use_deskew, use_denoise=cfg.use_denoise, use_enhance=cfg.use_enhance)
            tmp = Path(image_path).with_suffix(".prepped.png")
            tmp.parent.mkdir(parents=True, exist_ok=True)
            out.save(tmp)
            return str(tmp)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Preprocessing failed, OCR on original: %s", exc)
            return image_path

    def _maybe_preprocess_bytes(self, image_data: bytes) -> bytes:
        cfg = self._settings.ocr
        if not (cfg.use_deskew or cfg.use_denoise or cfg.use_enhance):
            return image_data
        try:
            from aetheros_ocr.preprocessing import preprocess_bytes
            return preprocess_bytes(image_data, use_deskew=cfg.use_deskew, use_denoise=cfg.use_denoise, use_enhance=cfg.use_enhance)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Preprocessing failed, OCR on original bytes: %s", exc)
            return image_data

    def _pdf_to_images(self, pdf_path: str) -> List[str]:
        try:
            from pdf2image import convert_from_path
            pages = convert_from_path(pdf_path)
            out_paths = []
            for i, page in enumerate(pages):
                tmp = Path(pdf_path).with_suffix(f".page{i + 1}.png")
                page.save(tmp)
                out_paths.append(str(tmp))
            return out_paths
        except Exception as exc:  # noqa: BLE001
            logger.debug("pdf2image unavailable for %s: %s", pdf_path, exc)
            return []

    def _map_result(self, result: OCRResult, start: float) -> OCRExtraction:
        elapsed = (time.perf_counter() - start) * 1000
        return OCRExtraction(
            success=result.success,
            text=result.text,
            confidence=result.confidence,
            language=result.language,
            provider=result.provider,
            blocks=[self._to_block(b) for b in (result.blocks or [])],
            pages=result.pages,
            processing_time_ms=elapsed,
            error=result.error,
        )

    def _to_block(self, block) -> Any:
        try:
            bbox = block.bbox
            from aetheros_vision.models import OCRBlock
            return OCRBlock(
                text=block.text,
                confidence=float(block.confidence or 0.0),
                box=BoundingBox(x=bbox[0], y=bbox[1], width=bbox[2] - bbox[0], height=bbox[3] - bbox[1]),
            )
        except Exception:  # noqa: BLE001
            from aetheros_vision.models import OCRBlock
            return OCRBlock(text=getattr(block, "text", ""), confidence=0.0, box=BoundingBox(0, 0, 0, 0))

    def _cleanup_temp(self, tmp_path: str, original_path: str) -> None:
        if tmp_path != original_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass

    def health(self) -> dict:
        provider = self._engine._get_provider()
        return {
            "ok": provider is not None,
            "provider": provider.name if provider else "",
            "detail": f"provider={provider.name if provider else 'none'}",
        }
