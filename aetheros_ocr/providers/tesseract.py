from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from aetheros_ocr.providers.base import OCRProvider, OCRProviderType, OCRResult, TextBlock

logger = logging.getLogger(__name__)


class TesseractProvider(OCRProvider):

    name = "tesseract"
    provider_type = OCRProviderType.LOCAL

    def __init__(self, tesseract_cmd: Optional[str] = None, custom_config: Optional[str] = None):
        self._tesseract_cmd = tesseract_cmd or os.environ.get("TESSERACT_CMD", "")
        self._custom_config = custom_config or ""
        self._pytesseract = None

    def _get_pytesseract(self):
        if self._pytesseract is not None:
            return self._pytesseract
        try:
            import pytesseract
            if self._tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd
            self._pytesseract = pytesseract
            return pytesseract
        except ImportError:
            raise ImportError(
                "pytesseract is not installed. Install it with: pip install pytesseract"
            )

    def is_available(self) -> bool:
        try:
            import pytesseract
            if self._tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def list_supported_languages(self) -> list[str]:
        try:
            pytesseract = self._get_pytesseract()
            return pytesseract.get_languages()
        except Exception:
            return []

    def ocr(self, image_path: str, language: Optional[str] = None, **kwargs) -> OCRResult:
        try:
            pytesseract = self._get_pytesseract()
            lang = language or "eng"
            psm = kwargs.get("psm_mode", 3)
            config_parts = [f"--psm {psm}"]
            if self._custom_config:
                config_parts.append(self._custom_config)
            custom_config = " ".join(config_parts)

            text = pytesseract.image_to_string(image_path, lang=lang, config=custom_config)
            data = pytesseract.image_to_data(image_path, lang=lang, config=custom_config, output_type="dict")

            confidence = 0.0
            blocks: list[TextBlock] = []
            confidences = [c for c in data.get("conf", []) if isinstance(c, (int, float)) and c > 0]
            if confidences:
                confidence = sum(confidences) / len(confidences) / 100.0

            n_boxes = len(data.get("level", []))
            for i in range(n_boxes):
                if data.get("text", [""] * n_boxes)[i].strip():
                    block = TextBlock(
                        text=data["text"][i],
                        confidence=data["conf"][i] / 100.0 if data["conf"][i] > 0 else 0.0,
                        bbox=(
                            float(data["left"][i]),
                            float(data["top"][i]),
                            float(data["left"][i] + data["width"][i]),
                            float(data["top"][i] + data["height"][i]),
                        ),
                    )
                    blocks.append(block)

            return OCRResult(
                success=True,
                text=text.strip(),
                confidence=confidence,
                language=lang,
                provider=self.name,
                pages=[{"page_number": 1, "text": text.strip(), "confidence": confidence}],
                blocks=blocks,
            )
        except ImportError as e:
            return OCRResult(success=False, error=str(e), provider=self.name)
        except Exception as e:
            error_msg = str(e)
            if "TesseractNotFound" in type(e).__name__ or "tesseract" in error_msg.lower():
                return OCRResult(
                    success=False,
                    error="Tesseract OCR is not installed or not on PATH. Install Tesseract from https://github.com/tesseract-ocr/tesseract",
                    provider=self.name,
                )
            return OCRResult(success=False, error=error_msg, provider=self.name)

    def ocr_bytes(self, image_data: bytes, language: Optional[str] = None, **kwargs) -> OCRResult:
        try:
            from PIL import Image
            import io
            image = Image.open(io.BytesIO(image_data))
            pytesseract = self._get_pytesseract()
            lang = language or "eng"
            psm = kwargs.get("psm_mode", 3)
            config_parts = [f"--psm {psm}"]
            if self._custom_config:
                config_parts.append(self._custom_config)
            custom_config = " ".join(config_parts)

            text = pytesseract.image_to_string(image, lang=lang, config=custom_config)
            data = pytesseract.image_to_data(image, lang=lang, config=custom_config, output_type="dict")

            confidence = 0.0
            blocks: list[TextBlock] = []
            confidences = [c for c in data.get("conf", []) if isinstance(c, (int, float)) and c > 0]
            if confidences:
                confidence = sum(confidences) / len(confidences) / 100.0

            n_boxes = len(data.get("level", []))
            for i in range(n_boxes):
                if data.get("text", [""] * n_boxes)[i].strip():
                    block = TextBlock(
                        text=data["text"][i],
                        confidence=data["conf"][i] / 100.0 if data["conf"][i] > 0 else 0.0,
                        bbox=(
                            float(data["left"][i]),
                            float(data["top"][i]),
                            float(data["left"][i] + data["width"][i]),
                            float(data["top"][i] + data["height"][i]),
                        ),
                    )
                    blocks.append(block)

            return OCRResult(
                success=True,
                text=text.strip(),
                confidence=confidence,
                language=lang,
                provider=self.name,
                pages=[{"page_number": 1, "text": text.strip(), "confidence": confidence}],
                blocks=blocks,
            )
        except ImportError as e:
            return OCRResult(success=False, error=str(e), provider=self.name)
        except Exception as e:
            error_msg = str(e)
            if "TesseractNotFound" in type(e).__name__ or "tesseract" in error_msg.lower():
                return OCRResult(
                    success=False,
                    error="Tesseract OCR is not installed or not on PATH. Install Tesseract from https://github.com/tesseract-ocr/tesseract",
                    provider=self.name,
                )
            return OCRResult(success=False, error=error_msg, provider=self.name)
