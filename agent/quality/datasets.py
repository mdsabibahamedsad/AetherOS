"""Golden dataset versioning + integrity (P30-31).

Datasets are immutable: any content change requires a NEW version with a
change note. Silent replacement is impossible by construction.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class DatasetIntegrityError(Exception):
    pass


@dataclass
class DatasetVersion:
    name: str
    version: int
    records: List[Dict[str, Any]]
    source: str
    license: str
    schema: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    change_note: str = ""
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = self.compute_hash()

    def compute_hash(self) -> str:
        return hashlib.sha256(json.dumps(
            self.records, sort_keys=True, default=str).encode()).hexdigest()[:16]


class DatasetRegistry:
    def __init__(self):
        self._versions: Dict[str, Dict[int, DatasetVersion]] = {}

    def create(self, *, name: str, records: List[Dict[str, Any]],
               source: str, license: str, schema: str,
               change_note: str = "initial") -> DatasetVersion:
        if name in self._versions:
            raise DatasetIntegrityError(f"dataset '{name}' already exists; "
                                        "add_version() instead")
        v = DatasetVersion(name=name, version=1, records=list(records),
                           source=source, license=license, schema=schema,
                           change_note=change_note)
        self._versions[name] = {1: v}
        return v

    def add_version(self, name: str, *, records: List[Dict[str, Any]],
                    change_note: str, source: str = "",
                    license: str = "", schema: str = "") -> DatasetVersion:
        """P31 — dataset evolution is explicit and reviewable."""
        if name not in self._versions:
            raise DatasetIntegrityError(f"unknown dataset '{name}'")
        if not change_note or not change_note.strip():
            raise DatasetIntegrityError("change_note is mandatory")
        prev = self.latest(name)
        v = DatasetVersion(
            name=name, version=prev.version + 1, records=list(records),
            source=source or prev.source, license=license or prev.license,
            schema=schema or prev.schema, change_note=change_note,
        )
        if v.content_hash == prev.content_hash:
            raise DatasetIntegrityError(
                "content identical to previous version; nothing to add")
        self._versions[name][v.version] = v
        return v

    def latest(self, name: str) -> DatasetVersion:
        versions = self._versions.get(name)
        if not versions:
            raise DatasetIntegrityError(f"unknown dataset '{name}'")
        return versions[max(versions)]

    def get(self, name: str, version: int) -> DatasetVersion:
        try:
            return self._versions[name][version]
        except KeyError:
            raise DatasetIntegrityError(
                f"dataset '{name}' has no version {version}")

    def history(self, name: str) -> List[DatasetVersion]:
        return [self._versions[name][v]
                for v in sorted(self._versions.get(name, {}))]

    def verify_integrity(self, name: str, version: int) -> bool:
        v = self.get(name, version)
        return v.content_hash == v.compute_hash()
