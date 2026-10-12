"""Indexing pipeline — parse, chunk, embed, index."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aetheros_knowledge.store import KnowledgeStore
from aetheros_knowledge.models import (
    KnowledgeDocument, DocumentChunk, DocumentStatus,
)
from aetheros_knowledge.indexing.parsers import get_parser
from aetheros_knowledge.indexing.chunkers import chunk_text
from aetheros_knowledge.indexing.embedders import get_embedder
from aetheros_knowledge.indexing.detectors import detect_language, detect_duplicates

logger = logging.getLogger(__name__)

# Embedding version format: "provider:model:dimensions:YYYYMMDD"
def _embedding_version(embedder) -> str:
    try:
        dims = getattr(embedder, "dimensions", None)
        provider = getattr(embedder, "provider_name", "unknown")
        model = getattr(embedder, "model_name", "unknown")
        if dims is None:
            dims = 0
    except Exception:
        provider, model, dims = "unknown", "unknown", 0
    from datetime import date
    return f"{provider}:{model}:{dims}:{date.today().strftime('%Y%m%d')}"


def _file_fingerprint(path: str) -> Optional[dict]:
    """Return {checksum, mtime, size} for a file, or None if not found."""
    try:
        p = Path(path)
        if not p.exists() or not p.is_file():
            return None
        st = p.stat()
        content = p.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()[:16]
        return {"checksum": checksum, "mtime": st.st_mtime, "size": st.st_size}
    except Exception:
        return None


class IndexingPipeline:
    def __init__(self, store: KnowledgeStore,
                 embedder_name: str = "sentence-transformers",
                 chunk_size: int = 512,
                 chunk_overlap: int = 64):
        self.store = store
        self.embedder_name = embedder_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._embedder = None

    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = get_embedder(self.embedder_name)
        return self._embedder

    def _is_unchanged(self, doc: KnowledgeDocument) -> bool:
        """Incremental indexing: skip if file checksum+mtime unchanged."""
        fp = _file_fingerprint(doc.source_path)
        if fp is None:
            return False
        meta = doc.metadata or {}
        old_fp = meta.get("_file_fingerprint")
        if old_fp and old_fp.get("checksum") == fp["checksum"] and old_fp.get("mtime") == fp["mtime"]:
            return True
        return False

    def index_document(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        logger.info("Indexing document: %s (%s)", doc.title, doc.id)

        # Incremental indexing: skip if unchanged
        if self._is_unchanged(doc):
            logger.info("Skipping unchanged document: %s", doc.id)
            return doc

        self.store.update_document_status(doc.id, DocumentStatus.INDEXING)

        try:
            parser = get_parser(doc.source_type)
            content = parser(doc.source_path)
        except Exception as e:
            logger.error("Parse error for %s: %s", doc.id, e)
            self.store.update_document_status(doc.id, DocumentStatus.FAILED)
            return doc

        lang = detect_language(content)
        doc.language = lang

        # Store file fingerprint for incremental indexing
        fp = _file_fingerprint(doc.source_path)
        if fp:
            doc.metadata = doc.metadata or {}
            doc.metadata["_file_fingerprint"] = fp

        chunks = chunk_text(content, chunk_size=self.chunk_size,
                             chunk_overlap=self.chunk_overlap)
        doc.word_count = len(content.split())
        doc.chunk_count = len(chunks)

        # Secret scan before embedding (Phases 89-90)
        try:
            from agent.redact import redact_sensitive_text
        except Exception:
            redact_sensitive_text = None

        doc_chunks = []
        embed_ver = _embedding_version(self.embedder)
        for i, chunk_text_content in enumerate(chunks):
            cid = str(uuid.uuid4())
            # Redact secrets from chunk before embedding
            safe_chunk = chunk_text_content
            if redact_sensitive_text:
                safe_chunk = redact_sensitive_text(chunk_text_content, force=False, code_file=False)
            embedding = self.embedder.embed(safe_chunk)
            token_count = len(safe_chunk.split())
            dc = DocumentChunk(
                id=cid, document_id=doc.id, content=safe_chunk,
                chunk_index=i, token_count=token_count,
                embedding=embedding,
                metadata={
                    "language": lang,
                    "chunk_size": len(safe_chunk),
                    "embedding_version": embed_ver,
                    "redacted": safe_chunk != chunk_text_content,
                })
            doc_chunks.append(dc)

        self.store.delete_chunks(doc.id)
        self.store.save_chunks(doc_chunks)

        doc.status = DocumentStatus.INDEXED
        doc.indexed_at = datetime.utcnow().isoformat() + "Z"
        doc.updated_at = datetime.utcnow().isoformat() + "Z"
        self.store.save_document(doc)
        self.store.update_collection_stats(doc.collection_id)

        logger.info("Indexed %s: %d chunks (embed_ver=%s)", doc.id, len(doc_chunks), embed_ver)
        return doc

    def reindex_document(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        # Force reindex even if unchanged
        doc.metadata = doc.metadata or {}
        doc.metadata.pop("_file_fingerprint", None)
        return self.index_document(doc)

    def is_embedding_outdated(self, doc: KnowledgeDocument) -> bool:
        """Check if document's chunks use an outdated embedding model/version."""
        current_ver = _embedding_version(self.embedder)
        chunks = self.store.get_chunks(doc.id)
        for c in chunks:
            meta = c.metadata or {}
            if meta.get("embedding_version") != current_ver:
                return True
        return False

    def reindex_outdated(self) -> list[KnowledgeDocument]:
        """Reindex all documents whose embeddings are outdated."""
        docs = self.store.list_documents()
        results = []
        for d in docs:
            if self.is_embedding_outdated(d):
                try:
                    r = self.reindex_document(d)
                    results.append(r)
                except Exception as e:
                    logger.error("Reindex outdated error for %s: %s", d.id, e)
        return results

    def handle_source_deleted(self, doc: KnowledgeDocument) -> None:
        """Deletion propagation: mark document deleted, remove chunks, tombstone."""
        logger.info("Source deleted, propagating tombstone for %s", doc.id)
        doc.status = DocumentStatus.DELETED
        doc.updated_at = datetime.utcnow().isoformat() + "Z"
        self.store.save_document(doc)
        self.store.delete_chunks(doc.id)
        self.store.update_collection_stats(doc.collection_id)

    def scan_for_deleted_sources(self) -> list[str]:
        """Scan all indexed documents for missing source files.
        Returns list of document IDs whose source files are gone."""
        deleted = []
        docs = self.store.list_documents(status="indexed")
        for d in docs:
            if d.source_path and not Path(d.source_path).exists():
                deleted.append(d.id)
        return deleted

    def propagate_deletions(self) -> int:
        """Find and tombstone documents whose source files are gone."""
        deleted_ids = self.scan_for_deleted_sources()
        for did in deleted_ids:
            doc = self.store.get_document(did)
            if doc:
                self.handle_source_deleted(doc)
        if deleted_ids:
            logger.warning("Propagated deletion for %d documents", len(deleted_ids))
        return len(deleted_ids)

    def index_all_pending(self) -> list[KnowledgeDocument]:
        docs = self.store.list_documents(status="pending")
        results = []
        for d in docs:
            try:
                r = self.index_document(d)
                results.append(r)
            except Exception as e:
                logger.error("Index error for %s: %s", d.id, e)
        return results

    def bulk_index(self, doc_ids: list[str]) -> list[KnowledgeDocument]:
        results = []
        for did in doc_ids:
            doc = self.store.get_document(did)
            if doc:
                try:
                    results.append(self.index_document(doc))
                except Exception as e:
                    logger.error("Bulk index error for %s: %s", did, e)
        return results
