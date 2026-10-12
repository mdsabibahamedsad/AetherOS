from __future__ import annotations

import base64
import logging
import platform
import tempfile
from pathlib import Path
from typing import Any, Optional

from aetheros_ocr.providers.base import OCRProvider, OCRProviderType, OCRResult, TextBlock

logger = logging.getLogger(__name__)


class CloudOCRProvider(OCRProvider):

    provider_type = OCRProviderType.CLOUD

    def __init__(self, provider_name: str = "azure", api_key: Optional[str] = None, base_url: Optional[str] = None):
        self._provider_name = provider_name
        self._api_key = api_key or ""
        self._base_url = base_url or ""
        self._available = None

    @property
    def name(self) -> str:
        return f"cloud_{self._provider_name}"

    @property
    def display_name(self) -> str:
        names = {"azure": "Azure Computer Vision", "google": "Google Cloud Vision", "aws": "AWS Textract"}
        return names.get(self._provider_name, f"Cloud OCR ({self._provider_name})")

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        if not self._api_key:
            self._available = False
            return False
        self._available = True
        return True

    def ocr(self, image_path: str, language: Optional[str] = None, **kwargs) -> OCRResult:
        if self._provider_name == "azure":
            return self._ocr_azure(image_path, language, **kwargs)
        elif self._provider_name == "google":
            return self._ocr_google(image_path, language, **kwargs)
        elif self._provider_name == "aws":
            return self._ocr_aws(image_path, language, **kwargs)
        return OCRResult(success=False, error=f"Unknown cloud provider: {self._provider_name}", provider=self.name)

    def _ocr_azure(self, image_path: str, language: Optional[str] = None, **kwargs) -> OCRResult:
        try:
            import requests
            with open(image_path, "rb") as f:
                image_data = f.read()
            url = f"{self._base_url.rstrip('/')}/vision/v3.2/ocr"
            headers = {
                "Ocp-Apim-Subscription-Key": self._api_key,
                "Content-Type": "application/octet-stream",
            }
            params = {"language": language or "unk", "detectOrientation": "true"}
            response = requests.post(url, headers=headers, params=params, data=image_data, timeout=60)
            response.raise_for_status()
            data = response.json()

            lines = []
            blocks = []
            for region in data.get("regions", []):
                for line in region.get("lines", []):
                    line_text = " ".join(w.get("text", "") for w in line.get("words", []))
                    lines.append(line_text)
                    words = line.get("words", [])
                    if words:
                        bbox_str = line.get("boundingBox", "0,0,0,0")
                        parts = [float(x) for x in bbox_str.split(",")]
                        blocks.append(TextBlock(
                            text=line_text,
                            confidence=0.9,
                            bbox=(parts[0], parts[1], parts[2], parts[3]) if len(parts) >= 4 else (0, 0, 0, 0),
                        ))

            full_text = "\n".join(lines)
            return OCRResult(
                success=True,
                text=full_text,
                confidence=0.9,
                language=language or "unk",
                provider=self.name,
                pages=[{"page_number": 1, "text": full_text, "confidence": 0.9}],
                blocks=blocks,
            )
        except ImportError:
            return OCRResult(success=False, error="requests is required for Azure OCR. Install with: pip install requests", provider=self.name)
        except Exception as e:
            return OCRResult(success=False, error=str(e), provider=self.name)

    def _ocr_google(self, image_path: str, language: Optional[str] = None, **kwargs) -> OCRResult:
        try:
            import requests
            with open(image_path, "rb") as f:
                image_data = f.read()
            encoded = base64.b64encode(image_data).decode("utf-8")
            url = f"{self._base_url.rstrip('/')}/v1/images:annotate"
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "requests": [{
                    "image": {"content": encoded},
                    "features": [{"type": "TEXT_DETECTION"}],
                    "imageContext": {"languageHints": [language or "en"]} if language else {},
                }]
            }
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            annotations = data.get("responses", [{}])[0].get("textAnnotations", [])
            if not annotations:
                return OCRResult(success=False, error="No text detected", provider=self.name)

            full_text = annotations[0].get("description", "")
            blocks = []
            for ann in annotations[1:]:
                vertices = ann.get("boundingPoly", {}).get("vertices", [])
                if vertices:
                    xs = [v.get("x", 0) for v in vertices]
                    ys = [v.get("y", 0) for v in vertices]
                    blocks.append(TextBlock(
                        text=ann.get("description", ""),
                        confidence=0.9,
                        bbox=(min(xs), min(ys), max(xs), max(ys)),
                    ))

            return OCRResult(
                success=True,
                text=full_text,
                confidence=0.9,
                language=language or "en",
                provider=self.name,
                pages=[{"page_number": 1, "text": full_text, "confidence": 0.9}],
                blocks=blocks,
            )
        except ImportError:
            return OCRResult(success=False, error="requests is required for Google Cloud Vision OCR. Install with: pip install requests", provider=self.name)
        except Exception as e:
            return OCRResult(success=False, error=str(e), provider=self.name)

    def _ocr_aws(self, image_path: str, language: Optional[str] = None, **kwargs) -> OCRResult:
        try:
            import boto3
            with open(image_path, "rb") as f:
                image_data = f.read()
            client = boto3.client(
                "textract",
                aws_access_key_id=kwargs.get("aws_access_key_id"),
                aws_secret_access_key=kwargs.get("aws_secret_access_key"),
                region_name=kwargs.get("region_name", "us-east-1"),
            )
            response = client.detect_document_text(Document={"Bytes": image_data})
            blocks_data = response.get("Blocks", [])

            lines = []
            blocks = []
            for b in blocks_data:
                if b.get("BlockType") == "LINE":
                    lines.append(b.get("Text", ""))
                    geom = b.get("Geometry", {}).get("BoundingBox", {})
                    blocks.append(TextBlock(
                        text=b.get("Text", ""),
                        confidence=b.get("Confidence", 0) / 100.0,
                        bbox=(
                            geom.get("Left", 0),
                            geom.get("Top", 0),
                            geom.get("Left", 0) + geom.get("Width", 0),
                            geom.get("Top", 0) + geom.get("Height", 0),
                        ),
                    ))

            full_text = "\n".join(lines)
            confidence = 0.0
            confidences = [b.get("Confidence", 0) for b in blocks_data if b.get("BlockType") == "LINE" and b.get("Confidence")]
            if confidences:
                confidence = sum(confidences) / len(confidences) / 100.0

            return OCRResult(
                success=True,
                text=full_text,
                confidence=confidence,
                language=language or "en",
                provider=self.name,
                pages=[{"page_number": 1, "text": full_text, "confidence": confidence}],
                blocks=blocks,
            )
        except ImportError:
            return OCRResult(success=False, error="boto3 is required for AWS Textract. Install with: pip install boto3", provider=self.name)
        except Exception as e:
            return OCRResult(success=False, error=str(e), provider=self.name)
