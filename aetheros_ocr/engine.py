from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from aetheros_ocr.providers.base import OCRProvider, OCRResult, TextBlock

try:
    from aetheros_cli.config import load_config
except ImportError:
    load_config = None

logger = logging.getLogger(__name__)


@dataclass
class OCRConfig:
    provider: str = "tesseract"
    language: str = "eng"
    confidence_threshold: float = 0.0
    psm_mode: int = 3
    use_deskew: bool = False
    use_denoise: bool = False
    use_enhance: bool = False
    max_image_size: Optional[int] = None
    supported_languages: list[str] = field(default_factory=lambda: ["eng"])


class OCREngine:

    def __init__(self, config: Optional[OCRConfig] = None):
        self._lock = threading.RLock()
        self._config = config or OCRConfig()
        self._providers: dict[str, OCRProvider] = {}
        self._stats: dict[str, Any] = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "total_processing_time_ms": 0.0,
        }

    def register_provider(self, name: str, provider: OCRProvider) -> None:
        with self._lock:
            self._providers[name] = provider

    def set_provider(self, name: str) -> bool:
        with self._lock:
            if name in self._providers:
                self._config.provider = name
                return True
            return False

    def ocr_image(self, image_path: str, language: Optional[str] = None, **kwargs) -> OCRResult:
        provider = self._get_provider()
        if provider is None:
            return OCRResult(success=False, error="No OCR provider available", provider="")
        start = time.perf_counter()
        result = provider.ocr(image_path, language=language or self._config.language, **kwargs)
        self._record_result(result, start)
        return self._apply_threshold(result)

    def ocr_pdf(self, pdf_path: str, language: Optional[str] = None, **kwargs) -> OCRResult:
        provider = self._get_provider()
        if provider is None:
            return OCRResult(success=False, error="No OCR provider available", provider="")
        if not provider.can_handle_pdf():
            return OCRResult(success=False, error=f"Provider {provider.name} does not support PDF", provider=provider.name)
        start = time.perf_counter()
        result = provider.ocr(pdf_path, language=language or self._config.language, **kwargs)
        self._record_result(result, start)
        return self._apply_threshold(result)

    def ocr_bytes(self, image_data: bytes, language: Optional[str] = None, **kwargs) -> OCRResult:
        provider = self._get_provider()
        if provider is None:
            return OCRResult(success=False, error="No OCR provider available", provider="")
        start = time.perf_counter()
        result = provider.ocr_bytes(image_data, language=language or self._config.language, **kwargs)
        self._record_result(result, start)
        return self._apply_threshold(result)

    def list_providers(self) -> list[str]:
        with self._lock:
            return list(self._providers.keys())

    def get_provider(self, name: str) -> Optional[OCRProvider]:
        with self._lock:
            return self._providers.get(name)

    def get_stats(self) -> dict:
        with self._lock:
            return dict(self._stats)

    def _get_provider(self) -> Optional[OCRProvider]:
        with self._lock:
            name = self._config.provider
            provider = self._providers.get(name)
            if provider is not None and provider.is_available():
                return provider
            for p in self._providers.values():
                if p.is_available():
                    self._config.provider = p.name
                    return p
            return None

    def _record_result(self, result: OCRResult, start: float) -> None:
        elapsed = (time.perf_counter() - start) * 1000
        with self._lock:
            self._stats["total_requests"] += 1
            if result.success:
                self._stats["successful"] += 1
            else:
                self._stats["failed"] += 1
            self._stats["total_processing_time_ms"] += elapsed
        result.processing_time_ms = elapsed

    def _apply_threshold(self, result: OCRResult) -> OCRResult:
        threshold = self._config.confidence_threshold
        if threshold > 0.0 and result.confidence < threshold:
            return OCRResult(
                success=False,
                text=result.text,
                confidence=result.confidence,
                language=result.language,
                provider=result.provider,
                error=f"Confidence {result.confidence:.2f} below threshold {threshold:.2f}",
            )
        return result
