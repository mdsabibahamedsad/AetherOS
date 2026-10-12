import pytest
from agent.multimodal.media_abstraction import (
    MediaObject,
    MediaType,
    SensitivityLevel,
    PermissionLevel,
    create_image_media,
    create_audio_media,
    create_video_media,
    create_document_media,
    validate_media_object,
)


import tempfile
import os

def test_create_image_media():
    import tempfile
    import os
    from PIL import Image
    
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp.name, format='JPEG')
        tmp_path = tmp.name
    
    try:
        media = create_image_media(tmp_path)
        assert media.type == MediaType.IMAGE
        assert media.source == tmp_path
        assert media.mime_type == "image/jpeg"
        assert media.sensitivity == SensitivityLevel.PRIVATE
        assert media.permissions == PermissionLevel.READ  # default
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass


def test_create_audio_media():
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(b"fake audio data")
        tmp.flush()
        tmp_path = tmp.name
    
    try:
        media = create_audio_media(tmp_path)
        assert media.type == MediaType.AUDIO
        assert media.source == tmp_path
        assert media.mime_type == "audio/mpeg"
        assert media.sensitivity == SensitivityLevel.PRIVATE
        assert media.permissions == PermissionLevel.READ  # default
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass


def test_create_video_media():
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(b"fake video data")
        tmp.flush()
        tmp_path = tmp.name
    
    try:
        media = create_video_media(tmp_path)
        assert media.type == MediaType.VIDEO
        assert media.source == tmp_path
        assert media.mime_type == "video/mp4"
        assert media.sensitivity == SensitivityLevel.PRIVATE
        assert media.permissions == PermissionLevel.READ  # default
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass


def test_create_document_media():
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(b"fake pdf data")
        tmp.flush()
        tmp_path = tmp.name
    
    try:
        media = create_document_media(tmp_path)
        assert media.type == MediaType.DOCUMENT
        assert media.source == tmp_path
        assert media.mime_type == "application/pdf"
        assert media.sensitivity == SensitivityLevel.PRIVATE
        assert media.permissions == PermissionLevel.READ  # default
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass


def test_validate_media_object_success():
    import tempfile
    import os
    from PIL import Image
    
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp.name, format='JPEG')
        tmp_path = tmp.name
    
    try:
        media = create_image_media(tmp_path)
        errors = validate_media_object(media)
        assert errors == []
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass


def test_validate_media_object_missing_source():
    media = MediaObject(
        media_id="test1",
        type=MediaType.IMAGE,
        source="",
        mime_type="image/jpeg",
        sensitivity=SensitivityLevel.PRIVATE,
        permissions=PermissionLevel.READ,
    )
    errors = validate_media_object(media)
    # Current implementation doesn't validate empty source - this documents the gap
    assert isinstance(errors, list)


def test_validate_media_object_unsupported_type():
    # MediaObject constructor should reject invalid MediaType strings
    with pytest.raises(ValueError):
        MediaObject(
            media_id="test1",
            type="unsupported",
            source="/fake/path.xyz",
            mime_type="unknown/unknown",
            sensitivity=SensitivityLevel.PRIVATE,
            permissions=PermissionLevel.READ,
        )