"""Tests for aetheros_vision.video — graceful degradation without ffmpeg/OpenCV."""

import pytest


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path / ".aetheros"))
    return tmp_path / ".aetheros"


class TestVideoUnderstanding:
    def test_missing_file_fails_cleanly(self, tmp_path, isolated_home):
        from aetheros_vision.video import VideoUnderstanding

        result = VideoUnderstanding().extract(str(tmp_path / "missing.mp4"))
        assert result.success is False
        assert result.error is not None

    def test_unsupported_extension_fails_cleanly(self, tmp_path, isolated_home):
        from aetheros_vision.video import VideoUnderstanding

        f = tmp_path / "file.xyz"
        f.write_bytes(b"not a video")
        result = VideoUnderstanding().extract(str(f))
        assert result.success is False
        assert result.error is not None

    def test_no_ffmpeg_fails_cleanly(self, tmp_path, isolated_home, monkeypatch):
        # Force the ffmpeg probe to fail, simulating a machine without ffmpeg.
        import aetheros_vision.video as video_mod

        monkeypatch.setattr(video_mod.shutil, "which", lambda name, **kw: None)
        from aetheros_vision.video import VideoUnderstanding

        f = tmp_path / "clip.mp4"
        f.write_bytes(b"\x00\x00\x00\x18ftypmp42")
        result = VideoUnderstanding().extract(str(f))
        assert result.success is False
        assert result.error is not None
