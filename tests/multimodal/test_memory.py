import pytest
import os
import tempfile
from agent.multimodal.memory import MultimodalMemoryStore, default_store
from agent.multimodal.media_abstraction import MediaObject, MediaType, SensitivityLevel
from agent.multimodal.provenance import GroundedFact, EvidenceRef


def test_store_media():
    import tempfile
    import os
    from PIL import Image
    
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MultimodalMemoryStore(tmpdir)
        
        # Create a real temp image file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            img = Image.new('RGB', (100, 100), color='red')
            img.save(tmp.name, format='JPEG')
            tmp_path = tmp.name
        
        try:
            media = MediaObject(
                media_id="test1",
                type=MediaType.IMAGE,
                source=tmp_path,
                mime_type="image/jpeg",
                sensitivity=SensitivityLevel.PRIVATE,
            )
            entry_id = store.store_media(media, content="test content")
            assert entry_id is not None
            assert store.count() == 1
            retrieved = store.get(entry_id)
            assert retrieved is not None
            assert retrieved.kind == "image"
            assert retrieved.content == "test content"
            assert retrieved.hash == media.hash
        finally:
            try:
                os.unlink(tmp_path)
            except PermissionError:
                pass


def test_store_fact():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MultimodalMemoryStore(tmpdir)
        evidence = EvidenceRef(
            media_id="test1",
            source="/fake/path.jpg",
            confidence=0.9,
        )
        fact = GroundedFact(
            claim="The sky is blue.",
            evidence=evidence,
        )
        entry_id = store.store_fact(fact)
        assert entry_id is not None
        assert store.count() == 1
        retrieved = store.get(entry_id)
        assert retrieved is not None
        assert retrieved.kind == "fact"
        assert retrieved.content == "The sky is blue."
        assert retrieved.metadata["fact_id"] == fact.fact_id


def test_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MultimodalMemoryStore(tmpdir)
        media1 = MediaObject(
            media_id="test1",
            type=MediaType.IMAGE,
            source="/fake/path1.jpg",
            mime_type="image/jpeg",
            sensitivity=SensitivityLevel.PRIVATE,
        )
        media2 = MediaObject(
            media_id="test2",
            type=MediaType.TEXT,
            source="/fake/path2.txt",
            mime_type="text/plain",
            sensitivity=SensitivityLevel.PRIVATE,
        )
        store.store_media(media1, content="hello world")
        store.store_media(media2, content="goodbye world")
        results = store.search("hello", limit=10)
        assert len(results) == 1
        assert results[0].content == "hello world"
        results = store.search("world", limit=10)
        assert len(results) == 2  # both contain world


def test_delete():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MultimodalMemoryStore(tmpdir)
        media = MediaObject(
            media_id="test1",
            type=MediaType.IMAGE,
            source="/fake/path.jpg",
            mime_type="image/jpeg",
            sensitivity=SensitivityLevel.PRIVATE,
        )
        entry_id = store.store_media(media)
        assert store.count() == 1
        assert store.delete(entry_id) is True
        assert store.count() == 0
        assert store.get(entry_id) is None
        assert store.delete(entry_id) is False  # already deleted


def test_default_store():
    # This should return a store instance
    store = default_store()
    assert isinstance(store, MultimodalMemoryStore)
    # Calling again should return the same instance (singleton pattern)
    store2 = default_store()
    assert store is store2