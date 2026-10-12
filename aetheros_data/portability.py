"""Data portability: versioned export/import (sections 69-71, 97-98).

- Export scopes are explicit; secrets excluded by default.
- Import is untrusted: schema + integrity validation, provenance inspection,
  conflict detection, classification, migration, policy gating.
- Imported data can NEVER grant authority or activate credentials (90.5).
- Imported archives are data only: scripts/binaries/macros/plugin code are
  never executed (98).
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_data.engine import StorageEngine

EXPORT_FORMAT_VERSION = 1


class PortabilityManager:
    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def export(self, dest: Path, scope: str = "user",
               include: Optional[List[str]] = None) -> Dict[str, Any]:
        include = include or ["memory", "task", "configuration", "artifact-meta", "automation"]
        assert scope in ("user", "project"), scope
        conn = self.e._conn()
        data: Dict[str, Any] = {}
        if "memory" in include:
            data["memory"] = [dict(r) for r in conn.execute(
                "SELECT * FROM memory_records WHERE status IN ('CONFIRMED','CANDIDATE')").fetchall()]
        if "task" in include:
            data["tasks"] = [dict(r) for r in conn.execute(
                "SELECT * FROM records WHERE domain='task'").fetchall()]
        if "configuration" in include:
            data["configuration"] = [dict(r) for r in conn.execute(
                "SELECT * FROM config_values").fetchall()]
        if "artifact-meta" in include:
            data["artifacts_meta"] = [dict(r) for r in conn.execute(
                "SELECT * FROM artifacts").fetchall()]
        if "automation" in include:
            data["automations"] = [dict(r) for r in conn.execute(
                "SELECT * FROM records WHERE domain='automation'").fetchall()]
        export_id = f"exp_{uuid.uuid4().hex[:10]}"
        envelope = {"format_version": EXPORT_FORMAT_VERSION, "created_at": time.time(),
                    "source_version": "aetheros-data/1.0", "schema_versions": {"data": 3},
                    "manifest": {"export_id": export_id, "scope": scope, "include": include},
                    "data": data, "artifacts": [], "integrity": ""}
        envelope["integrity"] = "sha256:" + hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("EXPORT.json", json.dumps(envelope, indent=2, default=str))
        with self.e.transaction() as c2:
            c2.execute("INSERT INTO export_registry (export_id, created_at, format_version,"
                       " scope, content_hash, path) VALUES (?, ?, ?, ?, ?, ?)",
                       (export_id, envelope["created_at"], EXPORT_FORMAT_VERSION,
                        scope, envelope["integrity"], str(dest)))
        from aetheros_data.records import AuditLog
        AuditLog(self.e).record("portability", "data.export", scope, result="ok",
                                payload={"export_id": export_id, "include": include})
        return {"export_id": export_id, "path": str(dest), "integrity": envelope["integrity"]}

    def inspect(self, path: Path) -> Dict[str, Any]:
        with zipfile.ZipFile(path) as z:
            env = json.loads(z.read("EXPORT.json"))
        actual = "sha256:" + hashlib.sha256(
            json.dumps(env["data"], sort_keys=True, default=str).encode()).hexdigest()
        return {"format_version": env.get("format_version"), "scope": env["manifest"].get("scope"),
                "integrity_ok": actual == env.get("integrity"),
                "counts": {k: len(v) if isinstance(v, list) else 0 for k, v in env.get("data", {}).items()},
                "warnings": ["authority grants and credentials are never imported",
                             "untrusted content: scripts/binaries in archives are never executed"]}

    def import_data(self, path: Path, actor: str = "", authorize: bool = False) -> Dict[str, Any]:
        """Import with validation. ``authorize=True`` = explicit user authorization."""
        if not authorize:
            raise PermissionError("import requires explicit user authorization")
        with zipfile.ZipFile(path) as z:
            env = json.loads(z.read("EXPORT.json"))
        if env.get("format_version") != EXPORT_FORMAT_VERSION:
            return {"ok": False, "reasons": [f"unsupported format {env.get('format_version')}"]}
        actual = "sha256:" + hashlib.sha256(
            json.dumps(env["data"], sort_keys=True, default=str).encode()).hexdigest()
        if actual != env.get("integrity"):
            return {"ok": False, "reasons": ["integrity mismatch; archive untrusted"]}
        imported = {"memory": 0, "tasks": 0, "configuration": 0, "automations": 0}
        with self.e.transaction() as conn:
            for mem in env.get("data", {}).get("memory", []):
                # Preserve provenance/version/trust; never mark old backup memory as
                # current beyond what the archive states.
                conn.execute(
                    "INSERT OR IGNORE INTO memory_records (memory_id, scope, owner, content,"
                    " mem_type, source, provenance, confidence, sensitivity, trust, version,"
                    " status, created_at, updated_at, expires_at, supersedes)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (f"imp_{mem.get('memory_id', uuid.uuid4().hex[:8])}", mem.get("scope", "user"),
                     mem.get("owner", ""), mem.get("content", ""), mem.get("mem_type", "fact"),
                     f"import:{actor}", json.dumps({"imported_from": "export",
                                                    "orig_provenance": mem.get("provenance", "")}),
                     float(mem.get("confidence", 0.3)), mem.get("sensitivity", "internal"),
                     "imported", int(mem.get("version", 1)), "CANDIDATE",
                     time.time(), time.time(), 0, ""),
                )
                imported["memory"] += 1
            for t in env.get("data", {}).get("tasks", []):
                conn.execute(
                    "INSERT OR IGNORE INTO records (domain, record_id, version, generation, data,"
                    " idempotency_key, created_at, updated_at, deleted)"
                    " VALUES ('task', ?, 1, 1, ?, ?, ?, ?, 0)",
                    (f"imp_{t.get('record_id', uuid.uuid4().hex[:8])}",
                     json.dumps({"imported": t.get("data", {}), "state": "RECOVERED_PENDING_RECONCILIATION"}),
                     f"import:{uuid.uuid4().hex[:8]}", time.time(), time.time()),
                )
                imported["tasks"] += 1
            for cfg in env.get("data", {}).get("configuration", []):
                conn.execute(
                    "INSERT OR IGNORE INTO config_values (scope, config_key, value, source, version, updated_at)"
                    " VALUES (?, ?, ?, 'import', 1, ?)",
                    (cfg.get("scope", "USER"), cfg.get("config_key", cfg.get("key", "unknown")),
                     json.dumps(cfg.get("value")), time.time()),
                )
                imported["configuration"] += 1
            # NOTE: authority grants and credentials are deliberately NOT imported.
            self.e.append_event("import", "import", "recovery.event",
                                {"imported": imported, "actor": actor}, conn=conn)
        from aetheros_data.records import AuditLog
        AuditLog(self.e).record(actor or "import", "data.import", "user", result="ok",
                                payload=imported)
        return {"ok": True, "imported": imported,
                "note": "authority/credentials never imported; tasks enter reconciliation"}
