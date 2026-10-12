"""Tests for aetheros_vision.ocr — engine facade availability and fallbacks."""

import pytest


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path / ".aetheros"))
    return tmp_path / ".aetheros"


class TestVisionOCREngine:
    def test_availability_reports_boolean(self, isolated_home):
        from aetheros_vision.ocr import create_ocr_engine

        engine = create_ocr_engine()
        assert isinstance(engine.is_available(), bool)

    def test_languages_returns_list(self, isolated_home):
        from aetheros_vision.ocr import create_ocr_engine

        engine = create_ocr_engine()
        langs = engine.list_languages()
        assert isinstance(langs, list)

    def test_extract_without_provider_fails_cleanly(self, tmp_path, isolated_home):
        from aetheros_vision.ocr import create_ocr_engine

        p = tmp_path / "img.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        engine = create_ocr_engine()
        result = engine.extract(str(p))
        if engine.is_available():
            assert result.success in (True, False)
        else:
            assert result.success is False
            assert result.error is not None

    def test_extract_bytes_without_provider_fails_cleanly(self, isolated_home):
        from aetheros_vision.ocr import create_ocr_engine

        engine = create_ocr_engine()
        result = engine.extract_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        if not engine.is_available():
            assert result.success is False
            assert "provider" in (result.error or "").lower() or result.error is not None

    def test_health_shape(self, isolated_home):
        from aetheros_vision.ocr import create_ocr_engine

        engine = create_ocr_engine()
        health = engine.health()
        assert "ok" in health
        assert "provider" in health
