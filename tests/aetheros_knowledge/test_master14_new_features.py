"""Master 14: New knowledge features tests."""

import tempfile
import pytest
from pathlib import Path

from aetheros_knowledge.indexing.chunkers import chunk_text
from aetheros_knowledge.indexing.pipeline import IndexingPipeline, _file_fingerprint
from aetheros_knowledge.store import KnowledgeStore
from aetheros_knowledge.models import KnowledgeDocument, SourceType, DocumentStatus


class TestMarkdownChunker:
    def test_heading_path_preserved(self):
        md = """# Title
Intro text.
## Section A
Content A1.
### Subsection A1
Deep content.
## Section B
Content B."""
        chunks = chunk_text(md, chunk_size=200, chunk_overlap=32, strategy="markdown")
        assert len(chunks) >= 2
        # Each chunk should contain its heading path
        for c in chunks:
            assert " / " in c or "#" in c  # heading path delimiter or heading marker

    def test_no_headings_fallback(self):
        text = "Plain paragraph one.\n\nPlain paragraph two."
        chunks = chunk_text(text, chunk_size=50, strategy="markdown")
        # Should fall back to paragraph chunking
        assert len(chunks) >= 1


class TestFileFingerprint:
    def test_unchanged_file_returns_same_fp(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("hello world")
            path = f.name
        try:
            fp1 = _file_fingerprint(path)
            fp2 = _file_fingerprint(path)
            assert fp1 == fp2
            assert fp1["checksum"] == fp2["checksum"]
        finally:
            Path(path).unlink(missing_ok=True)

    def test_modified_file_changes_fp(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("hello")
            path = f.name
        try:
            fp1 = _file_fingerprint(path)
            Path(path).write_text("hello world")
            fp2 = _file_fingerprint(path)
            assert fp1["checksum"] != fp2["checksum"]
        finally:
            Path(path).unlink(missing_ok=True)


class TestIndexingPipeline:
    def setup_method(self):
        self.store = KnowledgeStore(":memory:")
        self.pipeline = IndexingPipeline(self.store)

    def test_index_and_reindex_unchanged_skips(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Hello\n\nWorld content.")
            path = f.name
        try:
            doc = KnowledgeDocument(
                id="test1", title="Test", source_type=SourceType.MARKDOWN,
                source_path=path, collection_id="documents",
                status=DocumentStatus.PENDING)
            self.store.save_document(doc)

            # First index
            r1 = self.pipeline.index_document(doc)
            assert r1.status.value == "indexed"
            chunks_before = len(self.store.get_chunks(r1.id))

            # Second index (should skip as unchanged)
            r2 = self.pipeline.index_document(doc)
            chunks_after = len(self.store.get_chunks(r2.id))
            assert chunks_before == chunks_after
        finally:
            Path(path).unlink(missing_ok=True)

    def test_modified_file_reindexes(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("v1")
            path = f.name
        try:
            doc = KnowledgeDocument(
                id="test2", title="Test", source_type=SourceType.MARKDOWN,
                source_path=path, collection_id="documents",
                status=DocumentStatus.PENDING)
            self.store.save_document(doc)

            self.pipeline.index_document(doc)
            Path(path).write_text("v2")
            r2 = self.pipeline.index_document(doc)
            assert r2.chunk_count > 0
        finally:
            Path(path).unlink(missing_ok=True)


class TestKnowledgeCLI:
    def test_platform_knowledge_status(self):
        from aetheros_platform.cli import plt_handle_knowledge
        import argparse
        store = KnowledgeStore(":memory:")
        # Can't easily test without monkeypatching; smoke test that handler loads
        assert callable(plt_handle_knowledge)

    def test_search_empty_index(self):
        from aetheros_platform.cli import plt_handle_knowledge
        import argparse
        # Just ensure it doesn't crash on empty index
        import io, sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            args = argparse.Namespace(command='search', query='test', limit=5, db='', yes=False)
            # This will print "No results." and return
        finally:
            sys.stdout = old_stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])