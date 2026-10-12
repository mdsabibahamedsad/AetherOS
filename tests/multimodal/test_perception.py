import pytest
from unittest.mock import patch, MagicMock

from agent.multimodal.perception import (
    ocr_media,
    analyze_image,
    transcribe_audio,
    synthesize_speech,
    extract_document,
    extract_video_frames,
    analyze_video,
)
from agent.multimodal.media_abstraction import MediaObject, MediaType, SensitivityLevel


def test_ocr_media_success():
    import tempfile
    import os
    from PIL import Image
    
    # Create a real temp image file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp.name, format='PNG')
        tmp_path = tmp.name
    
    # Mock the OCR engine and its result
    mock_engine = MagicMock()
    mock_engine.is_available.return_value = True
    mock_result = MagicMock()
    mock_result.text = "hello world"
    mock_result.confidence = 0.9
    mock_result.blocks = []
    mock_engine.extract.return_value = mock_result
    
    with patch('aetheros_vision.ocr.create_ocr_engine', return_value=mock_engine):
        media = MediaObject(
            media_id="test1",
            type=MediaType.IMAGE,
            source=tmp_path,
            mime_type="image/png",
            sensitivity=SensitivityLevel.PRIVATE,
        )
        result = ocr_media(media, language="eng")
        assert result["success"] is True
        assert result["text"] == "hello world"
        assert result["confidence"] == 0.9
        assert result["blocks"] == []
    
    try:
        os.unlink(tmp_path)
    except PermissionError:
        pass


def test_ocr_media_not_available():
    import tempfile
    import os
    from PIL import Image
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp.name, format='PNG')
        tmp_path = tmp.name
    
    try:
        with patch('aetheros_vision.ocr.create_ocr_engine', side_effect=Exception("not available")):
            media = MediaObject(
                media_id="test1",
                type=MediaType.IMAGE,
                source=tmp_path,
                mime_type="image/png",
                sensitivity=SensitivityLevel.PRIVATE,
            )
            # Current implementation doesn't catch exceptions from create_ocr_engine()
            with pytest.raises(Exception, match="not available"):
                ocr_media(media)
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass


def test_analyze_image_success():
    import tempfile
    import os
    from PIL import Image
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp.name, format='PNG')
        tmp_path = tmp.name
    
    try:
        with patch('tools.vision_tools.vision_analyze_tool') as mock_tool:
            mock_tool.return_value = '{"description": "a test image"}'
            media = MediaObject(
                media_id="test1",
                type=MediaType.IMAGE,
                source=tmp_path,
                mime_type="image/png",
                sensitivity=SensitivityLevel.PRIVATE,
            )
            result = analyze_image(media, question="What is in the image?")
            # vision_analyze_tool returns JSON string that gets normalized to dict with "description"
            assert "description" in result
            assert result["description"] == "a test image"
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass


def test_transcribe_audio_success():
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(b"fake audio data")
        tmp.flush()
        tmp_path = tmp.name
    
    try:
        with patch('tools.transcription_tools.transcribe_audio') as mock_tool:
            mock_tool.return_value = {"transcript": "hello world", "confidence": 0.9}
            media = MediaObject(
                media_id="test1",
                type=MediaType.AUDIO,
                source=tmp_path,
                mime_type="audio/mpeg",
                sensitivity=SensitivityLevel.PRIVATE,
            )
            result = transcribe_audio(media)
            # transcribe_audio returns dict with transcript key
            assert "transcript" in result
            assert result["transcript"] == "hello world"
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass


def test_synthesize_speech_success():
    with patch('tools.tts_tool.text_to_speech_tool') as mock_tool:
        mock_tool.return_value = '{"success": true, "file_path": "/fake/output.wav"}'
        result = synthesize_speech("hello world")
        assert result["success"] is True
        assert result["file_path"] == "/fake/output.wav"


def test_extract_document_success():
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(b"fake pdf data")
        tmp.flush()
        tmp_path = tmp.name
    
    try:
        with patch('aetheros_vision.documents.DocumentIntelligence') as mock_doc_class:
            mock_doc = MagicMock()
            mock_doc.extract.return_value = {"text": "document text"}
            mock_doc_class.return_value = mock_doc
            media = MediaObject(
                media_id="test1",
                type=MediaType.DOCUMENT,
                source=tmp_path,
                mime_type="application/pdf",
                sensitivity=SensitivityLevel.PRIVATE,
            )
            result = extract_document(media)
            assert result["success"] is True
            assert result["text"] == "document text"
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass


def test_extract_video_frames_success():
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(b"fake video data")
        tmp.flush()
        tmp_path = tmp.name
    
    try:
        with patch('aetheros_vision.video.VideoUnderstanding') as mock_vid_class:
            mock_vid = MagicMock()
            # VideoUnderstanding.extract returns dict with "frames" key
            mock_vid.extract.return_value = {"frames": [{"frame": 1}, {"frame": 2}], "key_moments": [], "timeline": []}
            mock_vid_class.return_value = mock_vid
            media = MediaObject(
                media_id="test1",
                type=MediaType.VIDEO,
                source=tmp_path,
                mime_type="video/mp4",
                sensitivity=SensitivityLevel.PRIVATE,
            )
            result = extract_video_frames(media, max_frames=5)
            assert result["success"] is True
            assert len(result["frames"]) == 2
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass


def test_analyze_video_success():
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(b"fake video data")
        tmp.flush()
        tmp_path = tmp.name
    
    try:
        # Mock the async video_analyze_tool to avoid needing LLM provider
        async def mock_video_analyze_tool(path, question):
            return '{"description": "a test video"}'
        
        with patch('tools.vision_tools.video_analyze_tool', side_effect=mock_video_analyze_tool):
            media = MediaObject(
                media_id="test1",
                type=MediaType.VIDEO,
                source=tmp_path,
                mime_type="video/mp4",
                sensitivity=SensitivityLevel.PRIVATE,
            )
            result = analyze_video(media, question="What happens in the video?")
            # video_analyze_tool returns JSON string that gets normalized to dict with "description"
            assert "description" in result
            assert result["description"] == "a test video"
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass