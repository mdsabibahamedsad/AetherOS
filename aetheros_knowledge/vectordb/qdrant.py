"""Placeholder Qdrant backend."""
from aetheros_knowledge.vectordb.base import VectorDB, SearchResult
import logging; logger = logging.getLogger(__name__)

class QdrantDB(VectorDB):
    def __init__(self, path="./qdrant_db", collection="aetheros", dimension=384):
        self.path=path; self.collection=collection; self.dimension=dimension; self._client=None
    def _ensure(self):
        if self._client: return
        try:
            from qdrant_client import QdrantClient; from qdrant_client.models import VectorParams, Distance
            self._client = QdrantClient(path=self.path)
            self._client.recreate_collection(self.collection, vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE))
        except Exception as e: logger.warning("Qdrant unavailable: %s", e)
    def add(self, *a, **kw): pass
    def add_batch(self, ids, embeddings, contents, metadatas=None):
        self._ensure()
        if not self._client: return
        from qdrant_client.models import PointStruct
        pts = [PointStruct(id=i, vector=embeddings[i], payload={"content": contents[i], **(metadatas[i] if metadatas else {})}) for i in range(len(ids))]
        self._client.upsert(self.collection, points=pts)
    def search(self, embedding, top_k=10, filters=None):
        self._ensure()
        if not self._client: return []
        from qdrant_client.models import Filter as QFilter
        f = QFilter(**filters) if filters else None
        r = self._client.search(self.collection, query_vector=embedding, limit=top_k, query_filter=f)
        return [SearchResult(id=str(p.id), score=p.score, content=p.payload.get("content",""), metadata={k:v for k,v in p.payload.items() if k!="content"}) for p in r]
    def delete(self, chunk_id): self._client.delete(self.collection, points_selector=[chunk_id]) if self._client else None
    def delete_by_metadata(self, key, value): pass
    def count(self): return self._client.count(self.collection).count if self._client else 0
    def close(self): self._client=None
