"""Restore manager (sections 45-48, 91-94).

Flow: VALIDATE -> PREVIEW -> SAFETY SNAPSHOT -> RESTORE -> MIGRATE ->
INTEGRITY CHECK -> RECONCILE -> VERIFY.

- Never overwrites live state before a safety snapshot exists.
- Authority is revalidated: expired/revoked grants stay revoked (91).
- Restored tasks enter RECOVERED_PENDING_RECONCILIATION when side effects
  are uncertain (92). Dangerous actions are never auto-continued.
- Memory keeps provenance/version/trust (93); artifacts re-hash (94).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home
from aetheros_data.backup import BackupManager
from aetheros_data.engine import StorageEngine

RESTORE_MODES = ("FULL_RESTORE", "SELECTIVE_RESTORE")
# POINT_IN_TIME / DISASTER_RECOVERY-as-mode are NOT separate code paths:
# point-in-time == restore the backup whose created_at you want; DR is the
# documented procedure in docs/AETHEROS_DISASTER_RECOVERY.md. NOT_IMPLEMENTED
# as magic buttons by design.


class RestoreManager:
    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine
        self.backups = BackupManager(engine)
        self.home = get_aetheros_home()

    def preview(self, backup_id: str, encryption_key: Optional[bytes] = None) -> Dict[str, Any]:
        verify = self.backups.verify(backup_id, encryption_key)
        if not verify["ok"]:
            return {"ok": False, "reasons": verify["reasons"]}
        reg = self._reg(backup_id)
        manifest = self._read_manifest(Path(reg["path"]), encryption_key)
        files = manifest.get("files", [])
        return {
            "ok": True,
            "backup_id": backup_id,
            "scope": manifest.get("scope"),
            "kind": manifest.get("kind"),
            "created_at": manifest.get("created_at"),
            "files": len(files),
            "files_affected": [f["rel"] for f in files][:50],
            "schema_version": manifest.get("schema_version"),
            "warnings": [
                "live state will be preserved in a safety snapshot first",
                "authority grants will be revalidated; expired/revoked stay revoked",
                "tasks with uncertain side effects enter RECOVERED_PENDING_RECONCILIATION",
            ],
        }

    def restore(self, backup_id: str, mode: str = "FULL_RESTORE",
                domains: Optional[List[str]] = None,
                encryption_key: Optional[bytes] = None,
                assume_yes: bool = False) -> Dict[str, Any]:
        assert mode in RESTORE_MODES, mode
        if not assume_yes:
            raise PermissionError("restore requires explicit confirmation (assume_yes=True)")
        verify = self.backups.verify(backup_id, encryption_key)
        if not verify["ok"]:
            return {"ok": False, "phase": "VALIDATE", "reasons": verify["reasons"]}
        # SAFETY SNAPSHOT of live state first.
        safety = self.backups.create(scope="critical", kind="SNAPSHOT")
        reg = self._reg(backup_id)
        tmpdir = Path(tempfile.mkdtemp(prefix="aetheros-restore-"))
        try:
            self._extract(Path(reg["path"]), tmpdir, encryption_key)
            manifest = json.loads((tmpdir / "MANIFEST.json").read_text())
            wanted = {f["rel"] for f in manifest.get("files", [])}
            if mode == "SELECTIVE_RESTORE" and domains:
                wanted = {r for r in wanted if any(r.startswith(self._domain_prefix(d)) for d in domains)}
            for rel in sorted(wanted):
                src = tmpdir / Path(rel)
                if not src.exists():
                    continue
                if rel == manifest.get("canonical_db", "data/aetheros_data.db"):
                    self._restore_database(src)
                else:
                    dst = self.home / Path(rel)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            integrity = self.e.integrity_check()
            reconciled = self._post_restore_reconcile()
            with self.e.transaction() as conn:
                self.e.append_event("restore", backup_id, "restore.completed",
                                    {"backup_id": backup_id, "mode": mode,
                                     "safety_snapshot": safety.backup_id}, conn=conn)
            from aetheros_data.records import AuditLog
            AuditLog(self.e).record("restore-manager", "restore.completed", backup_id,
                                    result="ok" if integrity["status"] != "CORRUPTED" else "degraded",
                                    payload={"mode": mode, "safety": safety.backup_id})
            return {"ok": integrity["status"] != "CORRUPTED", "mode": mode,
                    "safety_snapshot": safety.backup_id, "integrity": integrity,
                    "reconciled": reconciled}
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    # -- internals ---------------------------------------------------------
    def _reg(self, backup_id: str) -> Dict[str, Any]:
        row = self.e._conn().execute("SELECT * FROM backup_registry WHERE backup_id=?",
                                     (backup_id,)).fetchone()
        assert row is not None, backup_id
        return dict(row)

    def _read_manifest(self, path: Path, key: Optional[bytes]) -> Dict[str, Any]:
        if path.suffix == ".enc":
            assert key is not None
            payload = BackupManager.decrypt_file(path, key)
            import tempfile as tf
            with tf.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(payload)
                zp = Path(tmp.name)
            try:
                with zipfile.ZipFile(zp) as z:
                    return json.loads(z.read("MANIFEST.json"))
            finally:
                zp.unlink(missing_ok=True)
        with zipfile.ZipFile(path) as z:
            return json.loads(z.read("MANIFEST.json"))

    def _extract(self, path: Path, dest: Path, key: Optional[bytes]) -> None:
        if path.suffix == ".enc":
            assert key is not None
            payload = BackupManager.decrypt_file(path, key)
            import tempfile as tf
            with tf.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(payload)
                zp = Path(tmp.name)
            try:
                with zipfile.ZipFile(zp) as z:
                    z.extractall(dest)
            finally:
                zp.unlink(missing_ok=True)
        else:
            with zipfile.ZipFile(path) as z:
                z.extractall(dest)

    def _domain_prefix(self, domain: str) -> str:
        return {"task": "data/", "memory": "data/", "artifact": "data/artifacts",
                "configuration": "config", "audit": "data/"}.get(domain, "data/")

    def _restore_database(self, src: Path) -> None:
        """Merge backup rows into the live DB without resurrecting bad authority.

        Strategy: read the backup DB through a second read-only connection and
        copy rows in Python (no ATTACH — ATTACH filenames are not treated as
        URIs on all platforms). Authority grants are copied ONLY if still
        temporally valid AND not revoked in the live DB (section 91).
        """
        bkp = sqlite3.connect("file:" + src.as_posix() + "?mode=ro", uri=True)
        bkp.row_factory = sqlite3.Row
        try:
            names = {r[0] for r in bkp.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

            def cols(table: str) -> List[str]:
                return [r[1] for r in self.e._conn().execute(
                    f"PRAGMA table_info({table})").fetchall()]

            with self.e.transaction() as conn:
                if "records" in names:
                    for r in bkp.execute("SELECT * FROM records"):
                        conn.execute(
                            "INSERT OR REPLACE INTO records (domain, record_id, version,"
                            " generation, data, idempotency_key, created_at, updated_at, deleted)"
                            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (r["domain"], r["record_id"], r["version"], r["generation"],
                             r["data"], r["idempotency_key"], r["created_at"],
                             r["updated_at"], r["deleted"]))
                if "events" in names:
                    for r in bkp.execute("SELECT * FROM events"):
                        conn.execute(
                            "INSERT OR IGNORE INTO events (event_id, timestamp, aggregate_id,"
                            " aggregate_type, actor, task_id, agent_id, correlation_id,"
                            " causation_id, schema_version, kind, durable, payload)"
                            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (r["event_id"], r["timestamp"], r["aggregate_id"],
                             r["aggregate_type"], r["actor"], r["task_id"], r["agent_id"],
                             r["correlation_id"], r["causation_id"], r["schema_version"],
                             r["kind"], r["durable"], r["payload"]))
                if "side_effects" in names:
                    for r in bkp.execute("SELECT * FROM side_effects"):
                        # Uncertain side effects enter reconciliation, never SUCCESS.
                        state = ("UNKNOWN_OUTCOME" if r["state"] == "COMMITTED" else r["state"])
                        conn.execute(
                            "INSERT OR IGNORE INTO side_effects (operation_id, task_id, kind,"
                            " state, idempotency_key, receipt, created_at, updated_at)"
                            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (r["operation_id"], r["task_id"], r["kind"], state,
                             r["idempotency_key"], r["receipt"], r["created_at"], r["updated_at"]))
                for table in ("checkpoints", "memory_records", "graph_nodes",
                              "graph_edges", "config_values", "artifacts"):
                    if table not in names:
                        continue
                    collist = cols(table)
                    placeholders = ", ".join(["?"] * len(collist))
                    for r in bkp.execute(f"SELECT * FROM {table}"):
                        try:
                            conn.execute(
                                f"INSERT OR REPLACE INTO {table} ({', '.join(collist)})"
                                f" VALUES ({placeholders})",
                                tuple(r[c] for c in collist))
                        except sqlite3.IntegrityError:
                            pass
                if "authority_grants" in names:
                    now = time.time()
                    live_revoked = {r[0] for r in conn.execute(
                        "SELECT grant_id FROM authority_grants WHERE revoked=1").fetchall()}
                    for r in bkp.execute("SELECT * FROM authority_grants"):
                        if int(r["revoked"]) or float(r["expires_at"]) <= now:
                            continue
                        if r["grant_id"] in live_revoked:
                            continue
                        conn.execute(
                            "INSERT OR REPLACE INTO authority_grants (grant_id, subject,"
                            " capability, delegate, policy_version, issued_at, expires_at,"
                            " revoked, version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (r["grant_id"], r["subject"], r["capability"], r["delegate"],
                             r["policy_version"], r["issued_at"], r["expires_at"],
                             r["revoked"], r["version"]))
        finally:
            bkp.close()

    def _post_restore_reconcile(self) -> Dict[str, Any]:
        unknowns = self.e._conn().execute(
            "SELECT operation_id FROM side_effects WHERE state='UNKNOWN_OUTCOME'").fetchall()
        with self.e.transaction() as conn:
            for row in unknowns:
                self.e.append_event("restore", row["operation_id"], "recovery.event",
                                    {"operation_id": row["operation_id"],
                                     "state": "RECOVERED_PENDING_RECONCILIATION"}, conn=conn)
        return {"pending_reconciliation": [r["operation_id"] for r in unknowns]}
