"""Vector database backends — Chroma, FAISS, Qdrant, Milvus, SQLite-Vec."""

from __future__ import annotations

from aetheros_knowledge.vectordb.base import VectorDB, SearchResult
from aetheros_knowledge.vectordb.sqlite_vec import SQLiteVectorDB

VECTORDB_MAP: dict[str, type[VectorDB]] = {}

try:
    from aetheros_knowledge.vectordb.chroma import ChromaDB
    VECTORDB_MAP["chroma"] = ChromaDB
except ImportError:
    pass

try:
    from aetheros_knowledge.vectordb.faiss import FAISSDB
    VECTORDB_MAP["faiss"] = FAISSDB
except ImportError:
    pass

try:
    from aetheros_knowledge.vectordb.qdrant import QdrantDB
    VECTORDB_MAP["qdrant"] = QdrantDB
except ImportError:
    pass

try:
    from aetheros_knowledge.vectordb.milvus import MilvusDB
    VECTORDB_MAP["milvus"] = MilvusDB
except ImportError:
    pass

VECTORDB_MAP["sqlite"] = SQLiteVectorDB


def get_vectordb(name: str = "sqlite", **kwargs) -> VectorDB:
    cls = VECTORDB_MAP.get(name)
    if cls is None:
        cls = SQLiteVectorDB
    return cls(**kwargs)


def auto_detect_backend() -> str:
    for name in ["chroma", "faiss", "qdrant", "milvus"]:
        if name in VECTORDB_MAP:
            return name
    return "sqlite"


__all__ = ["VectorDB", "SearchResult", "get_vectordb", "auto_detect_backend",
           "VECTORDB_MAP"]
