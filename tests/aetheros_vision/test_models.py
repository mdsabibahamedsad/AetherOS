"""Tests for aetheros_vision models — serialization round-trips and invariants."""

from aetheros_vision.models import (
    AnalysisResult,
    BoundingBox,
    CaptureResult,
    CaptureMode,
    DocumentExtraction,
    MediaType,
    OCRExtraction,
    VisionDiagnostics,
    VisionMemoryKind,
    VisionMemoryRecord,
)


class TestBoundingBox:
    def test_to_dict_round_trip(self):
        box = BoundingBox(x=10, y=20, width=30, height=40, label="btn", confidence=0.9)
        d = box.to_dict()
        assert d["x"] == 10
        assert d["y"] == 20
        assert d["width"] == 30
        assert d["height"] == 40
        assert d["label"] == "btn"
        assert d["confidence"] == 0.9


class TestOCRExtraction:
    def test_defaults(self):
        r = OCRExtraction(success=False)
        assert r.text == ""
        assert r.confidence == 0.0
        assert r.blocks == []
        assert r.error is None


class TestAnalysisResult:
    def test_to_dict_includes_ocr_text(self):
        r = AnalysisResult(summary="s", text="hello")
        r.ocr = OCRExtraction(success=True, text="hello")
        d = r.to_dict()
        assert d["ocr_text"] == "hello"
        assert d["summary"] == "s"
        assert d["success"] is True

    def test_no_ocr_text_empty(self):
        d = AnalysisResult().to_dict()
        assert d["ocr_text"] == ""


class TestCaptureResult:
    def test_mode_serializes_as_value(self):
        r = CaptureResult(success=True, mode=CaptureMode.FULL_SCREEN)
        assert r.to_dict()["mode"] == "full_screen"


class TestDocumentExtraction:
    def test_media_type_serializes_as_value(self):
        r = DocumentExtraction(success=True, media_type=MediaType.MARKDOWN)
        assert r.to_dict()["media_type"] == "markdown"


class TestVisionMemoryRecord:
    def test_to_dict_round_trip(self):
        rec = VisionMemoryRecord(kind=VisionMemoryKind.SCREENSHOT, content="x", tags=["a", "b"])
        d = rec.to_dict()
        assert d["kind"] == "screenshot"
        assert d["tags"] == ["a", "b"]
        assert d["id"]


class TestVisionDiagnostics:
    def test_to_dict_all_fields(self):
        d = VisionDiagnostics(ocr_available=True, vision_provider="gemini").to_dict()
        assert d["state"] == "uninitialized"
        assert d["ocr_available"] is True
        assert d["vision_provider"] == "gemini"
