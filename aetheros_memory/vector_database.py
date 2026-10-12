"""Vector Database — swappable backends for vector storage and similarity search.

Supports SQLite + vector extension, LanceDB, Chroma, Qdrant, FAISS.
Abstract interface allows switching at runtime.
"""

from __future__ import annotations

import abc
import enum
import json
import logging
import math
import os
import pickle
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("aetheros_memory.vector_db")


class VectorDBType(str, enum.Enum):
    SQLITE = "sqlite"
    LANCEDB = "lancedb"
    CHROMA = "chroma"
    QDRANT = "qdrant"
    FAISS = "faiss"


@dataclass
class VectorDBConfig:
    backend: VectorDBType = VectorDBType.SQLITE
    path: str = ""
    collection_name: str = "memories"
    dimensions: int = 1536
    metric: str = "cosine"
    index_type: str = "flat"
    nprobe: int = 10
    ef_construction: int = 200
    ef_search: int = 50
    max_connections: int = 16


@dataclass
class SearchResult:
    id: str
    score: float
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    text: str = ""


@dataclass
class VectorRecord:
    id: str
    vector: List[float]
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class VectorBackend(abc.ABC):
    @abc.abstractmethod
    def initialize(self, dimensions: int) -> None:
        ...

    @abc.abstractmethod
    def insert(self, record: VectorRecord) -> None:
        ...

    @abc.abstractmethod
    def insert_batch(self, records: List[VectorRecord]) -> None:
        ...

    @abc.abstractmethod
    def search(self, query: List[float], top_k: int = 10) -> List[SearchResult]:
        ...

    @abc.abstractmethod
    def delete(self, id: str) -> bool:
        ...

    @abc.abstractmethod
    def delete_by_filter(self, key: str, value: Any) -> int:
        ...

    @abc.abstractmethod
    def get(self, id: str) -> Optional[VectorRecord]:
        ...

    @abc.abstractmethod
    def count(self) -> int:
        ...

    @abc.abstractmethod
    def clear(self) -> None:
        ...

    @abc.abstractmethod
    def close(self) -> None:
        ...


