"""Tests for aetheros_vision.capture — fallback behavior when no backend exists."""

import pytest


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path / ".aetheros"))
    return tmp_path / ".aetheros"


class TestScreenCaptureRuntime:
    def test_is_available(self, isolated_home):
        from aetheros_vision.capture import ScreenCaptureRuntime

        rt = ScreenCaptureRuntime()
        assert isinstance(rt.is_available(), bool)

    def test_capture_result_shape(self, isolated_home):
        from aetheros_vision.capture import ScreenCaptureRuntime

        rt = ScreenCaptureRuntime()
        result = rt.capture()
        # Either it succeeds (real display) or fails cleanly with an error —
        # never raises and never fabricates a success.
        if result.success:
            assert result.path
            assert result.width > 0
            assert result.height > 0
        else:
            assert result.error

    def test_capture_with_output_path(self, tmp_path, isolated_home):
        from aetheros_vision.capture import ScreenCaptureRuntime

        out = tmp_path / "shots" / "cap.png"
        rt = ScreenCaptureRuntime()
        result = rt.capture(output_path=str(out))
        if result.success:
            assert out.exists()
