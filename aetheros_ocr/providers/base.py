from __future__ import annotations

import logging
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OCRProviderType(Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    SYSTEM = "system"


@dataclass
class TextBlock:
    text: str = ""
    confidence: float = 0.0
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class OCRResult:
    success: bool = False
    text: str = ""
    confidence: float = 0.0
    language: str = ""
    pages: list[dict] = field(default_factory=list)
    provider: str = ""
    processing_time_ms: float = 0.0
    error: Optional[str] = None
    blocks: Optional[list[TextBlock]] = None


class OCRProvider(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def display_name(self) -> str:
        return self.name.title()

    @property
    @abstractmethod
    def provider_type(self) -> OCRProviderType:
        ...

    def is_available(self) -> bool:
        return True

    def list_supported_languages(self) -> list[str]:
        return []

    @abstractmethod
    def ocr(self, image_path: str, language: Optional[str] = None, **kwargs) -> OCRResult:
        ...

    def ocr_bytes(self, image_data: bytes, language: Optional[str] = None, **kwargs) -> OCRResult:
        try:
            suffix = kwargs.pop("suffix", ".png")
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(image_data)
                tmp_path = tmp.name
            result = self.ocr(tmp_path, language=language, **kwargs)
            Path(tmp_path).unlink(missing_ok=True)
            return result
        except Exception as e:
            return OCRResult(success=False, error=str(e), provider=self.name)

    def can_handle_pdf(self) -> bool:
        return False
