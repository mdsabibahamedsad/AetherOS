"""Knowledge Center — central document and collection manager."""

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
    KnowledgeDocument, KnowledgeCollection, DocumentChunk,
    Annotation, SourceType, DocumentStatus, CollectionVisibility,
    BUILTIN_COLLECTIONS, COLLECTION_TEMPLATES, SUPPORTED_EXTENSIONS,
)

logger = logging.getLogger(__name__)


class KnowledgeCenter:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    # --- Collections ---
    def create_collection(self, name: str, description: str = "",
                           icon: str = "folder", color: str = "#6366f1",
                           parent_id: str = None,
                           template: str = None) -> KnowledgeCollection:
        if template and template in COLLECTION_TEMPLATES:
            t = COLLECTION_TEMPLATES[template]
            c = KnowledgeCollection(
                id=str(uuid.uuid4()), name=t.name, description=t.description,
                icon=t.icon, color=t.color)
        else:
            c = KnowledgeCollection(
                id=str(uuid.uuid4()), name=name, description=description,
                icon=icon, color=color, parent_id=parent_id)
        self.store.save_collection(c)
        logger.info("Created collection: %s (%s)", c.name, c.id)
        return c

    def get_collection(self, cid: str) -> Optional[KnowledgeCollection]:
        return self.store.get_collection(cid)

    def list_collections(self) -> list[KnowledgeCollection]:
        all_c = self.store.list_collections()
        builtin_ids = {b.id for b in BUILTIN_COLLECTIONS}
        builtins = [c for c in all_c if c.id in builtin_ids]
        user = [c for c in all_c if c.id not in builtin_ids]
        return builtins + user

    def delete_collection(self, cid: str):
        self.store.delete_collection(cid)
        logger.info("Deleted collection: %s", cid)

    # --- Documents ---
    def add_document(self, title: str, source_type: SourceType,
                      source_path: str, collection_id: str = "documents",
                      content_type: str = "", language: str = "",
                      tags: list[str] = None,
                      metadata: dict = None) -> KnowledgeDocument:
        did = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        d = KnowledgeDocument(
            id=did, title=title, source_type=source_type,
            source_path=source_path, collection_id=collection_id,
            status=DocumentStatus.PENDING, content_type=content_type,
            language=language, tags=tags or [],
            metadata=metadata or {},
            created_at=now, updated_at=now)
        self.store.save_document(d)
        self.store.update_collection_stats(collection_id)
        return d

    def get_document(self, did: str) -> Optional[KnowledgeDocument]:
        return self.store.get_document(did)

    def list_documents(self, collection_id: str = None,
                        source_type: str = None,
                        status: str = None,
                        limit: int = 100) -> list[KnowledgeDocument]:
        return self.store.list_documents(collection_id, source_type, status, limit)

    def search_documents(self, query: str) -> list[KnowledgeDocument]:
        return self.store.search_documents(query)

    def delete_document(self, did: str):
        doc = self.store.get_document(did)
        if doc:
            self.store.delete_document(did)
            self.store.update_collection_stats(doc.collection_id)

    def trash_document(self, did: str):
        now = datetime.utcnow().isoformat() + "Z"
        doc = self.store.get_document(did)
        if doc:
            self.store._conn.execute(
                "UPDATE documents SET collection_id='trash', updated_at=? WHERE id=?",
                (now, did))
            self.store._conn.commit()
            self.store.update_collection_stats(doc.collection_id)
            self.store.update_collection_stats("trash")

    def get_total_stats(self) -> dict:
        return self.store.get_stats()

    # --- Annotations ---
    def add_annotation(self, document_id: str, annotation_type: str,
                        content: str = "", color: str = "",
                        position_start: int = 0, position_end: int = 0,
                        page: int = 0) -> Annotation:
        a = Annotation(
            id=str(uuid.uuid4()), document_id=document_id,
            annotation_type=annotation_type, content=content,
            color=color, position_start=position_start,
            position_end=position_end, page=page)
        self.store.save_annotation(a)
        return a

    def get_annotations(self, document_id: str) -> list[Annotation]:
        return self.store.get_annotations(document_id)

    def delete_annotation(self, aid: str):
        self.store.delete_annotation(aid)

    # --- Import ---
    def import_file(self, file_path: str, collection_id: str = "documents",
                     tags: list[str] = None) -> Optional[KnowledgeDocument]:
        path = Path(file_path)
        if not path.exists():
            logger.error("File not found: %s", file_path)
            return None
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            logger.warning("Unsupported extension: %s", ext)
            return None
        source_type = SUPPORTED_EXTENSIONS[ext]
        with open(path, "rb") as f:
            content = f.read()
        checksum = hashlib.sha256(content).hexdigest()
        title = path.stem
        doc = self.add_document(
            title=title, source_type=source_type,
            source_path=str(path.absolute()),
            collection_id=collection_id,
            content_type=f"text/{ext[1:]}" if ext != ".pdf" else "application/pdf",
            tags=tags or [],
            metadata={"checksum": checksum, "size": len(content)})
        return doc

    def import_folder(self, folder_path: str,
                       collection_id: str = "documents",
                       recursive: bool = True) -> list[KnowledgeDocument]:
        path = Path(folder_path)
        if not path.is_dir():
            logger.error("Folder not found: %s", folder_path)
            return []
        docs = []
        pattern = "**/*" if recursive else "*"
        for f in path.glob(pattern):
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                doc = self.import_file(str(f), collection_id)
                if doc:
                    docs.append(doc)
        return docs

    def get_source_type_from_extension(self, ext: str) -> Optional[SourceType]:
        return SUPPORTED_EXTENSIONS.get(ext.lower())
