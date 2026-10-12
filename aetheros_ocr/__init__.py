from __future__ import annotations

from aetheros_ocr.engine import OCREngine, OCRConfig, OCRResult
from aetheros_ocr.providers.base import OCRProvider, OCRProviderType
from aetheros_ocr.providers.tesseract import TesseractProvider
from aetheros_ocr.providers.windows_ocr import WindowsOCRProvider
from aetheros_ocr.providers.cloud import CloudOCRProvider

__all__ = [
    "OCREngine", "OCRConfig", "OCRResult",
    "OCRProvider", "OCRProviderType",
    "TesseractProvider", "WindowsOCRProvider", "CloudOCRProvider",
]
