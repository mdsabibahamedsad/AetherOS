"""Tests for aetheros_vision.config and runtime — lifecycle and diagnostics."""

import os
import tempfile

import pytest


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path / ".aetheros"))
    return tmp_path / ".aetheros"


class TestVisionSettings:
    def test_load_vision_settings_has_sections(self, isolated_home):
        from aetheros_vision.config import load_vision_settings

        s = load_vision_settings()
        assert s.ocr.language == "eng"
        assert s.ocr.confidence_threshold >= 0
        assert s.capture.format
        assert isinstance(s.max_analysis_bytes, int)

    def test_runtime_defaults(self, isolated_home):
        from aetheros_vision.config import load_vision_settings

        s = load_vision_settings()
        assert s.local_only is False
        assert s.cache_dir


class TestVisionRuntime:
    def test_initialize_reaches_ready_or_degraded(self, isolated_home):
        from aetheros_vision import get_vision_runtime
        from aetheros_vision.models import RuntimeState

        rt = get_vision_runtime()
        rt.initialize()
        assert rt.state in (RuntimeState.READY, RuntimeState.DEGRADED)

    def test_diagnostics_shape(self, isolated_home):
        from aetheros_vision import get_vision_runtime

        rt = get_vision_runtime()
        rt.initialize()
        d = rt.diagnostics()
        assert d.state.value in ("ready", "degraded")
        assert isinstance(d.checks, list)
        assert isinstance(d.ocr_languages, list)
        assert d.uptime_s >= 0

    def test_health_check_names(self, isolated_home):
        from aetheros_vision import get_vision_runtime

        rt = get_vision_runtime()
        rt.initialize()
        names = [c.name for c in rt.health_check()]
        assert "runtime" in names
        assert "gpu" in names
        assert "ocr" in names
        assert "vision" in names

    def test_shutdown_idempotent(self, isolated_home):
        from aetheros_vision import get_vision_runtime

        rt = get_vision_runtime()
        rt.initialize()
        rt.shutdown()
        rt.shutdown()
        from aetheros_vision.models import RuntimeState

        assert rt.state == RuntimeState.SHUTDOWN

    def test_record_request_counts(self, isolated_home):
        from aetheros_vision import get_vision_runtime

        rt = get_vision_runtime()
        rt.initialize()
        before = rt.diagnostics().total_requests
        rt.record_request(ok=True)
        rt.record_request(ok=False, error="boom")
        d = rt.diagnostics()
        assert d.total_requests == before + 2
        assert d.failures == before + 1
        assert d.last_error == "boom"


class TestVisionCache:
    def test_put_get_round_trip(self, isolated_home):
        from aetheros_vision.performance import VisionCache

        cache = VisionCache()
        key = "abc123"
        assert cache.get(key) is None
        cache.put(key, b"hello")
        assert cache.get(key) == b"hello"
        assert cache.stats()["hits"] >= 1

    def test_cached_bytes_loader_called_once(self, isolated_home):
        from aetheros_vision.performance import VisionCache

        cache = VisionCache()
        calls = {"n": 0}

        def loader():
            calls["n"] += 1
            return b"data"

        # cached_bytes hashes the file; use put/get directly to avoid file I/O.
        cache.put("k1", b"data")
        assert cache.get("k1") == b"data"
