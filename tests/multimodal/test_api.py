import pytest
from unittest.mock import patch, MagicMock

from agent.multimodal.api import (
    media_ingest,
    media_inspect,
    media_ocr,
    media_transcribe,
    media_analyze,
    media_embed,
    media_search,
    media_convert,
    media_stream,
    media_export,
)
from agent.multimodal.memory import MultimodalMemoryStore
from agent.multimodal.media_abstraction import MediaObject, MediaType, SensitivityLevel, PermissionLevel


import tempfile
import os

def test_media_ingest():
    import tempfile
    import os
    from PIL import Image
    
    # Create a valid test image
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp.name, format='JPEG')
        tmp_path = tmp.name
    
    try:
        result = media_ingest(tmp_path, source_type="file", sensitivity="private")
        assert result["success"] is True
        assert "media" in result
        assert result["media"]["type"] == "image"
    finally:
        # On Windows, ensure file is closed before deletion
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass


def test_media_inspect():
    media = MediaObject(
        media_id="test1",
        type=MediaType.IMAGE,
        source="/fake/path.jpg",
        mime_type="image/jpeg",
        sensitivity=SensitivityLevel.PRIVATE,
        permissions=PermissionLevel.READ_WRITE,
    )
    result = media_inspect(media)
    assert result["success"] is True
    assert result["media_id"] == "test1"
    assert result["type"] == "image"
    assert result["mime_type"] == "image/jpeg"


def test_media_ocr():
    with patch('agent.multimodal.api.ocr_media') as mock_ocr:
        mock_ocr.return_value = {"success": True, "text": "hello", "confidence": 0.9}
        media = MediaObject(
            media_id="test1",
            type=MediaType.IMAGE,
            source="/fake/path.jpg",
            mime_type="image/jpeg",
            sensitivity=SensitivityLevel.PRIVATE,
        )
        result = media_ocr(media)
        assert result["success"] is True
        assert result["text"] == "hello"
        mock_ocr.assert_called_once()


def test_media_transcribe():
    with patch('agent.multimodal.api.transcribe_audio') as mock_transcribe:
        mock_transcribe.return_value = {"success": True, "text": "hello world"}
        media = MediaObject(
            media_id="test1",
            type=MediaType.AUDIO,
            source="/fake/path.mp3",
            mime_type="audio/mpeg",
            sensitivity=SensitivityLevel.PRIVATE,
        )
        result = media_transcribe(media)
        assert result["success"] is True
        assert result["text"] == "hello world"
        mock_transcribe.assert_called_once()


def test_media_analyze_image():
    with patch('agent.multimodal.api.analyze_image') as mock_analyze:
        mock_analyze.return_value = {"success": True, "description": "a nice image"}
        media = MediaObject(
            media_id="test1",
            type=MediaType.IMAGE,
            source="/fake/path.jpg",
            mime_type="image/jpeg",
            sensitivity=SensitivityLevel.PRIVATE,
        )
        result = media_analyze(media, question="What is in the image?")
        assert result["success"] is True
        assert result["description"] == "a nice image"
        mock_analyze.assert_called_once()


def test_media_analyze_video():
    with patch('agent.multimodal.api.analyze_video') as mock_analyze:
        mock_analyze.return_value = {"success": True, "description": "a nice video"}
        media = MediaObject(
            media_id="test1",
            type=MediaType.VIDEO,
            source="/fake/path.mp4",
            mime_type="video/mp4",
            sensitivity=SensitivityLevel.PRIVATE,
        )
        result = media_analyze(media, question="What happens in the video?")
        assert result["success"] is True
        assert result["description"] == "a nice video"
        mock_analyze.assert_called_once()


def test_media_embed():
    media = MediaObject(
        media_id="test1",
        type=MediaType.IMAGE,
        source="/fake/path.jpg",
        mime_type="image/jpeg",
        sensitivity=SensitivityLevel.PRIVATE,
    )
    with patch('agent.auxiliary_client.call_llm') as mock_call_llm:
        mock_call_llm.return_value = {"embedding": [0.1, 0.2, 0.3]}
        with patch('agent.multimodal.api.default_store') as mock_store:
            mock_store_instance = MagicMock()
            mock_store_instance.store_media.return_value = "entry_id_123"
            mock_store.return_value = mock_store_instance
            result = media_embed(media, model="test-model")
            assert result["success"] is True
            assert result["entry_id"] == "entry_id_123"
            assert result["embedded"] is True
            mock_call_llm.assert_called_once()
            mock_store_instance.store_media.assert_called_once()


def test_media_search():
    with patch('agent.multimodal.api.default_store') as mock_store:
        mock_store_instance = MagicMock()
        mock_store_instance.search.return_value = []
        mock_store.return_value = mock_store_instance
        result = media_search("hello world")
        assert result["success"] is True
        assert result["query"] == "hello world"
        assert result["results"] == []
        assert result["count"] == 0


def test_media_convert():
    with patch('agent.multimodal.api.Image') as mock_image:
        mock_img = MagicMock()
        mock_image.open.return_value.__enter__.return_value = mock_img
        with patch('agent.multimodal.api.create_image_media') as mock_create:
            mock_media = MagicMock()
            mock_media.to_dict.return_value = {"type": "image"}
            mock_create.return_value = mock_media
            media = MediaObject(
                media_id="test1",
                type=MediaType.IMAGE,
                source="/fake/path.jpg",
                mime_type="image/jpeg",
                sensitivity=SensitivityLevel.PRIVATE,
            )
            result = media_convert(media, target_format="png", output_path="/fake/out.png")
            assert result["success"] is True
            assert result["output_path"] == "/fake/out.png"
            mock_img.save.assert_called_once_with("/fake/out.png", format="PNG")
            mock_create.assert_called_once_with("/fake/out.png")


def test_media_stream():
    with patch('agent.multimodal.stream_manager.MultimodalStreamManager') as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr.push.return_value = "frame_123"
        mock_mgr.stats.return_value = {"frames": 1}
        mock_mgr_class.return_value = mock_mgr
        result = media_stream("/fake/source", kind="audio", max_frames=100)
        assert result["success"] is True
        assert result["stream"] == "default"
        assert result["started"] is True
        assert result["stats"]["frames"] == 1


def test_media_export():
    with patch('builtins.open', create=True) as mock_open:
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        media = MediaObject(
            media_id="test1",
            type=MediaType.IMAGE,
            source="/fake/path.jpg",
            mime_type="image/jpeg",
            sensitivity=SensitivityLevel.PRIVATE,
        )
        media.metadata = {"analysis": "some analysis"}
        result = media_export(media, output_path="/fake/out.json", export_format="json")
        assert result["success"] is True
        assert result["output_path"] == "/fake/out.json"
        assert result["format"] == "json"
        mock_open.assert_called_once_with("/fake/out.json", "w", encoding="utf-8")