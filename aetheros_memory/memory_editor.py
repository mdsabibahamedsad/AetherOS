"""Memory Editor — view, edit, delete, merge, split, pin, archive, search, export, import memories."""

from __future__ import annotations

import copy
import csv
import enum
import io
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_memory.memory_manager import MemoryManager, MemoryCategory, MemoryRecord

logger = logging.getLogger("aetheros_memory.editor")


class EditOperation(str, enum.Enum):
    VIEW = "view"
    EDIT = "edit"
    DELETE = "delete"
    MERGE = "merge"
    SPLIT = "split"
    PIN = "pin"
    UNPIN = "unpin"
    ARCHIVE = "archive"
    UNARCHIVE = "unarchive"
    TAG = "tag"
    RENAME = "rename"
    CHANGE_CATEGORY = "change_category"
    CHANGE_PERMISSIONS = "change_permissions"


@dataclass
class EditResult:
    success: bool = False
    operation: EditOperation = EditOperation.VIEW
    memory_id: str = ""
    message: str = ""
    record: Optional[MemoryRecord] = None
    error: Optional[str] = None


@dataclass
class MergeResult:
    merged_id: str = ""
    source_ids: List[str] = field(default_factory=list)
    record: Optional[MemoryRecord] = None
    conflicts: List[Dict[str, Any]] = field(default_factory=list)


_EDIT_HISTORY: Dict[str, List[Dict[str, Any]]] = {}


