"""Tests for aetheros_vision.context — vision memory store and multimodal context."""

import pytest


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path / ".aetheros"))
    return tmp_path / ".aetheros"


class TestVisionMemory:
    def test_store_and_retrieve(self, isolated_home):
        from aetheros_vision.context import VisionMemory
        from aetheros_vision.models import VisionMemoryKind, VisionMemoryRecord

        mem = VisionMemory()
        rec = mem.store(VisionMemoryRecord(kind=VisionMemoryKind.SCREENSHOT, content="invoice total", tags=["invoice"]))
        assert mem.count() == 1
        fetched = mem.get(rec.id)
        assert fetched is not None
        assert fetched.content == "invoice total"

    def test_search_by_query(self, isolated_home):
        from aetheros_vision.context import VisionMemory
        from aetheros_vision.models import VisionMemoryKind, VisionMemoryRecord

        mem = VisionMemory()
        mem.store(VisionMemoryRecord(kind=VisionMemoryKind.CHART, content="quarterly revenue chart", tags=["finance"]))
        mem.store(VisionMemoryRecord(kind=VisionMemoryKind.SCREENSHOT, content="desktop workspace", tags=["ui"]))
        hits = mem.search("revenue")
        assert len(hits) == 1
        assert hits[0].kind == VisionMemoryKind.CHART

    def test_search_by_tag_and_kind(self, isolated_home):
        from aetheros_vision.context import VisionMemory
        from aetheros_vision.models import VisionMemoryKind, VisionMemoryRecord

        mem = VisionMemory()
        mem.store(VisionMemoryRecord(kind=VisionMemoryKind.DOCUMENT, content="spec", tags=["docs"]))
        mem.store(VisionMemoryRecord(kind=VisionMemoryKind.DOCUMENT, content="spec2", tags=["other"]))
        hits = mem.search(kind=VisionMemoryKind.DOCUMENT, tag="docs")
        assert len(hits) == 1
        assert hits[0].content == "spec"

    def test_delete(self, isolated_home):
        from aetheros_vision.context import VisionMemory
        from aetheros_vision.models import VisionMemoryKind, VisionMemoryRecord

        mem = VisionMemory()
        rec = mem.store(VisionMemoryRecord(kind=VisionMemoryKind.OBJECT, content="cat"))
        assert mem.delete(rec.id) is True
        assert mem.count() == 0
        assert mem.delete(rec.id) is False

    def test_list_kinds(self, isolated_home):
        from aetheros_vision.context import VisionMemory
        from aetheros_vision.models import VisionMemoryKind, VisionMemoryRecord

        mem = VisionMemory()
        mem.store(VisionMemoryRecord(kind=VisionMemoryKind.SCREENSHOT, content="a"))
        mem.store(VisionMemoryRecord(kind=VisionMemoryKind.SCREENSHOT, content="b"))
        mem.store(VisionMemoryRecord(kind=VisionMemoryKind.OBJECT, content="c"))
        kinds = mem.list_kinds()
        assert kinds["screenshot"] == 2
        assert kinds["object"] == 1

    def test_persists_across_instances(self, isolated_home):
        from aetheros_vision.context import VisionMemory
        from aetheros_vision.models import VisionMemoryKind, VisionMemoryRecord

        mem = VisionMemory()
        rec = mem.store(VisionMemoryRecord(kind=VisionMemoryKind.CAPTION, content="caption text"))
        mem2 = VisionMemory()
        fetched = mem2.get(rec.id)
        assert fetched is not None
        assert fetched.content == "caption text"


class TestMultimodalContext:
    def test_build_returns_bundle(self, isolated_home):
        from aetheros_vision.context import MultimodalContext

        ctx = MultimodalContext()
        ctx.add_message("user", "hello")
        bundle = ctx.build(query="hello")
        assert "query" in bundle
        assert "chat" in bundle
        assert len(bundle["chat"]) == 1
        assert "memory" in bundle
