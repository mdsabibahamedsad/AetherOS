"""Validated export/import for the memory fabric.

Export produces a schema-versioned, integrity-checked bundle.  Import is
STRICT: it verifies schema version + checksums, refuses unknown fields
(via MemoryEntry.from_dict), and re-runs the defense scan so a bundle
smuggling an injection payload or a secret cannot enter the store cleanly.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_memory_intelligence.defense import DefenseVerdict, InjectionDefense
from aetheros_memory_intelligence.schema import MemoryEntry, SchemaVersion
from aetheros_memory_intelligence.store import MemoryStore


@dataclass
class ExportResult:
    path: str
    entry_count: int
    schema_version: int
    checksum: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "entry_count": self.entry_count,
            "schema_version": self.schema_version,
            "checksum": self.checksum,
        }


@dataclass
class ImportReport:
    imported: int = 0
    rejected: int = 0
    rejected_reasons: List[str] = None

    def __post_init__(self) -> None:
        if self.rejected_reasons is None:
            self.rejected_reasons = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "imported": self.imported,
            "rejected": self.rejected,
            "rejected_reasons": self.rejected_reasons[:20],
        }


class TransferService:
    """Export + strict import of the fabric's entries."""

    def __init__(self, store: MemoryStore, *, defense: Optional[InjectionDefense] = None) -> None:
        self._store = store
        self._defense = defense or InjectionDefense()

    def export(self, destination: Path, *, include_archived: bool = False) -> ExportResult:
        entries = [e for e in self._store.all() if include_archived or e.state.value == "active"]
        bundle = {
            "kind": "aetheros-memory-intelligence",
            "schema_version": SchemaVersion.CURRENT,
            "exported_at": time.time(),
            "entries": [e.to_dict() for e in entries],
        }
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        return ExportResult(
            path=str(destination),
            entry_count=len(entries),
            schema_version=SchemaVersion.CURRENT,
            checksum=_sha256_file(destination),
        )

    def import_bundle(self, source: Path) -> ImportReport:
        report = ImportReport()
        try:
            bundle = json.loads(Path(source).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            report.rejected += 1
            report.rejected_reasons.append(f"unreadable bundle: {exc}")
            return report
        if bundle.get("kind") != "aetheros-memory-intelligence":
            report.rejected += 1
            report.rejected_reasons.append("wrong bundle kind")
            return report
        if not SchemaVersion.validate(bundle.get("schema_version")):
            report.rejected += 1
            report.rejected_reasons.append("unsupported schema version")
            return report

        accepted: List[MemoryEntry] = []
        for raw in bundle.get("entries", []):
            try:
                entry = MemoryEntry.from_dict(raw)
            except (ValueError, KeyError) as exc:
                report.rejected += 1
                report.rejected_reasons.append(f"entry schema invalid: {exc}")
                continue
            # Defense re-scan: never let a bundle smuggle content in clean.
            verdict = self._defense.inspect(entry.content, origin=entry.origin.value)
            if verdict.verdict != DefenseVerdict.SAFE:
                report.rejected += 1
                report.rejected_reasons.append(f"entry {entry.id}: defense: {verdict.reasons[:2]}")
                continue
            if entry.checksum and not entry.verify_integrity():
                report.rejected += 1
                report.rejected_reasons.append(f"entry {entry.id}: checksum mismatch")
                continue
            entry.checksum = ""  # re-seal after import
            entry.seal()
            accepted.append(entry)

        if accepted:
            self._store.save_many(accepted)
        report.imported = len(accepted)
        return report


def _sha256_file(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()