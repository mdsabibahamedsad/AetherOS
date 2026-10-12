"""
Memory Importer — imports memory from various formats.

Supports import from:
  - JSON (AetherOS export format)
  - Legacy SQLite (from existing Aetheros memory stores)
  - Markdown (structured format)
  - Previous memory system exports

All imports validate format version and handle migration.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope

logger = logging.getLogger(__name__)

SUPPORTED_IMPORT_VERSIONS = {"1.0"}


@dataclass
class ImportResult:
    """Result of a memory import operation.

    Attributes:
        total_parsed: Total entries parsed from source
        imported: Number of entries successfully imported
        skipped: Number of entries skipped (duplicates, invalid)
        errors: Number of entries that failed to import
        error_messages: List of error messages
        duration_seconds: How long the import took
    """
    total_parsed: int = 0
    imported: int = 0
    skipped: int = 0
    errors: int = 0
    error_messages: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class ImportOptions:
    """Options for memory import.

    Attributes:
        source_path: Path to import file/directory
        format: Import format (auto-detect by default)
        namespace: Override namespace for all imported entries
        merge_duplicates: Whether to merge with existing entries
        default_scope: Default scope if not specified in source
        validate: Whether to validate entries before import
        dry_run: If True, parse but don't actually import
    """
    source_path: str = ""
    format: str = "auto"
    namespace: str = ""
    merge_duplicates: bool = True
    default_scope: str = "global"
    validate: bool = True
    dry_run: bool = False


class MemoryImporter:
    """Imports memory entries from external sources.

    Usage:
        importer = MemoryImporter(store)
        result = importer.import_from_file("memory_export.json")
        result = importer.import_from_json(json_str)
        result = importer.import_from_legacy("legacy_memory.db")
    """

    def __init__(self, store: MemoryStore):
        self._store = store

    # ------------------------------------------------------------------
    # Main import
    # ------------------------------------------------------------------

    def import_from_file(self, file_path: str,
                         options: Optional[ImportOptions] = None) -> ImportResult:
        """Import memory from a file.

        Auto-detects format from file extension if format is "auto".

        Args:
            file_path: Path to the import file
            options: Import options

        Returns:
            ImportResult with import statistics
        """
        opts = options or ImportOptions()
        path = Path(file_path)

        if not path.exists():
            return ImportResult(
                errors=1,
                error_messages=[f"File not found: {file_path}"],
            )

        # Auto-detect format
        fmt = opts.format
        if fmt == "auto":
            ext = path.suffix.lower()
            if ext == ".json":
                fmt = "json"
            elif ext == ".db" or ext == ".sqlite":
                fmt = "sqlite"
            elif ext == ".md":
                fmt = "markdown"
            elif ext == ".csv":
                fmt = "csv"
            else:
                return ImportResult(
                    errors=1,
                    error_messages=[f"Unknown format for file: {file_path}"],
                )

        if fmt == "sqlite":
            return self.import_from_sqlite(file_path, opts)

        content = path.read_text(encoding="utf-8", errors="replace")

        if fmt == "json":
            return self.import_from_json(content, opts)
        elif fmt == "markdown":
            return self.import_from_markdown(content, opts)
        elif fmt == "csv":
            return self.import_from_csv(content, opts)
        else:
            return ImportResult(
                errors=1,
                error_messages=[f"Unsupported import format: {fmt}"],
            )

    # ------------------------------------------------------------------
    # Format-specific importers
    # ------------------------------------------------------------------

    def import_from_json(self, json_str: str,
                         options: Optional[ImportOptions] = None) -> ImportResult:
        """Import memory from JSON format (AetherOS export format)."""
        start = time.time()
        result = ImportResult()
        opts = options or ImportOptions()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            result.errors = 1
            result.error_messages.append(f"JSON parse error: {exc}")
            result.duration_seconds = time.time() - start
            return result

        # Validate format version
        export_version = data.get("export_version", "0.0")
        if export_version not in SUPPORTED_IMPORT_VERSIONS:
            result.errors = 1
            result.error_messages.append(
                f"Unsupported export version: {export_version}. "
                f"Supported: {SUPPORTED_IMPORT_VERSIONS}"
            )
            result.duration_seconds = time.time() - start
            return result

        entries_data = data.get("entries", [])
        result.total_parsed = len(entries_data)

        for entry_data in entries_data:
            try:
                if not self._validate_entry_data(entry_data, opts):
                    result.skipped += 1
                    continue

                entry = self._entry_from_dict(entry_data, opts)

                if opts.dry_run:
                    result.imported += 1
                    continue

                self._store.save(
                    key=entry.key, value=entry.value,
                    memory_type=entry.memory_type,
                    scope=entry.scope, namespace=entry.namespace,
                    tags=entry.tags, metadata=entry.metadata,
                    importance=entry.importance, source=entry.source,
                    entry_id=entry.id,
                )
                result.imported += 1

            except Exception as exc:
                result.errors += 1
                result.error_messages.append(
                    f"Entry import failed: {exc}"
                )

        result.duration_seconds = time.time() - start
        logger.info(
            "Import: parsed=%d, imported=%d, skipped=%d, errors=%d in %.2fs",
            result.total_parsed, result.imported,
            result.skipped, result.errors, result.duration_seconds,
        )
        return result

    def import_from_sqlite(self, db_path: str,
                           options: Optional[ImportOptions] = None) -> ImportResult:
        """Import memory from a legacy SQLite database."""
        start = time.time()
        result = ImportResult()
        opts = options or ImportOptions()

        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT id, key, value, memory_type, scope, namespace, tags, "
                "metadata, importance, created_at, updated_at, expires_at, source "
                "FROM memory_entries"
            )
            rows = cursor.fetchall()
            result.total_parsed = len(rows)

            for row in rows:
                try:
                    entry_id, key, value_json, memory_type, scope_str, \
                        namespace, tags_json, metadata_json, importance, \
                        created_at, updated_at, expires_at, source = row

                    # Parse stored values
                    value = json.loads(value_json) if value_json else None
                    tags = json.loads(tags_json) if tags_json else []
                    metadata = json.loads(metadata_json) if metadata_json else {}
                    scope = MemoryScope(scope_str) if scope_str else MemoryScope.GLOBAL

                    if opts.namespace:
                        namespace = opts.namespace

                    entry = MemoryEntry(
                        id=entry_id, key=key, value=value,
                        memory_type=memory_type, scope=scope,
                        namespace=namespace, tags=tags,
                        metadata=metadata, importance=importance,
                        created_at=created_at, updated_at=updated_at,
                        expires_at=expires_at, source=source,
                    )

                    if not opts.dry_run:
                        self._store.save(
                            key=entry.key, value=entry.value,
                            memory_type=entry.memory_type, scope=entry.scope,
                            namespace=entry.namespace, tags=entry.tags,
                            metadata=entry.metadata, importance=entry.importance,
                            source=entry.source, entry_id=entry.id,
                        )
                    result.imported += 1

                except Exception as exc:
                    result.errors += 1
                    result.error_messages.append(f"Row import failed: {exc}")

            conn.close()

        except Exception as exc:
            result.errors += 1
            result.error_messages.append(f"SQLite import failed: {exc}")

        result.duration_seconds = time.time() - start
        return result

    def import_from_markdown(self, md_str: str,
                             options: Optional[ImportOptions] = None) -> ImportResult:
        """Import memory from structured Markdown format."""
        start = time.time()
        result = ImportResult()
        opts = options or ImportOptions()

        # Very basic markdown parser for structured memory format
        lines = md_str.split("\n")
        current_type = "general"
        current_key = ""
        current_value = ""
        current_tags = []
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                current_value += line + "\n"
                continue

            # Section header -> memory type
            if stripped.startswith("## "):
                # Save previous entry
                if current_key and current_value.strip():
                    try:
                        entry = MemoryEntry(
                            key=current_key,
                            value=current_value.strip(),
                            memory_type=current_type,
                            scope=MemoryScope.GLOBAL,
                            tags=current_tags,
                        )
                        if not opts.dry_run:
                            self._store.save(
                                key=entry.key, value=entry.value,
                                memory_type=entry.memory_type,
                                scope=entry.scope, namespace=opts.namespace,
                                tags=entry.tags, importance=0.5,
                            )
                        result.imported += 1
                    except Exception:
                        result.errors += 1

                current_type = stripped[3:].split("(")[0].strip().lower()
                current_key = ""
                current_value = ""
                current_tags = []
                continue

            # Entry header
            if stripped.startswith("### "):
                if current_key and current_value.strip():
                    try:
                        entry = MemoryEntry(
                            key=current_key,
                            value=current_value.strip(),
                            memory_type=current_type,
                            scope=MemoryScope.GLOBAL,
                            tags=current_tags,
                        )
                        if not opts.dry_run:
                            self._store.save(
                                key=entry.key, value=entry.value,
                                memory_type=entry.memory_type,
                                scope=entry.scope, namespace=opts.namespace,
                                tags=entry.tags, importance=0.5,
                            )
                        result.imported += 1
                    except Exception:
                        result.errors += 1

                current_key = stripped[4:].strip()
                current_value = ""
                current_tags = []
                continue

            # Tags line
            if stripped.startswith("- **Tags:**"):
                tag_str = stripped.split(":", 1)[1]
                current_tags = [t.strip() for t in tag_str.split(",") if t.strip()]

        # Save last entry
        if current_key and current_value.strip():
            try:
                if not opts.dry_run:
                    self._store.save(
                        key=current_key, value=current_value.strip(),
                        memory_type=current_type, scope=MemoryScope.GLOBAL,
                        namespace=opts.namespace,
                        tags=current_tags, importance=0.5,
                    )
                result.imported += 1
            except Exception:
                result.errors += 1

        result.total_parsed = result.imported + result.errors
        result.duration_seconds = time.time() - start
        return result

    def import_from_csv(self, csv_str: str,
                        options: Optional[ImportOptions] = None) -> ImportResult:
        """Import memory from CSV format."""
        start = time.time()
        result = ImportResult()
        opts = options or ImportOptions()

        try:
            import csv
            import io

            reader = csv.DictReader(io.StringIO(csv_str))
            rows = list(reader)
            result.total_parsed = len(rows)

            for row in rows:
                try:
                    key = row.get("key", "")
                    if not key:
                        continue

                    value = row.get("value", "")
                    memory_type = row.get("memory_type", "general")
                    scope_str = row.get("scope", opts.default_scope)
                    namespace = opts.namespace or row.get("namespace", "")
                    tags_str = row.get("tags", "")
                    tags = [t.strip() for t in tags_str.split(";") if t.strip()]

                    try:
                        scope = MemoryScope(scope_str)
                    except ValueError:
                        scope = MemoryScope.GLOBAL

                    if not opts.dry_run:
                        self._store.save(
                            key=key, value=value,
                            memory_type=memory_type, scope=scope,
                            namespace=namespace, tags=tags,
                            importance=0.5,
                        )
                    result.imported += 1

                except Exception as exc:
                    result.errors += 1
                    result.error_messages.append(f"Row import failed: {exc}")

        except Exception as exc:
            result.errors = result.total_parsed
            result.error_messages.append(f"CSV parse error: {exc}")

        result.duration_seconds = time.time() - start
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate_entry_data(self, data: Dict[str, Any],
                             opts: ImportOptions) -> bool:
        """Validate an entry data dictionary."""
        if not isinstance(data, dict):
            return False
        if not data.get("key"):
            return False
        if opts.validate and "memory_type" not in data:
            return False
        return True

    def _entry_from_dict(self, data: Dict[str, Any],
                         opts: ImportOptions) -> MemoryEntry:
        """Convert a dictionary to a MemoryEntry."""
        scope_str = data.get("scope", opts.default_scope)
        try:
            scope = MemoryScope(scope_str)
        except ValueError:
            scope = MemoryScope.GLOBAL

        namespace = opts.namespace or data.get("namespace", "")

        # Parse tags
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        return MemoryEntry(
            id=data.get("id", ""),
            key=data["key"],
            value=data.get("value"),
            memory_type=data.get("memory_type", "general"),
            scope=scope,
            namespace=namespace,
            tags=tags,
            metadata=data.get("metadata", {}),
            importance=data.get("importance", 0.5),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            source=data.get("source", "import"),
        )

    def stats(self) -> Dict[str, Any]:
        """Return import statistics."""
        return {
            "supported_versions": list(SUPPORTED_IMPORT_VERSIONS),
            "supported_formats": ["json", "sqlite", "markdown", "csv"],
        }
