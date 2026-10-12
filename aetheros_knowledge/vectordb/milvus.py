"""Placeholder Milvus backend."""
from aetheros_knowledge.vectordb.base import VectorDB, SearchResult
import logging; logger = logging.getLogger(__name__)

class MilvusDB(VectorDB):
    def __init__(self, host="localhost", port=19530, collection="aetheros", dimension=384):
        self.host=host; self.port=port; self.collection=collection; self.dimension=dimension; self._client=None
    def _ensure(self):
        if self._client: return
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
            connections.connect(host=self.host, port=self.port)
            self._client = Collection(self.collection)
        except Exception as e: logger.warning("Milvus unavailable: %s", e)
    def add(self, *a, **kw): pass
    def add_batch(self, ids, embeddings, contents, metadatas=None): pass
    def search(self, embedding, top_k=10, filters=None): return []
    def delete(self, chunk_id): pass
    def delete_by_metadata(self, key, value): pass
    def count(self): return 0
    def close(self): self._client=None