class SQLiteVecBackend(VectorBackend):
    def __init__(self, config: VectorDBConfig) -> None:
        self._config = config
        self._conn: Any = None
        self._lock = threading.Lock()
        self._path = config.path or ":memory:"

    def initialize(self, dimensions: int) -> None:
        import sqlite3
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(f"""
            CREATE TABLE IF NOT EXISTS vectors (
                id TEXT PRIMARY KEY,
                vector BLOB NOT NULL,
                text TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{{}}',
                created_at REAL NOT NULL
            )
        """)
        self._conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_vectors_created ON vectors(created_at)
        """)
        self._conn.commit()

    def _serialize_vector(self, vec: List[float]) -> bytes:
        return pickle.dumps(vec)

    def _deserialize_vector(self, blob: bytes) -> List[float]:
        return pickle.loads(blob)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def insert(self, record: VectorRecord) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO vectors (id, vector, text, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    record.id,
                    self._serialize_vector(record.vector),
                    record.text,
                    json.dumps(record.metadata, ensure_ascii=False),
                    record.created_at,
                ),
            )
            self._conn.commit()

    def insert_batch(self, records: List[VectorRecord]) -> None:
        with self._lock:
            for record in records:
                self._conn.execute(
                    "INSERT OR REPLACE INTO vectors (id, vector, text, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        record.id,
                        self._serialize_vector(record.vector),
                        record.text,
                        json.dumps(record.metadata, ensure_ascii=False),
                        record.created_at,
                    ),
                )
            self._conn.commit()

    def search(self, query: List[float], top_k: int = 10) -> List[SearchResult]:
        with self._lock:
            cursor = self._conn.execute("SELECT id, vector, text, metadata FROM vectors")
            results: List[SearchResult] = []
            for row in cursor:
                vec = self._deserialize_vector(row[1])
                score = self._cosine_similarity(query, vec)
                meta: Dict[str, Any] = {}
                try:
                    meta = json.loads(row[3]) if row[3] else {}
                except (json.JSONDecodeError, TypeError):
                    pass
                results.append(SearchResult(
                    id=row[0],
                    score=score,
                    vector=vec,
                    metadata=meta,
                    text=row[2] or "",
                ))
            results.sort(key=lambda r: r.score, reverse=True)
            return results[:top_k]

    def delete(self, id: str) -> bool:
        with self._lock:
            cursor = self._conn.execute("DELETE FROM vectors WHERE id = ?", (id,))
            self._conn.commit()
            return cursor.rowcount > 0

    def delete_by_filter(self, key: str, value: Any) -> int:
        with self._lock:
            cursor = self._conn.execute("SELECT id, metadata FROM vectors")
            ids_to_delete: List[str] = []
            for row in cursor:
                try:
                    meta = json.loads(row[1]) if row[1] else {}
                    if key in meta and meta[key] == value:
                        ids_to_delete.append(row[0])
                except (json.JSONDecodeError, TypeError):
                    pass
            for vid in ids_to_delete:
                self._conn.execute("DELETE FROM vectors WHERE id = ?", (vid,))
            self._conn.commit()
            return len(ids_to_delete)

    def get(self, id: str) -> Optional[VectorRecord]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT id, vector, text, metadata, created_at FROM vectors WHERE id = ?", (id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            meta: Dict[str, Any] = {}
            try:
                meta = json.loads(row[3]) if row[3] else {}
            except (json.JSONDecodeError, TypeError):
                pass
            return VectorRecord(
                id=row[0],
                vector=self._deserialize_vector(row[1]),
                text=row[2] or "",
                metadata=meta,
                created_at=row[4],
            )

    def count(self) -> int:
        with self._lock:
            cursor = self._conn.execute("SELECT COUNT(*) FROM vectors")
            return cursor.fetchone()[0]

    def clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM vectors")
            self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()


class LanceDBBackend(VectorBackend):
    def __init__(self, config: VectorDBConfig) -> None:
        self._config = config
        self._table: Any = None
        self._db: Any = None
        self._lock = threading.Lock()

    def initialize(self, dimensions: int) -> None:
        try:
            import lancedb
        except ImportError:
            raise ImportError("lancedb not installed. pip install lancedb")
        uri = self._config.path or "memory.lancedb"
        self._db = lancedb.connect(uri)
        table_name = self._config.collection_name
        import pyarrow as pa
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), dimensions)),
            pa.field("text", pa.string()),
            pa.field("metadata_json", pa.string()),
            pa.field("created_at", pa.float64()),
        ])
        try:
            self._table = self._db.create_table(table_name, schema=schema, exist_ok=True)
        except Exception:
            self._table = self._db.open_table(table_name)

    def insert(self, record: VectorRecord) -> None:
        with self._lock:
            import pyarrow as pa
            data = pa.table({
                "id": [record.id],
                "vector": [record.vector],
                "text": [record.text],
                "metadata_json": [json.dumps(record.metadata, ensure_ascii=False)],
                "created_at": [record.created_at],
            })
            self._table.merge_insert("id").when_matched_update_all().execute(data)

    def insert_batch(self, records: List[VectorRecord]) -> None:
        if not records:
            return
        with self._lock:
            import pyarrow as pa
            data = pa.table({
                "id": [r.id for r in records],
                "vector": [r.vector for r in records],
                "text": [r.text for r in records],
                "metadata_json": [json.dumps(r.metadata, ensure_ascii=False) for r in records],
                "created_at": [r.created_at for r in records],
            })
            self._table.merge_insert("id").when_matched_update_all().execute(data)

    def search(self, query: List[float], top_k: int = 10) -> List[SearchResult]:
        try:
            results = self._table.search(query).limit(top_k).to_list()
            search_results: List[SearchResult] = []
            for r in results:
                meta: Dict[str, Any] = {}
                try:
                    meta = json.loads(r.get("metadata_json", "{}"))
                except (json.JSONDecodeError, TypeError):
                    pass
                search_results.append(SearchResult(
                    id=r.get("id", ""),
                    score=r.get("_distance", 0),
                    vector=r.get("vector", []),
                    metadata=meta,
                    text=r.get("text", ""),
                ))
            return search_results
        except Exception as exc:
            logger.warning("LanceDB search failed: %s", exc)
            return []

    def delete(self, id: str) -> bool:
        try:
            self._table.delete(f"id = '{id}'")
            return True
        except Exception:
            return False

    def delete_by_filter(self, key: str, value: Any) -> int:
        count = 0
        try:
            all_data = self._table.to_list()
            ids_to_delete: List[str] = []
            for r in all_data:
                try:
                    meta = json.loads(r.get("metadata_json", "{}"))
                    if key in meta and meta[key] == value:
                        ids_to_delete.append(r["id"])
                except (json.JSONDecodeError, TypeError):
                    pass
            for vid in ids_to_delete:
                self._table.delete(f"id = '{vid}'")
                count += 1
        except Exception as exc:
            logger.warning("LanceDB filter delete failed: %s", exc)
        return count

    def get(self, id: str) -> Optional[VectorRecord]:
        try:
            results = self._table.search().where(f"id = '{id}'").limit(1).to_list()
            if not results:
                return None
            r = results[0]
            meta: Dict[str, Any] = {}
            try:
                meta = json.loads(r.get("metadata_json", "{}"))
            except (json.JSONDecodeError, TypeError):
                pass
            return VectorRecord(
                id=r.get("id", ""),
                vector=r.get("vector", []),
                text=r.get("text", ""),
                metadata=meta,
                created_at=r.get("created_at", time.time()),
            )
        except Exception:
            return None

    def count(self) -> int:
        try:
            return len(self._table.to_list())
        except Exception:
            return 0

    def clear(self) -> None:
        try:
            all_data = self._table.to_list()
            for r in all_data:
                self._table.delete(f"id = '{r['id']}'")
        except Exception as exc:
            logger.warning("LanceDB clear failed: %s", exc)

    def close(self) -> None:
        pass


class ChromaBackend(VectorBackend):
    def __init__(self, config: VectorDBConfig) -> None:
        self._config = config
        self._collection: Any = None
        self._client: Any = None
        self._lock = threading.Lock()

    def initialize(self, dimensions: int) -> None:
        try:
            import chromadb
        except ImportError:
            raise ImportError("chromadb not installed. pip install chromadb")
        path = self._config.path or "./memory_chromadb"
        self._client = chromadb.PersistentClient(path=path)
        collection_name = self._config.collection_name
        try:
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            try:
                self._client.delete_collection(collection_name)
            except Exception:
                pass
            self._collection = self._client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )

    def insert(self, record: VectorRecord) -> None:
        with self._lock:
            self._collection.add(
                ids=[record.id],
                embeddings=[record.vector],
                documents=[record.text],
                metadatas=[{
                    **_get_flat_meta(record.metadata),
                    "created_at": str(record.created_at),
                }],
            )

    def insert_batch(self, records: List[VectorRecord]) -> None:
        if not records:
            return
        with self._lock:
            self._collection.add(
                ids=[r.id for r in records],
                embeddings=[r.vector for r in records],
                documents=[r.text for r in records],
                metadatas=[{
                    **_get_flat_meta(r.metadata),
                    "created_at": str(r.created_at),
                } for r in records],
            )

    def search(self, query: List[float], top_k: int = 10) -> List[SearchResult]:
        try:
            results = self._collection.query(
                query_embeddings=[query],
                n_results=top_k,
            )
            search_results: List[SearchResult] = []
            ids = results.get("ids", [[]])[0]
            distances = results.get("distances", [[]])[0]
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            for i in range(len(ids)):
                meta: Dict[str, Any] = dict(metadatas[i]) if i < len(metadatas) and metadatas[i] else {}
                if "created_at" in meta:
                    try:
                        meta["created_at"] = float(meta["created_at"])
                    except (ValueError, TypeError):
                        pass
                search_results.append(SearchResult(
                    id=ids[i],
                    score=1.0 - distances[i] if i < len(distances) else 0.0,
                    vector=[],
                    metadata=meta,
                    text=documents[i] if i < len(documents) else "",
                ))
            return search_results
        except Exception as exc:
            logger.warning("Chroma search failed: %s", exc)
            return []

    def delete(self, id: str) -> bool:
        try:
            self._collection.delete(ids=[id])
            return True
        except Exception:
            return False

    def delete_by_filter(self, key: str, value: Any) -> int:
        try:
            all_data = self._collection.get()
            ids_to_delete: List[str] = []
            for i, mid in enumerate(all_data.get("metadatas", [])):
                if mid and mid.get(key) == value:
                    ids_to_delete.append(all_data["ids"][i])
            if ids_to_delete:
                self._collection.delete(ids=ids_to_delete)
            return len(ids_to_delete)
        except Exception as exc:
            logger.warning("Chroma filter delete failed: %s", exc)
            return 0

    def get(self, id: str) -> Optional[VectorRecord]:
        try:
            results = self._collection.get(ids=[id])
            if not results or not results["ids"]:
                return None
            meta: Dict[str, Any] = {}
            if results["metadatas"] and results["metadatas"][0]:
                meta = dict(results["metadatas"][0])
            if "created_at" in meta:
                try:
                    meta["created_at"] = float(meta["created_at"])
                except (ValueError, TypeError):
                    pass
            return VectorRecord(
                id=results["ids"][0],
                vector=[],
                text=results["documents"][0] if results.get("documents") else "",
                metadata=meta,
                created_at=meta.get("created_at", time.time()),
            )
        except Exception:
            return None

    def count(self) -> int:
        try:
            return self._collection.count()
        except Exception:
            return 0

    def clear(self) -> None:
        try:
            all_data = self._collection.get()
            if all_data and all_data["ids"]:
                self._collection.delete(ids=all_data["ids"])
        except Exception as exc:
            logger.warning("Chroma clear failed: %s", exc)

    def close(self) -> None:
        pass


class QdrantBackend(VectorBackend):
    def __init__(self, config: VectorDBConfig) -> None:
        self._config = config
        self._client: Any = None
        self._lock = threading.Lock()

    def initialize(self, dimensions: int) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models
            self._models = models
        except ImportError:
            raise ImportError("qdrant-client not installed. pip install qdrant-client")
        path = self._config.path or "./memory_qdrant"
        self._client = QdrantClient(path=path)
        collection_name = self._config.collection_name
        collections = self._client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        if not exists:
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=dimensions,
                    distance=models.Distance.COSINE,
                ),
            )

    def insert(self, record: VectorRecord) -> None:
        with self._lock:
            self._client.upsert(
                collection_name=self._config.collection_name,
                points=[self._models.PointStruct(
                    id=record.id,
                    vector=record.vector,
                    payload={
                        "text": record.text,
                        "metadata": json.dumps(record.metadata, ensure_ascii=False),
                        "created_at": record.created_at,
                    },
                )],
            )

    def insert_batch(self, records: List[VectorRecord]) -> None:
        if not records:
            return
        with self._lock:
            self._client.upsert(
                collection_name=self._config.collection_name,
                points=[self._models.PointStruct(
                    id=r.id,
                    vector=r.vector,
                    payload={
                        "text": r.text,
                        "metadata": json.dumps(r.metadata, ensure_ascii=False),
                        "created_at": r.created_at,
                    },
                ) for r in records],
            )

    def search(self, query: List[float], top_k: int = 10) -> List[SearchResult]:
        try:
            results = self._client.search(
                collection_name=self._config.collection_name,
                query_vector=query,
                limit=top_k,
            )
            search_results: List[SearchResult] = []
            for r in results:
                meta: Dict[str, Any] = {}
                try:
                    payload_meta = r.payload.get("metadata", "{}")
                    if isinstance(payload_meta, str):
                        meta = json.loads(payload_meta)
                    elif isinstance(payload_meta, dict):
                        meta = payload_meta
                except (json.JSONDecodeError, TypeError):
                    pass
                search_results.append(SearchResult(
                    id=str(r.id),
                    score=r.score,
                    vector=r.vector if hasattr(r, "vector") else [],
                    metadata=meta,
                    text=r.payload.get("text", ""),
                ))
            return search_results
        except Exception as exc:
            logger.warning("Qdrant search failed: %s", exc)
            return []

    def delete(self, id: str) -> bool:
        try:
            self._client.delete(
                collection_name=self._config.collection_name,
                points_selector=self._models.FilterSelector(
                    filter=self._models.Filter(
                        must=[self._models.FieldCondition(
                            key="id",
                            match=self._models.MatchValue(value=id),
                        )],
                    ),
                ),
            )
            return True
        except Exception:
            return False

    def delete_by_filter(self, key: str, value: Any) -> int:
        try:
            results = self._client.scroll(
                collection_name=self._config.collection_name,
                limit=10000,
            )[0]
            ids_to_delete: List[str] = []
            for r in results:
                try:
                    payload_meta_str = r.payload.get("metadata", "{}")
                    if isinstance(payload_meta_str, str):
                        payload_meta = json.loads(payload_meta_str)
                    elif isinstance(payload_meta_str, dict):
                        payload_meta = payload_meta_str
                    else:
                        payload_meta = {}
                    if key in payload_meta and payload_meta[key] == value:
                        ids_to_delete.append(str(r.id))
                except (json.JSONDecodeError, TypeError):
                    pass
            for vid in ids_to_delete:
                self._client.delete(
                    collection_name=self._config.collection_name,
                    points_selector=self._models.PointIdsList(points=[vid]),
                )
            return len(ids_to_delete)
        except Exception as exc:
            logger.warning("Qdrant filter delete failed: %s", exc)
            return 0

    def get(self, id: str) -> Optional[VectorRecord]:
        try:
            results = self._client.retrieve(
                collection_name=self._config.collection_name,
                ids=[id],
            )
            if not results:
                return None
            r = results[0]
            meta: Dict[str, Any] = {}
            try:
                payload_meta = r.payload.get("metadata", "{}")
                if isinstance(payload_meta, str):
                    meta = json.loads(payload_meta)
                elif isinstance(payload_meta, dict):
                    meta = payload_meta
            except (json.JSONDecodeError, TypeError):
                pass
            return VectorRecord(
                id=str(r.id),
                vector=r.vector or [],
                text=r.payload.get("text", ""),
                metadata=meta,
                created_at=r.payload.get("created_at", time.time()),
            )
        except Exception:
            return None

    def count(self) -> int:
        try:
            result = self._client.count(collection_name=self._config.collection_name)
            return result.count
        except Exception:
            return 0

    def clear(self) -> None:
        try:
            self._client.delete(
                collection_name=self._config.collection_name,
                points_selector=self._models.FilterSelector(
                    filter=self._models.Filter(),
                ),
            )
        except Exception as exc:
            logger.warning("Qdrant clear failed: %s", exc)

    def close(self) -> None:
        pass


class FAISSBackend(VectorBackend):
    def __init__(self, config: VectorDBConfig) -> None:
        self._config = config
        self._index: Any = None
        self._records: Dict[str, VectorRecord] = {}
        self._id_to_idx: Dict[str, int] = {}
        self._idx_to_id: Dict[int, str] = {}
        self._next_idx: int = 0
        self._dimensions: int = 0
        self._lock = threading.Lock()

    def initialize(self, dimensions: int) -> None:
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss not installed. pip install faiss-cpu")
        self._dimensions = dimensions
        if self._config.metric == "cosine":
            self._index = faiss.IndexFlatIP(dimensions)
        else:
            self._index = faiss.IndexFlatL2(dimensions)

    def insert(self, record: VectorRecord) -> None:
        with self._lock:
            import faiss
            import numpy as np
            vec = np.array([record.vector], dtype=np.float32)
            if self._config.metric == "cosine":
                faiss.normalize_L2(vec)
            idx = self._next_idx
            self._index.add(vec)
            self._records[record.id] = record
            self._id_to_idx[record.id] = idx
            self._idx_to_id[idx] = record.id
            self._next_idx += 1

    def insert_batch(self, records: List[VectorRecord]) -> None:
        if not records:
            return
        with self._lock:
            import faiss
            import numpy as np
            vecs = np.array([r.vector for r in records], dtype=np.float32)
            if self._config.metric == "cosine":
                faiss.normalize_L2(vecs)
            start_idx = self._next_idx
            self._index.add(vecs)
            for i, record in enumerate(records):
                idx = start_idx + i
                self._records[record.id] = record
                self._id_to_idx[record.id] = idx
                self._idx_to_id[idx] = record.id
            self._next_idx += len(records)

    def search(self, query: List[float], top_k: int = 10) -> List[SearchResult]:
        with self._lock:
            if self._index.ntotal == 0:
                return []
            import faiss
            import numpy as np
            vec = np.array([query], dtype=np.float32)
            if self._config.metric == "cosine":
                faiss.normalize_L2(vec)
            k = min(top_k, self._index.ntotal)
            distances, indices = self._index.search(vec, k)
            results: List[SearchResult] = []
            for i in range(k):
                idx = int(indices[0][i])
                if idx < 0:
                    continue
                rid = self._idx_to_id.get(idx)
                if not rid or rid not in self._records:
                    continue
                record = self._records[rid]
                score = float(distances[0][i])
                results.append(SearchResult(
                    id=rid,
                    score=score,
                    vector=record.vector,
                    metadata=record.metadata,
                    text=record.text,
                ))
            return results

    def delete(self, id: str) -> bool:
        with self._lock:
            if id not in self._records:
                return False
            del self._records[id]
            idx = self._id_to_idx.pop(id, None)
            if idx is not None:
                self._idx_to_id.pop(idx, None)
            return True

    def delete_by_filter(self, key: str, value: Any) -> int:
        with self._lock:
            ids_to_delete = [
                rid for rid, rec in self._records.items()
                if key in rec.metadata and rec.metadata[key] == value
            ]
            for rid in ids_to_delete:
                idx = self._id_to_idx.pop(rid, None)
                if idx is not None:
                    self._idx_to_id.pop(idx, None)
                self._records.pop(rid, None)
            return len(ids_to_delete)

    def get(self, id: str) -> Optional[VectorRecord]:
        with self._lock:
            return self._records.get(id)

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._id_to_idx.clear()
            self._idx_to_id.clear()
            self._next_idx = 0
            self.initialize(self._dimensions)

    def close(self) -> None:
        pass


_BACKEND_REGISTRY: Dict[VectorDBType, type] = {
    VectorDBType.SQLITE: SQLiteVecBackend,
    VectorDBType.LANCEDB: LanceDBBackend,
    VectorDBType.CHROMA: ChromaBackend,
    VectorDBType.QDRANT: QdrantBackend,
    VectorDBType.FAISS: FAISSBackend,
}


class VectorDatabase:
    def __init__(self, config: Optional[VectorDBConfig] = None) -> None:
        self._config = config or VectorDBConfig()
        self._backend: Optional[VectorBackend] = None
        self._lock = threading.RLock()

    def initialize(self) -> None:
        backend_cls = _BACKEND_REGISTRY.get(self._config.backend)
        if not backend_cls:
            raise ValueError(f"Unsupported vector DB backend: {self._config.backend}")
        self._backend = backend_cls(self._config)
        self._backend.initialize(self._config.dimensions)
        logger.info("Vector database initialized: %s/%s", self._config.backend.value, self._config.collection_name)

    def switch_backend(self, backend: VectorDBType, config: Optional[VectorDBConfig] = None) -> None:
        if self._backend:
            self._backend.close()
        if config:
            self._config = config
        else:
            self._config.backend = backend
        self._backend = None
        self.initialize()
        logger.info("Switched vector DB backend to %s", backend.value)

    def insert(self, id: str, vector: List[float], text: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
        self._require_backend()
        record = VectorRecord(id=id, vector=vector, text=text, metadata=metadata or {})
        self._backend.insert(record)

    def insert_batch(self, records: List[VectorRecord]) -> None:
        self._require_backend()
        if records:
            self._backend.insert_batch(records)

    def search(self, query: List[float], top_k: int = 10) -> List[SearchResult]:
        self._require_backend()
        return self._backend.search(query, top_k)

    def delete(self, id: str) -> bool:
        self._require_backend()
        return self._backend.delete(id)

    def delete_by_filter(self, key: str, value: Any) -> int:
        self._require_backend()
        return self._backend.delete_by_filter(key, value)

    def get(self, id: str) -> Optional[VectorRecord]:
        self._require_backend()
        return self._backend.get(id)

    def count(self) -> int:
        self._require_backend()
        return self._backend.count()

    def clear(self) -> None:
        self._require_backend()
        self._backend.clear()

    def close(self) -> None:
        if self._backend:
            self._backend.close()

    def _require_backend(self) -> None:
        if self._backend is None:
            raise RuntimeError("VectorDatabase not initialized. Call initialize() first.")


def _get_flat_meta(meta: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    flat: Dict[str, Any] = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)):
            flat[f"{prefix}{k}"] = v
        elif isinstance(v, dict):
            flat.update(_get_flat_meta(v, f"{prefix}{k}."))
        else:
            flat[f"{prefix}{k}"] = str(v)
    return flat