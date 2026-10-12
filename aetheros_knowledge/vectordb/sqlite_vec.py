"""SQLite-based vector database with cosine similarity."""

from __future__ import annotations

import json
import math
import sqlite3
import threading
from typing import Any, Optional

from aetheros_knowledge.vectordb.base import VectorDB, SearchResult


class SQLiteVectorDB(VectorDB):
    def __init__(self, db_path: str = ":memory:", dimension: int = 384):
        self.db_path = db_path
        self.dimension = dimension
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS vector_store (
                    id TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    document_id TEXT DEFAULT '',
                    chunk_index INTEGER DEFAULT 0
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_vector_doc
                ON vector_store(document_id)
            """)
            self._conn.commit()

    def add(self, chunk_id: str, embedding: list[float],
             content: str, metadata: dict = None) -> None:
        meta = metadata or {}
        emb_blob = json.dumps(embedding).encode()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO vector_store "
                "(id, embedding, content, metadata, document_id, chunk_index) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (chunk_id, emb_blob, content, json.dumps(meta),
                 meta.get("document_id", ""), meta.get("chunk_index", 0)))
            self._conn.commit()

    def add_batch(self, ids: list[str], embeddings: list[list[float]],
                   contents: list[str], metadatas: list[dict] = None) -> None:
        with self._lock:
            for i, cid in enumerate(ids):
                meta = (metadatas[i] if metadatas and i < len(metadatas)
                        else {})
                emb_blob = json.dumps(embeddings[i]).encode()
                self._conn.execute(
                    "INSERT OR REPLACE INTO vector_store "
                    "(id, embedding, content, metadata, document_id, chunk_index) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (cid, emb_blob, contents[i], json.dumps(meta),
                     meta.get("document_id", ""), meta.get("chunk_index", 0)))
            self._conn.commit()

    def search(self, embedding: list[float], top_k: int = 10,
               filters: dict = None) -> list[SearchResult]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, embedding, content, metadata, document_id, chunk_index "
                "FROM vector_store")
            rows = cur.fetchall()
        results = []
        for row in rows:
            cid, emb_blob, content, meta_json, doc_id, chunk_idx = row
            stored_emb = json.loads(emb_blob.decode())
            score = self._cosine_similarity(embedding, stored_emb)
            meta = json.loads(meta_json) if isinstance(meta_json, str) else {}
            if filters:
                matched = True
                for k, v in filters.items():
                    if meta.get(k) != v:
                        matched = False
                        break
                if not matched:
                    continue
            results.append(SearchResult(
                id=cid, score=score, content=content,
                metadata=meta, document_id=doc_id,
                chunk_index=chunk_idx))
        results.sort(key=lambda x: -x.score)
        return results[:top_k]

    def delete(self, chunk_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM vector_store WHERE id=?", (chunk_id,))
            self._conn.commit()

    def delete_by_metadata(self, key: str, value: Any) -> None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id FROM vector_store WHERE metadata LIKE ?",
                (f'%"{key}": "{value}"%',))
            ids = [r[0] for r in cur.fetchall()]
            for cid in ids:
                self._conn.execute("DELETE FROM vector_store WHERE id=?", (cid,))
            self._conn.commit()

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM vector_store").fetchone()[0]

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if not na or not nb:
            return 0.0
        return dot / (na * nb)
