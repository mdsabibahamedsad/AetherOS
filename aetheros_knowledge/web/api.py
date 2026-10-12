"""Web API — JSON endpoints for Knowledge OS frontend."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from aetheros_knowledge.store import KnowledgeStore
from aetheros_knowledge.center.manager import KnowledgeCenter
from aetheros_knowledge.memory.engine import MemoryEngine
from aetheros_knowledge.rag.studio import RAGStudio
from aetheros_knowledge.search.engine import SearchEngine
from aetheros_knowledge.sharing.share import KnowledgeSharing
from aetheros_knowledge.security.encryption import KnowledgeSecurity
from aetheros_knowledge.indexing.pipeline import IndexingPipeline
from aetheros_knowledge.indexing.embedders import get_embedder
from aetheros_knowledge.vectordb import get_vectordb, auto_detect_backend
from aetheros_knowledge.models import SourceType, DocumentStatus

logger = logging.getLogger(__name__)


class KnowledgeAPI:
    def __init__(self, store: KnowledgeStore = None):
        self.store = store or KnowledgeStore()
        self.center = KnowledgeCenter(self.store)
        self.memory = MemoryEngine(self.store)
        self.rag = RAGStudio(self.store)
        self.sharing = KnowledgeSharing(self.store)
        self.security = KnowledgeSecurity(self.store)
        self.search = SearchEngine(self.store)
        self.pipeline = IndexingPipeline(self.store)

    # --- Overview ---
    def get_overview(self) -> dict:
        return {
            "stats": self.store.get_stats(),
            "vector_backend": auto_detect_backend(),
            "memory": self.memory.get_stats(),
            "collections": len(self.center.list_collections()),
        }

    # --- Documents ---
    def list_documents(self, **kwargs) -> list[dict]:
        docs = self.center.list_documents(**kwargs)
        return [self._doc_to_dict(d) for d in docs]

    def get_document(self, did: str) -> Optional[dict]:
        doc = self.center.get_document(did)
        if not doc:
            return None
        result = self._doc_to_dict(doc)
        result["chunks"] = [{"id": c.id, "content": c.content[:200],
                              "chunk_index": c.chunk_index}
                             for c in self.store.get_chunks(did)]
        result["annotations"] = [
            {"id": a.id, "type": a.annotation_type, "content": a.content,
             "color": a.color}
            for a in self.center.get_annotations(did)]
        return result

    def delete_document(self, did: str) -> dict:
        self.center.delete_document(did)
        return {"success": True}

    def trash_document(self, did: str) -> dict:
        self.center.trash_document(did)
        return {"success": True}

    def search_documents(self, query: str) -> list[dict]:
        docs = self.center.search_documents(query)
        return [self._doc_to_dict(d) for d in docs]

    # --- Import ---
    def import_file(self, file_path: str, collection_id: str = "documents") -> dict:
        doc = self.center.import_file(file_path, collection_id)
        if doc:
            return {"success": True, "document": self._doc_to_dict(doc)}
        return {"success": False, "error": "Import failed"}

    def import_folder(self, folder_path: str,
                       collection_id: str = "documents") -> dict:
        docs = self.center.import_folder(folder_path, collection_id)
        return {"success": True, "count": len(docs),
                "documents": [self._doc_to_dict(d) for d in docs]}

    # --- Indexing ---
    def index_document(self, did: str) -> dict:
        doc = self.center.get_document(did)
        if not doc:
            return {"success": False, "error": "Document not found"}
        doc = self.pipeline.index_document(doc)
        return {"success": True, "status": doc.status.value}

    def index_all_pending(self) -> dict:
        results = self.pipeline.index_all_pending()
        return {"success": True, "indexed": len(results)}

    # --- Collections ---
    def list_collections(self) -> list[dict]:
        return [self._col_to_dict(c) for c in self.center.list_collections()]

    def create_collection(self, name: str, **kwargs) -> dict:
        col = self.center.create_collection(name, **kwargs)
        return {"success": True, "collection": self._col_to_dict(col)}

    def delete_collection(self, cid: str) -> dict:
        self.center.delete_collection(cid)
        return {"success": True}

    # --- Search ---
    def fulltext_search(self, query: str, **kwargs) -> list[dict]:
        return self.search.fulltext_search(query, **kwargs)

    def semantic_search(self, query: str, top_k: int = 10) -> list[dict]:
        results = self.search.semantic_search(query, top_k)
        return [{"id": r.id, "content": r.content[:300],
                 "score": r.score, "metadata": r.metadata}
                for r in results]

    def hybrid_search(self, query: str, top_k: int = 10,
                       collection_id: str = None) -> list[dict]:
        return self.search.hybrid_search(query, top_k, collection_id)

    # --- Memory ---
    def get_memory(self, memory_type: str = None) -> list[dict]:
        from aetheros_knowledge.models import MemoryType
        if memory_type:
            try:
                mt = MemoryType(memory_type)
                entries = self.store.list_memory(mt)
            except ValueError:
                return []
        else:
            entries = self.store.list_memory()
        return [{"key": e.key, "value": e.value, "type": e.memory_type.value,
                  "tags": e.tags, "importance": e.importance,
                  "created_at": e.created_at}
                for e in entries]

    def set_memory(self, key: str, value: Any,
                    memory_type: str = "personal") -> dict:
        from aetheros_knowledge.models import MemoryType
        try:
            mt = MemoryType(memory_type)
        except ValueError:
            mt = MemoryType.PERSONAL
        entry = self.memory._store_memory(mt, key, value)
        return {"success": True, "id": entry.id}

    def delete_memory(self, key: str, memory_type: str = None) -> dict:
        from aetheros_knowledge.models import MemoryType
        if memory_type:
            try:
                self.store.delete_memory(key, MemoryType(memory_type))
            except ValueError:
                pass
        else:
            self.store.delete_memory(key)
        return {"success": True}

    # --- RAG ---
    def list_pipelines(self) -> list[dict]:
        return [{"id": p.id, "name": p.name, "description": p.description,
                  "embedder": p.embedder, "vector_store": p.vector_store,
                  "chunk_size": p.chunk_size}
                for p in self.rag.list_pipelines()]

    def create_pipeline(self, **kwargs) -> dict:
        p = self.rag.create_pipeline(**kwargs)
        return {"success": True, "pipeline": {"id": p.id, "name": p.name}}

    def retrieve(self, pipeline_id: str, query: str) -> dict:
        p = self.rag.get_pipeline(pipeline_id)
        if not p:
            return {"success": False, "error": "Pipeline not found"}
        results = self.rag.retrieve(p, query)
        return {"success": True, "results": results}

    def evaluate(self, pipeline_id: str,
                  test_queries: list[list[str]]) -> dict:
        p = self.rag.get_pipeline(pipeline_id)
        if not p:
            return {"success": False, "error": "Pipeline not found"}
        queries = [(q[0], q[1]) for q in test_queries]
        metrics = self.rag.evaluate(p, queries)
        return {"success": True, "metrics": metrics}

    # --- Sharing ---
    def export_collection(self, cid: str) -> dict:
        data = self.sharing.export_collection(cid)
        if data:
            return {"success": True, "data": json.loads(data) if isinstance(data, str) and data.startswith("{") else data}
        return {"success": False, "error": "Collection not found"}

    def import_collection(self, data: dict,
                           target_collection_id: str = None) -> dict:
        col = self.sharing.import_collection(
            json_str=json.dumps(data), target_collection_id=target_collection_id)
        if col:
            return {"success": True, "collection_id": col.id}
        return {"success": False, "error": "Import failed"}

    # --- Security ---
    def get_permissions(self) -> list[dict]:
        return self.security.get_permissions()

    def set_permission(self, **kwargs) -> dict:
        self.security.set_permission(
            kwargs.get("resource_type", ""), kwargs.get("resource_id", ""),
            kwargs.get("user_id", ""), kwargs.get("permission", "read"))
        return {"success": True}

    # --- Util ---
    def get_config(self) -> dict:
        from aetheros_knowledge.vectordb import VECTORDB_MAP, auto_detect_backend
        from aetheros_knowledge.rag.studio import EMBEDDER_OPTIONS
        return {
            "vector_backends": list(VECTORDB_MAP.keys()),
            "auto_detected": auto_detect_backend(),
            "embedders": EMBEDDER_OPTIONS,
            "supported_extensions": list(SourceType),
        }

    @staticmethod
    def _doc_to_dict(doc) -> dict:
        return {
            "id": doc.id, "title": doc.title,
            "source_type": doc.source_type.value,
            "source_path": doc.source_path,
            "collection_id": doc.collection_id,
            "status": doc.status.value,
            "language": doc.language,
            "size_bytes": doc.size_bytes,
            "word_count": doc.word_count,
            "chunk_count": doc.chunk_count,
            "tags": doc.tags,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "indexed_at": doc.indexed_at,
        }

    @staticmethod
    def _col_to_dict(col) -> dict:
        return {
            "id": col.id, "name": col.name,
            "description": col.description,
            "icon": col.icon, "color": col.color,
            "parent_id": col.parent_id,
            "visibility": col.visibility.value,
            "document_count": col.document_count,
            "size_bytes": col.size_bytes,
        }
