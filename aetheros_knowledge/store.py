"""SQLite store for Knowledge OS."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aetheros_constants import get_aetheros_home
from aetheros_knowledge.models import (
    KnowledgeDocument, DocumentChunk, KnowledgeCollection,
    Annotation, MemoryEntry, RAGPipeline, KnowledgeSource,
    DocumentStatus, SourceType, CollectionVisibility, MemoryType,
)

logger = logging.getLogger(__name__)


DEFAULT_DB_NAME = "knowledge.db"


def _default_db_path() -> str:
    """Profile-aware default knowledge database path."""
    try:
        return str(get_aetheros_home() / "knowledge" / DEFAULT_DB_NAME)
    except Exception:
        return ":memory:"


class KnowledgeStore:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = _default_db_path()
        self.db_path = db_path
        self._lock = threading.Lock()
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_db()

    def _init_db(self):
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS collections (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT DEFAULT '',
                    icon TEXT DEFAULT 'folder', color TEXT DEFAULT '#6366f1',
                    parent_id TEXT, visibility TEXT DEFAULT 'private',
                    tags TEXT DEFAULT '[]',
                    document_count INTEGER DEFAULT 0, size_bytes INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL,
                    source_type TEXT NOT NULL, source_path TEXT NOT NULL,
                    collection_id TEXT NOT NULL, status TEXT DEFAULT 'pending',
                    content_type TEXT DEFAULT '', language TEXT DEFAULT '',
                    size_bytes INTEGER DEFAULT 0, page_count INTEGER DEFAULT 0,
                    word_count INTEGER DEFAULT 0, chunk_count INTEGER DEFAULT 0,
                    checksum TEXT DEFAULT '', tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, indexed_at TEXT DEFAULT '',
                    FOREIGN KEY (collection_id) REFERENCES collections(id)
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
                    content TEXT NOT NULL, chunk_index INTEGER DEFAULT 0,
                    token_count INTEGER DEFAULT 0,
                    embedding BLOB, metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS annotations (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
                    annotation_type TEXT NOT NULL, content TEXT DEFAULT '',
                    color TEXT DEFAULT '', position_start INTEGER DEFAULT 0,
                    position_end INTEGER DEFAULT 0, page INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS memory (
                    id TEXT PRIMARY KEY, memory_type TEXT NOT NULL,
                    key TEXT NOT NULL, value TEXT NOT NULL,
                    scope TEXT DEFAULT '', tags TEXT DEFAULT '[]',
                    importance REAL DEFAULT 0.5,
                    ttl_seconds INTEGER, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, expires_at TEXT
                );
                CREATE TABLE IF NOT EXISTS rag_pipelines (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL,
                    description TEXT DEFAULT '', embedder TEXT DEFAULT 'sentence-transformers',
                    vector_store TEXT DEFAULT 'sqlite', chunk_size INTEGER DEFAULT 512,
                    chunk_overlap INTEGER DEFAULT 64, ranking TEXT DEFAULT 'cosine',
                    reranking INTEGER DEFAULT 0, hybrid_search INTEGER DEFAULT 1,
                    top_k INTEGER DEFAULT 5, config TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY, source_type TEXT NOT NULL,
                    uri TEXT NOT NULL, label TEXT DEFAULT '',
                    collection_id TEXT, config TEXT DEFAULT '{}',
                    enabled INTEGER DEFAULT 1, auto_sync INTEGER DEFAULT 0,
                    sync_interval_minutes INTEGER DEFAULT 0,
                    last_synced TEXT, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS knowledge_tags (
                    document_id TEXT NOT NULL, tag TEXT NOT NULL,
                    PRIMARY KEY (document_id, tag)
                );
                CREATE TABLE IF NOT EXISTS permissions (
                    id TEXT PRIMARY KEY, resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL, user_id TEXT,
                    permission TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS claim_evidence (
                    claim_id TEXT NOT NULL, claim_text TEXT NOT NULL,
                    evidence_id TEXT NOT NULL, evidence_type TEXT DEFAULT 'chunk',
                    support_type TEXT DEFAULT 'supports', confidence REAL DEFAULT 0.5,
                    context TEXT DEFAULT '', created_at TEXT NOT NULL,
                    created_by TEXT DEFAULT '',
                    FOREIGN KEY (evidence_id) REFERENCES chunks(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS secure_delete_audit (
                    id TEXT PRIMARY KEY, resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL, deletion_type TEXT DEFAULT 'hard',
                    requested_by TEXT, reason TEXT, deleted_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_docs_collection ON documents(collection_id);
                CREATE INDEX IF NOT EXISTS idx_docs_status ON documents(status);
                CREATE INDEX IF NOT EXISTS idx_docs_source ON documents(source_type);
                CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
                CREATE INDEX IF NOT EXISTS idx_annotations_doc ON annotations(document_id);
                CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(memory_type);
                CREATE INDEX IF NOT EXISTS idx_memory_key ON memory(key);
                CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(source_type);
                CREATE INDEX IF NOT EXISTS idx_claim_evidence_claim_id ON claim_evidence(claim_id);
                CREATE INDEX IF NOT EXISTS idx_claim_evidence_evidence_id ON claim_evidence(evidence_id);
            """)
            self._seed_collections()

    def _seed_collections(self):
        from aetheros_knowledge.models import BUILTIN_COLLECTIONS
        now = datetime.utcnow().isoformat() + "Z"
        for c in BUILTIN_COLLECTIONS:
            self._conn.execute(
                "INSERT OR IGNORE INTO collections "
                "(id, name, description, icon, color, visibility, tags, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (c.id, c.name, c.description, c.icon, c.color,
                 c.visibility.value, json.dumps(c.tags), now, now))
        self._conn.commit()

    # --- Collections ---
    def save_collection(self, c: KnowledgeCollection):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO collections "
                "(id, name, description, icon, color, parent_id, visibility, tags, "
                "document_count, size_bytes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (c.id, c.name, c.description, c.icon, c.color, c.parent_id,
                 c.visibility.value, json.dumps(c.tags),
                 c.document_count, c.size_bytes, c.created_at, c.updated_at))
            self._conn.commit()

    def get_collection(self, cid: str) -> Optional[KnowledgeCollection]:
        cur = self._conn.execute("SELECT * FROM collections WHERE id=?", (cid,))
        return self._row_to_collection(cur.fetchone())

    def list_collections(self, parent_id: str = None) -> list[KnowledgeCollection]:
        if parent_id is not None:
            cur = self._conn.execute(
                "SELECT * FROM collections WHERE parent_id=? ORDER BY name",
                (parent_id,))
        else:
            cur = self._conn.execute(
                "SELECT * FROM collections ORDER BY name")
        return [self._row_to_collection(r) for r in cur.fetchall()]

    def delete_collection(self, cid: str):
        with self._lock:
            self._conn.execute("DELETE FROM documents WHERE collection_id=?", (cid,))
            self._conn.execute("DELETE FROM collections WHERE id=?", (cid,))
            self._conn.commit()

    def update_collection_stats(self, cid: str):
        with self._lock:
            stats = self._conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(size_bytes), 0) FROM documents "
                "WHERE collection_id=? AND status!='deleted'", (cid,)).fetchone()
            self._conn.execute(
                "UPDATE collections SET document_count=?, size_bytes=? WHERE id=?",
                (stats[0], stats[1], cid))
            self._conn.commit()

    # --- Documents ---
    def save_document(self, d: KnowledgeDocument):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO documents "
                "(id, title, source_type, source_path, collection_id, status, "
                "content_type, language, size_bytes, page_count, word_count, "
                "chunk_count, checksum, tags, metadata, created_at, updated_at, indexed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (d.id, d.title, d.source_type.value, d.source_path, d.collection_id,
                 d.status.value, d.content_type, d.language, d.size_bytes,
                 d.page_count, d.word_count, d.chunk_count, d.checksum,
                 json.dumps(d.tags), json.dumps(d.metadata),
                 d.created_at, d.updated_at, d.indexed_at))
            for tag in d.tags:
                self._conn.execute(
                    "INSERT OR IGNORE INTO knowledge_tags (document_id, tag) VALUES (?, ?)",
                    (d.id, tag))
            self._conn.commit()

    def get_document(self, did: str) -> Optional[KnowledgeDocument]:
        cur = self._conn.execute("SELECT * FROM documents WHERE id=?", (did,))
        return self._row_to_document(cur.fetchone())

    def list_documents(self, collection_id: str = None,
                        source_type: str = None, status: str = None,
                        limit: int = 100, offset: int = 0) -> list[KnowledgeDocument]:
        conditions = []
        params = []
        if collection_id:
            conditions.append("collection_id=?")
            params.append(collection_id)
        if source_type:
            conditions.append("source_type=?")
            params.append(source_type)
        if status:
            conditions.append("status=?")
            params.append(status)
        where = " AND ".join(conditions) if conditions else "1=1"
        cur = self._conn.execute(
            f"SELECT * FROM documents WHERE {where} "
            f"ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset])
        return [self._row_to_document(r) for r in cur.fetchall()]

    def search_documents(self, query: str, limit: int = 20) -> list[KnowledgeDocument]:
        cur = self._conn.execute(
            "SELECT * FROM documents WHERE title LIKE ? OR tags LIKE ? "
            "ORDER BY updated_at DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit))
        return [self._row_to_document(r) for r in cur.fetchall()]

    def update_document_status(self, did: str, status: DocumentStatus):
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            self._conn.execute(
                "UPDATE documents SET status=?, updated_at=? WHERE id=?",
                (status.value, now, did))
            self._conn.commit()

    def delete_document(self, did: str):
        with self._lock:
            self._conn.execute("DELETE FROM annotations WHERE document_id=?", (did,))
            self._conn.execute("DELETE FROM chunks WHERE document_id=?", (did,))
            self._conn.execute("DELETE FROM documents WHERE id=?", (did,))
            self._conn.commit()

    def get_document_count(self) -> int:
        cur = self._conn.execute(
            "SELECT COUNT(*) FROM documents WHERE status!='deleted'")
        return cur.fetchone()[0]

    # --- Chunks ---
    def save_chunks(self, chunks: list[DocumentChunk]):
        with self._lock:
            for c in chunks:
                emb_blob = json.dumps(c.embedding).encode() if c.embedding else b""
                self._conn.execute(
                    "INSERT OR REPLACE INTO chunks "
                    "(id, document_id, content, chunk_index, token_count, embedding, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (c.id, c.document_id, c.content, c.chunk_index,
                     c.token_count, emb_blob, json.dumps(c.metadata)))
            self._conn.commit()

    def get_chunks(self, document_id: str) -> list[DocumentChunk]:
        cur = self._conn.execute(
            "SELECT * FROM chunks WHERE document_id=? ORDER BY chunk_index",
            (document_id,))
        return [self._row_to_chunk(r) for r in cur.fetchall()]

    def delete_chunks(self, document_id: str):
        with self._lock:
            self._conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            self._conn.commit()

    # --- Annotations ---
    def save_annotation(self, a: Annotation):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO annotations "
                "(id, document_id, annotation_type, content, color, "
                "position_start, position_end, page, metadata, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (a.id, a.document_id, a.annotation_type, a.content, a.color,
                 a.position_start, a.position_end, a.page,
                 json.dumps(a.metadata), a.created_at, a.updated_at))
            self._conn.commit()

    def get_annotations(self, document_id: str) -> list[Annotation]:
        cur = self._conn.execute(
            "SELECT * FROM annotations WHERE document_id=? ORDER BY created_at",
            (document_id,))
        return [self._row_to_annotation(r) for r in cur.fetchall()]

    def delete_annotation(self, aid: str):
        with self._lock:
            self._conn.execute("DELETE FROM annotations WHERE id=?", (aid,))
            self._conn.commit()

    # --- Memory ---
    def save_memory(self, m: MemoryEntry):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO memory "
                "(id, memory_type, key, value, scope, tags, importance, "
                "ttl_seconds, created_at, updated_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (m.id, m.memory_type.value, m.key, json.dumps(m.value),
                 m.scope, json.dumps(m.tags), m.importance,
                 m.ttl_seconds, m.created_at, m.updated_at, m.expires_at))
            self._conn.commit()

    def get_memory(self, key: str, memory_type: MemoryType = None) -> Optional[MemoryEntry]:
        if memory_type:
            cur = self._conn.execute(
                "SELECT * FROM memory WHERE key=? AND memory_type=?",
                (key, memory_type.value))
        else:
            cur = self._conn.execute(
                "SELECT * FROM memory WHERE key=?", (key,))
        return self._row_to_memory(cur.fetchone())

    def list_memory(self, memory_type: MemoryType = None,
                     scope: str = "", limit: int = 100) -> list[MemoryEntry]:
        conditions = []
        params = []
        if memory_type:
            conditions.append("memory_type=?")
            params.append(memory_type.value)
        if scope:
            conditions.append("scope=?")
            params.append(scope)
        where = " AND ".join(conditions) if conditions else "1=1"
        cur = self._conn.execute(
            f"SELECT * FROM memory WHERE {where} "
            f"ORDER BY importance DESC, updated_at DESC LIMIT ?",
            params + [limit])
        return [self._row_to_memory(r) for r in cur.fetchall()]

    def search_memory(self, query: str, limit: int = 20) -> list[MemoryEntry]:
        cur = self._conn.execute(
            "SELECT * FROM memory WHERE key LIKE ? OR value LIKE ? OR tags LIKE ? "
            "ORDER BY importance DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit))
        return [self._row_to_memory(r) for r in cur.fetchall()]

    def delete_memory(self, key: str, memory_type: MemoryType = None):
        with self._lock:
            if memory_type:
                self._conn.execute(
                    "DELETE FROM memory WHERE key=? AND memory_type=?",
                    (key, memory_type.value))
            else:
                self._conn.execute("DELETE FROM memory WHERE key=?", (key,))
            self._conn.commit()

    def clear_memory_type(self, memory_type: MemoryType):
        with self._lock:
            self._conn.execute("DELETE FROM memory WHERE memory_type=?",
                               (memory_type.value,))
            self._conn.commit()

    # --- RAG Pipelines ---
    def save_pipeline(self, p: RAGPipeline):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO rag_pipelines "
                "(id, name, description, embedder, vector_store, chunk_size, "
                "chunk_overlap, ranking, reranking, hybrid_search, top_k, config, "
                "created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (p.id, p.name, p.description, p.embedder, p.vector_store,
                 p.chunk_size, p.chunk_overlap, p.ranking,
                 1 if p.reranking else 0, 1 if p.hybrid_search else 0,
                 p.top_k, json.dumps(p.config), p.created_at, p.updated_at))
            self._conn.commit()

    def list_pipelines(self) -> list[RAGPipeline]:
        cur = self._conn.execute("SELECT * FROM rag_pipelines ORDER BY created_at DESC")
        return [self._row_to_pipeline(r) for r in cur.fetchall()]

    def delete_pipeline(self, pid: str):
        with self._lock:
            self._conn.execute("DELETE FROM rag_pipelines WHERE id=?", (pid,))
            self._conn.commit()

    # --- Sources ---
    def save_source(self, s: KnowledgeSource):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO sources "
                "(id, source_type, uri, label, collection_id, config, "
                "enabled, auto_sync, sync_interval_minutes, last_synced, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (s.id, s.source_type.value, s.uri, s.label, s.collection_id,
                 json.dumps(s.config), 1 if s.enabled else 0,
                 1 if s.auto_sync else 0, s.sync_interval_minutes,
                 s.last_synced, s.created_at))
            self._conn.commit()

    def list_sources(self, source_type: str = None) -> list[KnowledgeSource]:
        if source_type:
            cur = self._conn.execute(
                "SELECT * FROM sources WHERE source_type=? ORDER BY created_at DESC",
                (source_type,))
        else:
            cur = self._conn.execute(
                "SELECT * FROM sources ORDER BY created_at DESC")
        return [self._row_to_source(r) for r in cur.fetchall()]

    def delete_source(self, sid: str):
        with self._lock:
            self._conn.execute("DELETE FROM sources WHERE id=?", (sid,))
            self._conn.commit()

    # --- Stats ---
    def get_stats(self) -> dict:
        docs = self._conn.execute(
            "SELECT COUNT(*) FROM documents WHERE status!='deleted'").fetchone()[0]
        indexed = self._conn.execute(
            "SELECT COUNT(*) FROM documents WHERE status='indexed'").fetchone()[0]
        chunks = self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        collections = self._conn.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
        mem = self._conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
        by_source = self._conn.execute(
            "SELECT source_type, COUNT(*) FROM documents "
            "WHERE status!='deleted' GROUP BY source_type").fetchall()
        return {
            "documents": docs, "indexed": indexed, "chunks": chunks,
            "collections": collections, "memory_entries": mem,
            "by_source": dict(by_source),
        }

    def close(self):
        self._conn.close()

    # --- Row mappers ---
    @staticmethod
    def _row_to_collection(row) -> Optional[KnowledgeCollection]:
        if not row:
            return None
        return KnowledgeCollection(
            id=row[0], name=row[1], description=row[2], icon=row[3],
            color=row[4], parent_id=row[5],
            visibility=CollectionVisibility(row[6]),
            tags=json.loads(row[7]) if isinstance(row[7], str) else row[7],
            document_count=row[8], size_bytes=row[9],
            created_at=row[10], updated_at=row[11])

    @staticmethod
    def _row_to_document(row) -> Optional[KnowledgeDocument]:
        if not row:
            return None
        return KnowledgeDocument(
            id=row[0], title=row[1], source_type=SourceType(row[2]),
            source_path=row[3], collection_id=row[4],
            status=DocumentStatus(row[5]),
            content_type=row[6], language=row[7],
            size_bytes=row[8], page_count=row[9], word_count=row[10],
            chunk_count=row[11], checksum=row[12],
            tags=json.loads(row[13]) if isinstance(row[13], str) else row[13],
            metadata=json.loads(row[14]) if isinstance(row[14], str) else row[14],
            created_at=row[15], updated_at=row[16], indexed_at=row[17])

    @staticmethod
    def _row_to_chunk(row) -> DocumentChunk:
        emb = []
        if row[5] and len(row[5]) > 2:
            try:
                emb = json.loads(row[5].decode())
            except Exception:
                pass
        return DocumentChunk(
            id=row[0], document_id=row[1], content=row[2],
            chunk_index=row[3], token_count=row[4], embedding=emb,
            metadata=json.loads(row[6]) if isinstance(row[6], str) else row[6])

    @staticmethod
    def _row_to_annotation(row) -> Annotation:
        return Annotation(
            id=row[0], document_id=row[1], annotation_type=row[2],
            content=row[3], color=row[4],
            position_start=row[5], position_end=row[6], page=row[7],
            metadata=json.loads(row[8]) if isinstance(row[8], str) else row[8],
            created_at=row[9], updated_at=row[10])

    @staticmethod
    def _row_to_memory(row) -> Optional[MemoryEntry]:
        if not row:
            return None
        return MemoryEntry(
            id=row[0], memory_type=MemoryType(row[1]), key=row[2],
            value=json.loads(row[3]) if isinstance(row[3], str) else row[3],
            scope=row[4],
            tags=json.loads(row[5]) if isinstance(row[5], str) else row[5],
            importance=row[6], ttl_seconds=row[7],
            created_at=row[8], updated_at=row[9], expires_at=row[10])

    @staticmethod
    def _row_to_pipeline(row) -> RAGPipeline:
        return RAGPipeline(
            id=row[0], name=row[1], description=row[2], embedder=row[3],
            vector_store=row[4], chunk_size=row[5], chunk_overlap=row[6],
            ranking=row[7], reranking=bool(row[8]),
            hybrid_search=bool(row[9]), top_k=row[10],
            config=json.loads(row[11]) if isinstance(row[11], str) else row[11],
            created_at=row[12], updated_at=row[13])

    @staticmethod
    def _row_to_source(row) -> KnowledgeSource:
        return KnowledgeSource(
            id=row[0], source_type=SourceType(row[1]), uri=row[2],
            label=row[3], collection_id=row[4],
            config=json.loads(row[5]) if isinstance(row[5], str) else row[5],
            enabled=bool(row[6]), auto_sync=bool(row[7]),
            sync_interval_minutes=row[8], last_synced=row[9],
            created_at=row[10])
