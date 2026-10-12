"""Knowledge sharing — share, export, import collections."""

from __future__ import annotations

import json
import logging
import zipfile
import io
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aetheros_knowledge.store import KnowledgeStore
from aetheros_knowledge.models import KnowledgeCollection, CollectionVisibility

logger = logging.getLogger(__name__)


class KnowledgeSharing:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    def share_collection(self, collection_id: str,
                          visibility: CollectionVisibility) -> bool:
        col = self.store.get_collection(collection_id)
        if not col:
            return False
        col.visibility = visibility
        col.updated_at = datetime.utcnow().isoformat() + "Z"
        self.store.save_collection(col)
        return True

    def export_collection(self, collection_id: str,
                           output_path: str = None) -> Optional[str]:
        col = self.store.get_collection(collection_id)
        if not col:
            return None
        docs = self.store.list_documents(collection_id)
        data = {
            "collection": {
                "name": col.name, "description": col.description,
                "icon": col.icon, "color": col.color, "tags": col.tags,
            },
            "documents": [],
        }
        for doc in docs:
            chunks = self.store.get_chunks(doc.id)
            data["documents"].append({
                "title": doc.title, "source_type": doc.source_type.value,
                "source_path": doc.source_path, "language": doc.language,
                "tags": doc.tags, "metadata": doc.metadata,
                "content": chunks[0].content if chunks else "",
            })
        json_str = json.dumps(data, indent=2, default=str)
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)
            return output_path
        return json_str

    def import_collection(self, input_path: str = None,
                           json_str: str = None,
                           target_collection_id: str = None) -> Optional[KnowledgeCollection]:
        if input_path:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif json_str:
            data = json.loads(json_str)
        else:
            return None
        col_data = data.get("collection", {})
        if target_collection_id:
            col = self.store.get_collection(target_collection_id)
            if not col:
                return None
        else:
            from aetheros_knowledge.models import KnowledgeCollection
            import uuid
            col = KnowledgeCollection(
                id=str(uuid.uuid4()), name=col_data.get("name", "Imported"),
                description=col_data.get("description", ""),
                icon=col_data.get("icon", "folder"),
                color=col_data.get("color", "#6366f1"),
                tags=col_data.get("tags", []))
            self.store.save_collection(col)
        from aetheros_knowledge.models import SourceType, KnowledgeDocument
        import uuid
        for doc_data in data.get("documents", []):
            try:
                st = SourceType(doc_data.get("source_type", "txt"))
            except ValueError:
                st = SourceType.TXT
            doc = KnowledgeDocument(
                id=str(uuid.uuid4()), title=doc_data.get("title", "Untitled"),
                source_type=st, source_path=doc_data.get("source_path", ""),
                collection_id=col.id,
                language=doc_data.get("language", "en"),
                tags=doc_data.get("tags", []),
                metadata=doc_data.get("metadata", {}))
            self.store.save_document(doc)
        self.store.update_collection_stats(col.id)
        return col

    def export_bundle(self, collection_ids: list[str],
                       output_path: str) -> str:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for cid in collection_ids:
                data = self.export_collection(cid)
                if data:
                    col = self.store.get_collection(cid)
                    zf.writestr(f"{col.name}.json" if col else f"{cid}.json",
                                 data)
        return output_path

    def import_bundle(self, input_path: str) -> list[KnowledgeCollection]:
        imported = []
        with zipfile.ZipFile(input_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".json"):
                    data = zf.read(name).decode("utf-8")
                    col = self.import_collection(json_str=data)
                    if col:
                        imported.append(col)
        return imported

    def list_shared(self) -> list[KnowledgeCollection]:
        all_cols = self.store.list_collections()
        return [c for c in all_cols if c.visibility != CollectionVisibility.PRIVATE]
