from __future__ import annotations

import logging
import platform
import tempfile
from pathlib import Path
from typing import Any, Optional

from aetheros_ocr.providers.base import OCRProvider, OCRProviderType, OCRResult, TextBlock

logger = logging.getLogger(__name__)


class WindowsOCRProvider(OCRProvider):

    name = "windows_ocr"
    provider_type = OCRProviderType.SYSTEM

    def __init__(self):
        self._ocr_engine = None
        self._available = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        if platform.system() != "Windows":
            self._available = False
            return False
        try:
            import winrt.windows.media.ocr as wocr
            import winrt.windows.globalization as wg
            self._available = True
            return True
        except ImportError:
            self._available = False
            return False
        except Exception:
            self._available = False
            return False

    def list_supported_languages(self) -> list[str]:
        if not self.is_available():
            return []
        try:
            import winrt.windows.media.ocr as wocr
            import winrt.windows.globalization as wg
            engine = wocr.OcrEngine
            languages = []
            for lang in engine.available_recognizer_languages:
                languages.append(lang.language_tag)
            return languages
        except Exception:
            return []

    def ocr(self, image_path: str, language: Optional[str] = None, **kwargs) -> OCRResult:
        if platform.system() != "Windows":
            return OCRResult(
                success=False,
                error="Windows OCR is only available on Windows",
                provider=self.name,
            )
        try:
            import winrt.windows.media.ocr as wocr
            import winrt.windows.globalization as wg
            import winrt.windows.graphics.imaging as wgi
            from winrt.windows.storage import StorageFile
            from winrt.windows.storage.streams import FileOpenMode

            lang_tag = language or "en"
            if language:
                ocr_engine = wocr.OcrEngine.try_create_from_language(wg.Language(lang_tag))
            else:
                ocr_engine = wocr.OcrEngine.try_create()

            if ocr_engine is None:
                return OCRResult(
                    success=False,
                    error=f"Failed to create OCR engine for language '{lang_tag}'",
                    provider=self.name,
                )

            storage_file = StorageFile.get_file_from_path_async(image_path).get_results()
            stream = storage_file.open_async(FileOpenMode.READ).get_results()
            decoder = wgi.BitmapDecoder.create_async(stream).get_results()
            bitmap = decoder.get_software_bitmap_async().get_results()

            ocr_result = ocr_engine.recognize_async(bitmap).get_results()

            lines = []
            blocks = []
            for line in ocr_result.lines:
                lines.append(line.text)
                blocks.append(TextBlock(
                    text=line.text,
                    confidence=line.confidence if hasattr(line, "confidence") else 1.0,
                    bbox=(
                        line.words[0].bounding_rect.x if line.words else 0,
                        line.words[0].bounding_rect.y if line.words else 0,
                        line.words[-1].bounding_rect.x + line.words[-1].bounding_rect.width if line.words else 0,
                        line.words[-1].bounding_rect.y + line.words[-1].bounding_rect.height if line.words else 0,
                    ) if line.words else (0, 0, 0, 0),
                ))

            full_text = "\n".join(lines)
            confidence = ocr_result.text_angle if hasattr(ocr_result, "text_angle") else 1.0

            return OCRResult(
                success=True,
                text=full_text,
                confidence=confidence if isinstance(confidence, (int, float)) else 1.0,
                language=lang_tag,
                provider=self.name,
                pages=[{"page_number": 1, "text": full_text, "confidence": confidence}],
                blocks=blocks,
            )
        except ImportError:
            return OCRResult(
                success=False,
                error="Windows OCR requires winrt. Install with: pip install winrt",
                provider=self.name,
            )
        except Exception as e:
            return OCRResult(success=False, error=str(e), provider=self.name)

    def ocr_bytes(self, image_data: bytes, language: Optional[str] = None, **kwargs) -> OCRResult:
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(image_data)
                tmp_path = tmp.name
            result = self.ocr(tmp_path, language=language, **kwargs)
            Path(tmp_path).unlink(missing_ok=True)
            return result
        except Exception as e:
            return OCRResult(success=False, error=str(e), provider=self.name)

    def can_handle_pdf(self) -> bool:
        return False
