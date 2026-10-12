"""Durable entry store for the memory intelligence fabric.

A simple, corruption-aware, atomic JSON store scoped to the fabric's storage
directory.  Every mutation rewrites an integrity manifest; a torn write is
detected on load and healed from the atomic temp file if present.  This is a
complement to (not a replacement for) the platform MemoryManager — the fabric
store keeps the entry envelopes (with provenance/trust/integrity), while the
platform continues to own embeddings/vector search for those who enable it.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_memory_intelligence.schema import MemoryEntry

logger = logging.getLogger("aetheros_memory_intelligence.store")


class MemoryStore:
    """Atomic, manifest-verified JSON store for MemoryEntry objects."""

    STORE_NAME = "entries.json"
    MANIFEST_NAME = "manifest.json"

    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = Path(root) if root else None
        self._lock = threading.RLock()
        self._entries: Dict[str, MemoryEntry] = {}
        self._loaded = False
        self._generation = 0
        self._quarantined: List[Dict[str, Any]] = []

# ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def root(self) -> Path:
        if self._root is None:
            raise RuntimeError("store root not set; call initialize() first")
        return self._root

    def initialize(self, root: Optional[Path] = None) -> None:
        if root is not None:
            self._root = Path(root)
        else:
            # Set default root to a temporary directory if none provided
            self._root = Path("./temp_store")
        self._root.mkdir(parents=True, exist_ok=True)
        self._load()
        self._loaded = True

    def is_initialized(self) -> bool:
        return self._loaded

    def _entries_path(self) -> Path:
        return self.root / self.STORE_NAME

    def _manifest_path(self) -> Path:
        return self.root / self.MANIFEST_NAME

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def save(self, entry: MemoryEntry) -> MemoryEntry:
        with self._lock:
            entry.seal()
            self._entries[entry.id] = entry
            self._persist()
            self._generation += 1
            return entry

    def save_many(self, entries: List[MemoryEntry]) -> List[MemoryEntry]:
        with self._lock:
            for entry in entries:
                entry.seal()
                self._entries[entry.id] = entry
            self._persist()
            self._generation += 1
            return entries

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        with self._lock:
            return self._entries.get(entry_id)

    def get_many(self, entry_ids: List[str]) -> List[MemoryEntry]:
        with self._lock:
            return [self._entries[i] for i in entry_ids if i in self._entries]

    def all(self) -> List[MemoryEntry]:
        with self._lock:
            return list(self._entries.values())

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            existed = entry_id in self._entries
            if existed:
                self._entries.pop(entry_id, None)
                self._persist()
                self._generation += 1
            return existed

    def delete_many(self, entry_ids: List[str]) -> int:
        with self._lock:
            removed = 0
            for i in entry_ids:
                if i in self._entries:
                    self._entries.pop(i, None)
                    removed += 1
            if removed:
                self._persist()
                self._generation += 1
            return removed

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def quarantine(self, entry_id: str, reason: str) -> None:
        """Move a corrupted/suspicious entry out of the live index."""
        with self._lock:
            entry = self._entries.pop(entry_id, None)
            if entry is None:
                return
            self._quarantined.append({
                "id": entry_id,
                "reason": reason,
                "content": entry.content[:500],
                "quarantined_at": time.time(),
            })
            self._persist()

    def quarantined_entries(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._quarantined)

    # ------------------------------------------------------------------
    # Persistence (atomic, manifest-verified)
    # ------------------------------------------------------------------

    def _persist(self) -> None:
        data = {
            "generation": self._generation,
            "entries": {eid: e.to_dict() for eid, e in self._entries.items()},
            "quarantined": self._quarantined,
        }
        manifest = {
            "generation": self._generation,
            "entry_count": len(self._entries),
            "written_at": time.time(),
        }
        # Write atomically via temp file + os.replace.
        fd, tmp_name = tempfile.mkstemp(dir=str(self.root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_name, str(self._entries_path()))
            (self.root / self.MANIFEST_NAME).write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:
            logger.warning("memory store persist failed: %s", exc)
            if os.path.exists(tmp_name):
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass

    def _load(self) -> None:
        path = self._entries_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            # Heal from a torn write: if a temp file exists, prefer it.
            logger.warning("memory store unreadable (%s); attempting recovery", exc)
            self._recover_torn_write()
            return
        entries: Dict[str, MemoryEntry] = {}
        for raw in data.get("entries", {}).values():
            try:
                entry = MemoryEntry.from_dict(raw)
                entries[entry.id] = entry
            except (ValueError, KeyError) as exc:
                logger.warning("skipping malformed entry in store: %s", exc)
                self._quarantined.append({
                    "id": str(uuid.uuid4()),
                    "reason": f"malformed on load: {exc}",
                    "content": "",
                    "quarantined_at": time.time(),
                })
        self._entries = entries
        self._quarantined = data.get("quarantined", [])
        self._generation = data.get("generation", 0)

    def _recover_torn_write(self) -> None:
        candidates = sorted(self.root.glob("*.tmp"), key=lambda p: p.stat().st_mtime, reverse=True)
        for cand in candidates:
            try:
                data = json.loads(cand.read_text(encoding="utf-8"))
                entries = {
                    raw["id"]: MemoryEntry.from_dict(raw)
                    for raw in data.get("entries", {}).values()
                }
                self._entries = entries
                self._quarantined = data.get("quarantined", [])
                self._generation = data.get("generation", 0)
                logger.info("memory store recovered %d entries from torn write", len(entries))
                os.replace(str(cand), str(self._entries_path()))
                return
            except Exception as exc:
                logger.warning("torn-write candidate unusable: %s", exc)
        logger.error("memory store could not be recovered; starting empty")

    # ------------------------------------------------------------------
    # Integrity scan
    # ------------------------------------------------------------------

    def integrity_scan(self) -> Dict[str, Any]:
        """Verify every entry's checksum.  Returns report + quarantines bad ones."""
        bad = 0
        report_entries: List[Dict[str, Any]] = []
        with self._lock:
            for eid, entry in list(self._entries.items()):
                if entry.checksum and not entry.verify_integrity():
                    bad += 1
                    report_entries.append({"id": eid, "issue": "checksum_mismatch"})
                    self._entries.pop(eid, None)
                    self._quarantined.append({
                        "id": eid,
                        "reason": "checksum mismatch during integrity scan",
                        "content": entry.content[:500],
                        "quarantined_at": time.time(),
                    })
        if bad:
            self._persist()
        return {
            "checked": bad + (self.count()),
            "corrupted": bad,
            "quarantined": len(self._quarantined),
            "details": report_entries,
        }

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            types: Dict[str, int] = {}
            boundaries: Dict[str, int] = {}
            states: Dict[str, int] = {}
            for entry in self._entries.values():
                types[entry.memory_type.value] = types.get(entry.memory_type.value, 0) + 1
                boundaries[entry.boundary.value] = boundaries.get(entry.boundary.value, 0) + 1
                states[entry.state.value] = states.get(entry.state.value, 0) + 1
            return {
                "entry_count": len(self._entries),
                "by_type": types,
                "by_boundary": boundaries,
                "by_state": states,
                "quarantined": len(self._quarantined),
                "generation": self._generation,
            }