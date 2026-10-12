"""Shared knowledge manager — vector DB, documents, collections, embeddings."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_cloud.models import SharedKnowledge, ShareLink, SharePermission, generate_id, now

logger = logging.getLogger(__name__)


class KnowledgeManager:
    """Manages shared knowledge across workspaces and teams.

    Integrates with existing Hermes knowledge store (aetheros_knowledge).
    """

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir:
            self._data_dir = data_dir
        else:
            from aetheros_constants import get_aetheros_home
            self._data_dir = get_aetheros_home() / "cloud" / "knowledge"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._items: Dict[str, SharedKnowledge] = {}
        self._share_links: Dict[str, ShareLink] = {}
        self._load()

    def share(
        self,
        entity_type: str,
        entity_id: str,
        workspace_id: str,
        name: str = "",
        description: str = "",
        created_by: str = "",
        tags: Optional[List[str]] = None,
    ) -> SharedKnowledge:
        item = SharedKnowledge(
            id=generate_id("know"),
            workspace_id=workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            name=name or entity_id,
            description=description,
            tags=tags or [],
            created_by=created_by,
            created_at=now(),
            updated_at=now(),
        )
        self._items[item.id] = item
        self._persist()
        logger.info("Shared %s/%s in workspace %s", entity_type, entity_id, workspace_id)
        return item

    def create_share_link(
        self,
        entity_type: str,
        entity_id: str,
        permission: SharePermission = SharePermission.READ,
        created_by: str = "",
        workspace_id: str = "",
        expires_in: Optional[int] = None,
    ) -> ShareLink:
        import uuid
        link = ShareLink(
            id=generate_id("link"),
            entity_type=entity_type,
            entity_id=entity_id,
            permission=permission,
            created_by=created_by,
            workspace_id=workspace_id,
            expires_at=(now() + expires_in) if expires_in else None,
            code=uuid.uuid4().hex[:16],
            created_at=now(),
        )
        self._share_links[link.id] = link
        self._persist()
        logger.info("Created share link for %s/%s (%s)", entity_type, entity_id, permission.value)
        return link

    def resolve_share_link(self, code: str) -> Optional[ShareLink]:
        for link in self._share_links.values():
            if link.code == code and not link.is_revoked:
                if link.expires_at and link.expires_at < now():
                    return None
                link.access_count += 1
                self._persist()
                return link
        return None

    def revoke_share_link(self, link_id: str) -> bool:
        link = self._share_links.get(link_id)
        if link is None:
            return False
        link.is_revoked = True
        self._persist()
        return True

    def list_shared(self, workspace_id: Optional[str] = None,
                    entity_type: Optional[str] = None) -> List[SharedKnowledge]:
        results = list(self._items.values())
        if workspace_id:
            results = [i for i in results if i.workspace_id == workspace_id]
        if entity_type:
            results = [i for i in results if i.entity_type == entity_type]
        return results

    def unshare(self, item_id: str) -> bool:
        if item_id in self._items:
            del self._items[item_id]
            self._persist()
            return True
        return False

    def get_shared_embeddings(self, workspace_id: str) -> List[Dict[str, Any]]:
        try:
            from aetheros_knowledge.vectordb import get_vector_store
            store = get_vector_store()
            return store.search(workspace_id=workspace_id, limit=100)
        except ImportError:
            logger.debug("Vector store not available")
            return []
        except Exception as e:
            logger.error("Failed to get shared embeddings: %s", e)
            return []

    def _persist(self):
        import dataclasses
        from enum import Enum
        def ser(obj):
            if dataclasses.is_dataclass(obj):
                return {f.name: ser(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, list):
                return [ser(v) for v in obj]
            if isinstance(obj, dict):
                return {k: ser(v) for k, v in obj.items()}
            return obj
        items_file = self._data_dir / "shared_items.json"
        links_file = self._data_dir / "share_links.json"
        items_file.write_text(json.dumps([ser(i) for i in self._items.values()], indent=2, default=str))
        links_file.write_text(json.dumps([ser(l) for l in self._share_links.values()], indent=2, default=str))

    def _load(self):
        items_file = self._data_dir / "shared_items.json"
        links_file = self._data_dir / "share_links.json"
        if items_file.exists():
            try:
                data = json.loads(items_file.read_text())
                for d in data:
                    item = SharedKnowledge(
                        id=d.get("id", ""),
                        workspace_id=d.get("workspace_id", ""),
                        entity_type=d.get("entity_type", ""),
                        entity_id=d.get("entity_id", ""),
                        name=d.get("name", ""),
                        description=d.get("description", ""),
                        tags=d.get("tags", []),
                        created_by=d.get("created_by", ""),
                        created_at=d.get("created_at", 0.0),
                        updated_at=d.get("updated_at", 0.0),
                        access_count=d.get("access_count", 0),
                        is_pinned=d.get("is_pinned", False),
                    )
                    self._items[item.id] = item
            except Exception as e:
                logger.error("Failed to load shared items: %s", e)
        if links_file.exists():
            try:
                data = json.loads(links_file.read_text())
                for d in data:
                    try:
                        perm = SharePermission(d.get("permission", "read"))
                    except ValueError:
                        perm = SharePermission.READ
                    link = ShareLink(
                        id=d.get("id", ""),
                        entity_type=d.get("entity_type", ""),
                        entity_id=d.get("entity_id", ""),
                        permission=perm,
                        created_by=d.get("created_by", ""),
                        workspace_id=d.get("workspace_id", ""),
                        expires_at=d.get("expires_at"),
                        is_revoked=d.get("is_revoked", False),
                        code=d.get("code", ""),
                        created_at=d.get("created_at", 0.0),
                        access_count=d.get("access_count", 0),
                    )
                    self._share_links[link.id] = link
            except Exception as e:
                logger.error("Failed to load share links: %s", e)