class MemoryEditor:
    def __init__(self, memory_manager: Optional[MemoryManager] = None) -> None:
        self._manager = memory_manager
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # View
    # ------------------------------------------------------------------

    def view(self, memory_id: str) -> Optional[MemoryRecord]:
        return self._manager.retrieve(memory_id)

    # ------------------------------------------------------------------
    # Edit
    # ------------------------------------------------------------------

    def edit(
        self,
        memory_id: str,
        content: Optional[str] = None,
        key: Optional[str] = None,
        tags: Optional[List[str]] = None,
        importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EditResult:
        with self._lock:
            record = self._manager.retrieve(memory_id)
            if not record:
                return EditResult(
                    success=False, operation=EditOperation.EDIT,
                    memory_id=memory_id, error="Memory not found",
                )
            old_state = record.to_dict()
            if content is not None:
                record.content = content
            if key is not None:
                record.key = key
            if tags is not None:
                record.tags = tags
            if importance is not None:
                record.importance = importance
            if metadata is not None:
                record.metadata.update(metadata)
            record.updated_at = time.time()
            self._append_history(memory_id, EditOperation.EDIT, old_state, record.to_dict())
            return EditResult(
                success=True, operation=EditOperation.EDIT,
                memory_id=memory_id, record=record, message="Memory updated",
            )

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, memory_id: str) -> EditResult:
        success = self._manager.delete(memory_id)
        if success:
            return EditResult(
                success=True, operation=EditOperation.DELETE,
                memory_id=memory_id, message="Memory deleted",
            )
        return EditResult(
            success=False, operation=EditOperation.DELETE,
            memory_id=memory_id, error="Memory not found",
        )

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    def merge(
        self,
        memory_ids: List[str],
        strategy: str = "keep_longest",
    ) -> MergeResult:
        if len(memory_ids) < 2:
            return MergeResult(conflicts=[{"error": "At least two memory IDs required"}])

        with self._lock:
            records: List[MemoryRecord] = []
            for mid in memory_ids:
                r = self._manager.retrieve(mid)
                if r:
                    records.append(r)

            if len(records) < 2:
                return MergeResult(conflicts=[{"error": "Could not retrieve enough memories"}])

            if strategy == "keep_longest":
                records.sort(key=lambda x: len(x.content), reverse=True)
            elif strategy == "keep_most_recent":
                records.sort(key=lambda x: x.updated_at, reverse=True)
            elif strategy == "keep_most_important":
                records.sort(key=lambda x: x.importance, reverse=True)
            elif strategy == "concatenate":
                pass
            else:
                return MergeResult(conflicts=[{"error": f"Unknown strategy: {strategy}"}])

            primary = records[0]
            sources = records[1:]

            if strategy == "concatenate":
                separator = "\n---\n"
                combined_content = separator.join(r.content for r in records)
            else:
                combined_content = primary.content

            merged_tags: List[str] = []
            seen_tags: set = set()
            for r in records:
                for t in r.tags:
                    if t not in seen_tags:
                        merged_tags.append(t)
                        seen_tags.add(t)

            merged_metadata: Dict[str, Any] = {}
            for r in records:
                merged_metadata.update(r.metadata)

            merged_importance = max(r.importance for r in records)
            merged = self._manager.store(
                content=combined_content,
                category=primary.category,
                key=f"merged_{uuid.uuid4().hex[:8]}",
                tags=merged_tags,
                importance=merged_importance,
                source=primary.source,
                workspace_id=primary.workspace_id,
                project_id=primary.project_id,
                permissions=primary.permissions,
                metadata=merged_metadata,
            )

            for r in records:
                self._manager.delete(r.id)

            return MergeResult(
                merged_id=merged.id,
                source_ids=memory_ids,
                record=merged,
                conflicts=[],
            )

    # ------------------------------------------------------------------
    # Split
    # ------------------------------------------------------------------

    def split(
        self,
        memory_id: str,
        split_points: List[int],
    ) -> List[MemoryRecord]:
        if not split_points:
            return []

        with self._lock:
            record = self._manager.retrieve(memory_id)
            if not record:
                return []

            content = record.content
            sorted_points = sorted(split_points)
            if sorted_points[0] < 0 or sorted_points[-1] >= len(content):
                return []

            segments: List[str] = []
            prev = 0
            for p in sorted_points:
                segments.append(content[prev:p])
                prev = p
            segments.append(content[prev:])

            parts: List[MemoryRecord] = []
            for i, seg in enumerate(segments):
                part = self._manager.store(
                    content=seg,
                    category=record.category,
                    tags=list(record.tags),
                    importance=record.importance,
                    source=record.source,
                    workspace_id=record.workspace_id,
                    project_id=record.project_id,
                    metadata={**record.metadata, "split_parent": memory_id, "segment_index": i},
                )
                parts.append(part)

            self._manager.delete(memory_id)
            return parts

    # ------------------------------------------------------------------
    # Pin / Unpin
    # ------------------------------------------------------------------

    def pin(self, memory_id: str) -> EditResult:
        success = self._manager.pin(memory_id)
        return EditResult(
            success=success, operation=EditOperation.PIN,
            memory_id=memory_id,
            message="Memory pinned" if success else "",
            error=None if success else "Memory not found",
        )

    def unpin(self, memory_id: str) -> EditResult:
        success = self._manager.unpin(memory_id)
        return EditResult(
            success=success, operation=EditOperation.UNPIN,
            memory_id=memory_id,
            message="Memory unpinned" if success else "",
            error=None if success else "Memory not found",
        )

    # ------------------------------------------------------------------
    # Archive / Unarchive
    # ------------------------------------------------------------------

    def archive(self, memory_id: str) -> EditResult:
        success = self._manager.archive(memory_id)
        return EditResult(
            success=success, operation=EditOperation.ARCHIVE,
            memory_id=memory_id,
            message="Memory archived" if success else "",
            error=None if success else "Memory not found or already archived",
        )

    def unarchive(self, memory_id: str) -> EditResult:
        success = self._manager.unarchive(memory_id)
        return EditResult(
            success=success, operation=EditOperation.UNARCHIVE,
            memory_id=memory_id,
            message="Memory unarchived" if success else "",
            error=None if success else "Memory not found or not archived",
        )

    # ------------------------------------------------------------------
    # Tag
    # ------------------------------------------------------------------

    def add_tag(self, memory_id: str, tag: str) -> EditResult:
        with self._lock:
            record = self._manager.retrieve(memory_id)
            if not record:
                return EditResult(
                    success=False, operation=EditOperation.TAG,
                    memory_id=memory_id, error="Memory not found",
                )
            if tag not in record.tags:
                record.tags.append(tag)
                record.updated_at = time.time()
            return EditResult(
                success=True, operation=EditOperation.TAG,
                memory_id=memory_id, record=record, message=f"Tag '{tag}' added",
            )

    def remove_tag(self, memory_id: str, tag: str) -> EditResult:
        with self._lock:
            record = self._manager.retrieve(memory_id)
            if not record:
                return EditResult(
                    success=False, operation=EditOperation.TAG,
                    memory_id=memory_id, error="Memory not found",
                )
            if tag in record.tags:
                record.tags.remove(tag)
                record.updated_at = time.time()
            return EditResult(
                success=True, operation=EditOperation.TAG,
                memory_id=memory_id, record=record, message=f"Tag '{tag}' removed",
            )

    # ------------------------------------------------------------------
    # Category / Permissions
    # ------------------------------------------------------------------

    def change_category(self, memory_id: str, category: MemoryCategory) -> EditResult:
        with self._lock:
            record = self._manager.retrieve(memory_id)
            if not record:
                return EditResult(
                    success=False, operation=EditOperation.CHANGE_CATEGORY,
                    memory_id=memory_id, error="Memory not found",
                )
            old = record.category
            record.category = category
            record.updated_at = time.time()
            return EditResult(
                success=True, operation=EditOperation.CHANGE_CATEGORY,
                memory_id=memory_id, record=record,
                message=f"Category changed from '{old.value}' to '{category.value}'",
            )

    def change_permissions(self, memory_id: str, permissions: str) -> EditResult:
        with self._lock:
            record = self._manager.retrieve(memory_id)
            if not record:
                return EditResult(
                    success=False, operation=EditOperation.CHANGE_PERMISSIONS,
                    memory_id=memory_id, error="Memory not found",
                )
            record.permissions = permissions
            record.updated_at = time.time()
            return EditResult(
                success=True, operation=EditOperation.CHANGE_PERMISSIONS,
                memory_id=memory_id, record=record,
                message=f"Permissions set to '{permissions}'",
            )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str = "",
        category: Optional[MemoryCategory] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[MemoryRecord]:
        return self._manager.search(query=query, category=category, tags=tags, limit=limit)

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_json(self, query: str = "", filepath: str = "") -> str:
        results = self._manager.search(query=query) if query else list(self._manager._memories.values())
        data = [r.to_dict() for r in results]
        payload = json.dumps(data, indent=2, ensure_ascii=False)
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(payload)
        return payload

    def export_csv(self, query: str = "", filepath: str = "") -> str:
        results = self._manager.search(query=query) if query else list(self._manager._memories.values())
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "category", "content", "summary", "key", "tags",
            "importance", "permissions", "source", "workspace_id",
            "project_id", "created_at", "updated_at", "accessed_at",
            "access_count", "archived", "pinned",
        ])
        for r in results:
            writer.writerow([
                r.id, r.category.value, r.content, r.summary, r.key,
                ",".join(r.tags), r.importance, r.permissions, r.source,
                r.workspace_id, r.project_id, r.created_at, r.updated_at,
                r.accessed_at, r.access_count, r.archived, r.pinned,
            ])
        payload = output.getvalue()
        if filepath:
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                f.write(payload)
        return payload

    def import_json(self, filepath: str) -> int:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for item in data:
            record = MemoryRecord.from_dict(item)
            self._manager.store(
                content=record.content,
                category=record.category,
                key=record.key,
                tags=record.tags,
                importance=record.importance,
                source=record.source,
                workspace_id=record.workspace_id,
                project_id=record.project_id,
                permissions=record.permissions,
                metadata=record.metadata,
            )
            count += 1
        return count

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, memory_id: str) -> List[Dict[str, Any]]:
        return list(_EDIT_HISTORY.get(memory_id, []))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append_history(
        self,
        memory_id: str,
        operation: EditOperation,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any],
    ) -> None:
        entry = {
            "timestamp": time.time(),
            "operation": operation.value,
            "old_state": old_state,
            "new_state": new_state,
        }
        if memory_id not in _EDIT_HISTORY:
            _EDIT_HISTORY[memory_id] = []
        _EDIT_HISTORY[memory_id].append(entry)
        if len(_EDIT_HISTORY[memory_id]) > 100:
            _EDIT_HISTORY[memory_id] = _EDIT_HISTORY[memory_id][-100:]
