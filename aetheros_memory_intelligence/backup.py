"""Backup integration for the memory fabric.

Backups reuse the reliability layer's ``BackupStore`` (versioned, atomic,
integrity-verified, rotated) which already snapshots the whole AETHEROS_HOME
including the fabric store.  This module additionally provides a scoped
fabric-only backup for cases where only the memory store matters, plus a
restore path that re-validates every entry on the way back in.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_memory_intelligence.schema import MemoryEntry, validate_entry
from aetheros_memory_intelligence.store import MemoryStore


@dataclass
class FabricBackup:
    path: str
    entry_count: int


class FabricBackupService:
    """Scoped fabric-only backup/restore (reliability BackupStore covers full-home)."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def create(self, destination: Path, *, include_archived: bool = False) -> FabricBackup:
        """Copy the fabric store directory to ``destination`` (a directory)."""
        destination = Path(destination)
        dest_store = MemoryStore(root=destination)
        dest_store.initialize()
        for entry in self._store.all():
            if include_archived or entry.state.value == "active":
                dest_store.save(entry)
        return FabricBackup(path=str(destination), entry_count=dest_store.count())

    def restore(self, source: Path, *, overwrite: bool = True) -> Dict[str, Any]:
        """Load entries from a fabric backup dir and re-validate them.

        Validation runs on restore because a corrupted/poisoned entry must not
        re-enter the live store silently.
        """
        source_store = MemoryStore(root=source)
        source_store.initialize()
        entries = source_store.all()
        accepted: List[MemoryEntry] = []
        rejected = 0
        for entry in entries:
            problems = validate_entry(entry)
            if problems:
                rejected += 1
                continue
            if not entry.verify_integrity():
                rejected += 1
                continue
            accepted.append(entry)
        if overwrite:
            for e in accepted:
                self._store.save(e)
        return {"restored": len(accepted), "rejected": rejected}

    def export_bundle(self, destination: Path, *, include_archived: bool = False) -> FabricBackup:
        """Alias of create() for parity with the CLI's backup/export naming."""
        return self.create(destination, include_archived=include_archived)


def full_home_backup() -> Optional[Any]:
    """Create a full-home backup through the reliability layer.

    Returns the BackupEntry (reliability.backup.BackupEntry) or None if the
    reliability layer is unavailable.
    """
    try:
        from aetheros_reliability.backup import get_backup_store
        store = get_backup_store()
        return store.create(label="memory-intelligence")
    except Exception:
        return None