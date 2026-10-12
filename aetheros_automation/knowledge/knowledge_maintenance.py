from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class DuplicateGroup:
    ids: list[str]
    similarity: float
    field: str = "content"
    resolution: str = ""


@dataclass
class MaintenanceReport:
    duplicates_found: int = 0
    duplicates_removed: int = 0
    orphaned_deleted: int = 0
    embeddings_updated: int = 0
    permissions_fixed: int = 0
    entries_repaired: int = 0
    errors: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class KnowledgeMaintenance:
    def __init__(self):
        self._reports: list[MaintenanceReport] = []

    def find_duplicates(self, entries: list[dict], key_field: str = "key",
                        similarity_threshold: float = 0.9) -> list[DuplicateGroup]:
        groups = []
        checked = set()
        for i, a in enumerate(entries):
            if i in checked:
                continue
            group_ids = [i]
            for j, b in enumerate(entries):
                if j <= i or j in checked:
                    continue
                sim = self._compute_similarity(
                    str(a.get(key_field, "")),
                    str(b.get(key_field, "")),
                )
                if sim >= similarity_threshold:
                    group_ids.append(j)
                    checked.add(j)
            if len(group_ids) > 1:
                groups.append(DuplicateGroup(
                    ids=[entries[idx].get("id", str(idx)) for idx in group_ids],
                    similarity=1.0 if all(
                        entries[idx].get(key_field) == entries[group_ids[0]].get(key_field)
                        for idx in group_ids) else similarity_threshold,
                    field=key_field,
                ))
            checked.add(i)
        return groups

    def _compute_similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        a = a.lower().strip()
        b = b.lower().strip()
        if a == b:
            return 1.0
        set_a = set(a.split())
        set_b = set(b.split())
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    def find_orphaned_data(self, entries: list[dict], references: set[str],
                           id_field: str = "id") -> list[str]:
        entry_ids = {e.get(id_field, "") for e in entries}
        orphaned = []
        for ref_id in references:
            if ref_id not in entry_ids:
                orphaned.append(ref_id)
        return orphaned

    def validate_entries(self, entries: list[dict], required_fields: list[str] | None = None) -> list[str]:
        errors = []
        fields = required_fields or ["id"]
        for entry in entries:
            for field in fields:
                if field not in entry or entry[field] is None or entry[field] == "":
                    errors.append(f"Entry {entry.get('id', 'unknown')}: missing required field '{field}'")
        return errors

    def run_maintenance(self, entries: list[dict], key_field: str = "key",
                        id_field: str = "id", references: set[str] | None = None,
                        required_fields: list[str] | None = None) -> MaintenanceReport:
        report = MaintenanceReport()
        duplicates = self.find_duplicates(entries, key_field)
        report.duplicates_found = len(duplicates)
        report.details["duplicate_groups"] = [
            {"ids": g.ids, "similarity": g.similarity, "field": g.field} for g in duplicates
        ]
        validation_errors = self.validate_entries(entries, required_fields)
        report.entries_repaired = len(entries) - len(validation_errors)
        for err in validation_errors:
            report.errors.append(err)
        if references:
            orphaned = self.find_orphaned_data(entries, references, id_field)
            report.orphaned_deleted = len(orphaned)
            report.details["orphaned_ids"] = orphaned
        self._reports.append(report)
        return report

    def get_recent_reports(self, limit: int = 10) -> list[MaintenanceReport]:
        return self._reports[-limit:]
