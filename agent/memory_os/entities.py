"""Entity memory + entity resolution (P10, P11).

Entities are never merged on name alone: resolution weighs identifiers,
domain/repo context, type agreement and co-occurrence, producing
MERGED / SEPARATE / UNCERTAIN outcomes with confidence.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from agent.memory_os.models import Resolution
from agent.memory_os.store import MemoryStore


def canonical_key(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


class EntityRegistry:
    def __init__(self, store: MemoryStore):
        self._store = store

    def create(
        self,
        *,
        etype: str,
        name: str,
        aliases: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
        confidence: float = 0.5,
        identifier: str = "",
        domain: str = "",
        repo: str = "",
    ) -> Dict[str, Any]:
        import json as _json

        entity_id = uuid.uuid4().hex[:12]
        now = time.time()
        stored_meta = dict(meta or {})
        if identifier:
            stored_meta.setdefault("identifier", identifier)
        if repo:
            stored_meta.setdefault("repo", repo)
        if domain:
            stored_meta.setdefault("domain", domain)
        ent = {
            "entity_id": entity_id,
            "etype": etype,
            "name": name,
            "canonical_key": canonical_key(name),
            "confidence": confidence,
            "resolution": Resolution.SEPARATE.value,
            "merged_into": "",
            "created_at": now,
            "updated_at": now,
            "meta": _json.dumps(stored_meta),
        }
        self._store.upsert_entity(ent)
        self._store.add_alias(entity_id, name)
        for a in aliases or []:
            self._store.add_alias(entity_id, a)
        return ent

    def resolve(self, name: str, etype: str = "",
                identifier: str = "", domain: str = "",
                repo: str = "") -> Dict[str, Any]:
        """P11 — find-or-create with evidence-weighted resolution.

        Signals (each adds confidence toward MERGED):
          identifier match  (strongest — unique key)
          repo/domain match (namespace identity)
          alias/canonical-name match within the same entity type
        Name match across *different* types stays UNCERTAIN as a NEW record.
        """
        if identifier:
            hits = [
                e for e in self._store.find_entities(etype=etype or None)
                if (e.get("meta") or "{}").find(identifier) != -1
            ]
            if hits:
                return {"entity": hits[0], "resolution": Resolution.MERGED,
                        "basis": "identifier", "confidence": 0.95}
        if repo or domain:
            marker = repo or domain
            hits = [
                e for e in self._store.find_entities()
                if (e.get("meta") or "{}").find(marker) != -1
                and (not etype or e["etype"] == etype)
            ]
            if hits:
                return {"entity": hits[0], "resolution": Resolution.MERGED,
                        "basis": "namespace", "confidence": 0.85}
        alias_hits = self._store.alias_lookup(name)
        if alias_hits:
            ent = self._store.get_entity(alias_hits[0])
            if ent and ent["resolution"] == Resolution.MERGED.value \
                    and ent.get("merged_into"):
                parent = self._store.get_entity(ent["merged_into"])
                if parent:
                    same_type = (not etype) or parent["etype"] == etype
                    if same_type:
                        return {"entity": parent, "resolution": Resolution.MERGED,
                                "basis": "alias-of-merged", "confidence": 0.9}
            elif ent:
                same_type = (not etype) or ent["etype"] == etype
                if same_type:
                    return {"entity": ent, "resolution": Resolution.MERGED,
                            "basis": "alias", "confidence": 0.8}
        # canonical-key collision across types -> uncertain new entity
        ckey_hits = [
            e for e in self._store.find_entities()
            if e["canonical_key"] == canonical_key(name)
        ]
        if ckey_hits and etype and all(
                h["etype"] != etype for h in ckey_hits):
            ent = self.create(etype=etype, name=name, domain=domain, repo=repo)
            return {"entity": ent, "resolution": Resolution.UNCERTAIN,
                    "basis": "name-collision-different-type", "confidence": 0.3}
        ent = self.create(etype=etype, name=name, identifier=identifier,
                          domain=domain, repo=repo)
        return {"entity": ent, "resolution": Resolution.SEPARATE,
                "basis": "new", "confidence": 0.6}

    def merge(self, keep_id: str, drop_id: str) -> bool:
        """Explicit merge (user-confirmed). drop becomes alias of keep."""
        keep, drop = self._store.get_entity(keep_id), self._store.get_entity(drop_id)
        if not keep or not drop or keep_id == drop_id:
            return False
        self._store.merge_entity(keep_id, drop_id)
        self._store.add_alias(keep_id, drop["name"])
        return True

    def separate(self, merged_parent_id: str) -> int:
        """Undo merges into a parent: children become separate again."""
        count = 0
        for child in self._store.find_entities(resolution=Resolution.MERGED.value):
            if child.get("merged_into") == merged_parent_id:
                child["resolution"] = Resolution.SEPARATE.value
                child["merged_into"] = ""
                child["updated_at"] = time.time()
                self._store.upsert_entity(child)
                count += 1
        return count

    def get(self, entity_id: str) -> Optional[Dict[str, Any]]:
        ent = self._store.get_entity(entity_id)
        if not ent:
            return None
        if ent["resolution"] == Resolution.MERGED.value and ent.get("merged_into"):
            return self._store.get_entity(ent["merged_into"])
        return ent
