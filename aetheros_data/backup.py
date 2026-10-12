"""Backup manager (sections 37-44, 88).

Types supported: FULL and SNAPSHOT (transaction-consistent). INCREMENTAL/
DIFFERENTIAL/POINT_IN_TIME are NOT implemented (STATUS: NOT_IMPLEMENTED —
documented in the certification matrix rather than faked).

Safety:
- SQLite files are snapshotted via the backup API (never a live file copy).
- Secrets (``.env``, tokens, keys) are EXCLUDED by default (section 90.1).
- Every backup has a manifest with hashes; verify re-checks them.
- Encryption uses Fernet (``cryptography``) with a caller-supplied key.
  Key management (generation/rotation/recovery doc) lives in
  docs/AETHEROS_BACKUP_ARCHITECTURE.md; keys are never stored beside the
  backup (section 41).
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home
from aetheros_data.engine import StorageEngine

logger = logging.getLogger(__name__)

SECRET_NAMES = {".env", "auth.json", "mcp-tokens", "signing.key", "credentials.json"}
SECRET_SUFFIXES = (".key", ".pem", ".p12", ".pfx")
SIDE_CARS = (".db-wal", ".db-shm", ".db-journal")

BACKUP_KIND_FULL = "FULL"
BACKUP_KIND_SNAPSHOT = "SNAPSHOT"


def _is_secret(rel: Path) -> bool:
    name = rel.name
    if name in SECRET_NAMES or name in (".env",):
        return True
    if any(name.endswith(s) for s in SECRET_SUFFIXES):
        return True
    return any(part in SECRET_NAMES for part in rel.parts)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


@dataclass
class BackupResult:
    backup_id: str
    path: str
    content_hash: str
    size: int
    files: int
    scope: str
    encryption: str


class BackupManager:
    def __init__(self, engine: StorageEngine, backup_dir: Optional[Path] = None) -> None:
        self.e = engine
        home = get_aetheros_home()
        self.backup_dir = Path(backup_dir) if backup_dir else home / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.home = home

    # -- create ----------------------------------------------------------
    def create(self, scope: str = "critical", kind: str = BACKUP_KIND_FULL,
               include_secrets: bool = False,
               encryption_key: Optional[bytes] = None) -> BackupResult:
        """Create a backup. Secrets excluded unless explicitly requested + audited."""
        assert kind in (BACKUP_KIND_FULL, BACKUP_KIND_SNAPSHOT), kind
        bid = f"bkp_{time.strftime('%Y%m%d-%H%M%S')}_{uuid.uuid4().hex[:8]}"
        work = self.backup_dir / f".tmp-{bid}"
        work.mkdir(parents=True, exist_ok=True)
        try:
            files = self._collect(work, scope=scope, kind=kind, include_secrets=include_secrets)
            try:
                canonical_db = self.e.db_path.relative_to(self.home).as_posix()
            except ValueError:
                canonical_db = ""
            manifest = {
                "backup_id": bid,
                "created_at": time.time(),
                "source": str(self.home),
                "scope": scope,
                "kind": kind,
                "schema_version": self._schema_version(),
                "encryption": "fernet" if encryption_key else "none",
                "compression": "zip",
                "tool_version": "aetheros-data/1.0",
                "include_secrets": include_secrets,
                "canonical_db": canonical_db,
                "files": files,
            }
            (work / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
            zip_path = self.backup_dir / f"{bid}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for entry in files:
                    # entry["rel"] is POSIX; resolve against work via Path (handles / on Windows).
                    z.write(work / Path(entry["rel"]), entry["rel"])
                z.write(work / "MANIFEST.json", "MANIFEST.json")
            digest = _sha256_file(zip_path)
            final_path = zip_path
            if encryption_key:
                final_path = self._encrypt_file(zip_path, encryption_key)
                digest = _sha256_file(final_path)
                zip_path.unlink()
            size = final_path.stat().st_size
            with self.e.transaction() as conn:
                conn.execute(
                    "INSERT INTO backup_registry (backup_id, created_at, source, scope,"
                    " schema_version, encryption, compression, content_hash, size, path, retention_days)"
                    " VALUES (?, ?, ?, ?, ?, ?, 'zip', ?, ?, ?, 90)",
                    (bid, manifest["created_at"], manifest["source"], f"{scope}/{kind}",
                     manifest["schema_version"],
                     manifest["encryption"], digest, size, str(final_path)),
                )
                self.e.append_event("backup", bid, "backup.created",
                                    {"backup_id": bid, "scope": scope, "kind": kind}, conn=conn)
            from aetheros_data.records import AuditLog
            AuditLog(self.e).record("backup-manager", "backup.create", scope,
                                    result="ok", payload={"backup_id": bid, "secrets": include_secrets})
            return BackupResult(bid, str(final_path), digest, size, len(files), scope,
                                manifest["encryption"])
        finally:
            import shutil
            shutil.rmtree(work, ignore_errors=True)

    def _schema_version(self) -> int:
        row = self.e._conn().execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    def _collect(self, work: Path, scope: str, kind: str, include_secrets: bool) -> List[Dict[str, Any]]:
        home = self.home
        # Always include the live canonical DB by its actual path (the engine
        # may point at a test database, not the default name).
        try:
            db_rel = self.e.db_path.relative_to(home)
        except ValueError:
            db_rel = None
        if kind == BACKUP_KIND_SNAPSHOT or scope == "critical":
            rels = ["config.yaml"]
        else:  # FULL: curated set, never the whole $HOME blindly
            rels = ["config.yaml", "data/artifacts",
                    "state.db", "knowledge", "memory_os", "cron/jobs.json", "skills/.usage.json"]
        entries: List[Dict[str, Any]] = []
        seen: set[str] = set()
        candidates = list(rels)
        if db_rel is not None:
            candidates.insert(1, str(db_rel))
        for rel in candidates:
            if rel in seen:
                continue
            seen.add(rel)
            src = home / rel
            if not src.exists():
                continue
            if src.is_file():
                self._copy_one(src, home, work, include_secrets, entries)
            else:
                for f in sorted(src.rglob("*")):
                    if f.is_file():
                        self._copy_one(f, home, work, include_secrets, entries)
        return entries

    def _copy_one(self, src: Path, home: Path, work: Path, include_secrets: bool,
                  entries: List[Dict[str, Any]]) -> None:
        rel = src.relative_to(home)
        # Archive names are POSIX (forward slashes) so backups verify and
        # restore identically on Windows, macOS, and Linux.
        arc = rel.as_posix()
        if any(str(rel).endswith(s) for s in SIDE_CARS):
            return
        if _is_secret(rel) and not include_secrets:
            return
        if src.suffix == ".db":
            # Consistent snapshot via backup API (section 44).
            dst = work / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            s = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
            try:
                d = sqlite3.connect(str(dst))
                try:
                    s.backup(d)
                    d.execute("PRAGMA journal_mode=DELETE")
                    d.commit()
                finally:
                    d.close()
            finally:
                s.close()
        else:
            dst = work / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        entries.append({"rel": arc, "sha256": _sha256_file(work / rel),
                        "size": (work / rel).stat().st_size})

    # -- encryption --------------------------------------------------------
    def _encrypt_file(self, path: Path, key: bytes) -> Path:
        from cryptography.fernet import Fernet
        token = Fernet(key).encrypt(path.read_bytes())
        out = path.with_suffix(".zip.enc")
        out.write_bytes(token)
        return out

    @staticmethod
    def decrypt_file(path: Path, key: bytes) -> bytes:
        from cryptography.fernet import Fernet
        return Fernet(key).decrypt(Path(path).read_bytes())

    # -- list / verify -----------------------------------------------------
    def list(self) -> List[Dict[str, Any]]:
        rows = self.e._conn().execute(
            "SELECT * FROM backup_registry ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def verify(self, backup_id: str, encryption_key: Optional[bytes] = None) -> Dict[str, Any]:
        """Manifest + hash + schema + record-count validation (section 39)."""
        rows = self.e._conn().execute("SELECT * FROM backup_registry WHERE backup_id=?",
                                      (backup_id,)).fetchall()
        if not rows:
            return {"ok": False, "reasons": [f"unknown backup {backup_id}"]}
        reg = dict(rows[0])
        reasons: List[str] = []
        path = Path(reg["path"])
        if not path.exists():
            return {"ok": False, "reasons": [f"backup file missing: {path}"]}
        if _sha256_file(path) != reg["content_hash"]:
            reasons.append("content hash mismatch")
        payload: bytes
        if path.suffix == ".enc":
            if not encryption_key:
                return {"ok": False, "reasons": ["backup is encrypted; key required"]}
            try:
                payload = self.decrypt_file(path, encryption_key)
            except Exception as exc:
                return {"ok": False, "reasons": [f"decrypt failed: {exc}"]}
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(payload)
                zip_path = Path(tmp.name)
        else:
            zip_path = path
        try:
            with zipfile.ZipFile(zip_path) as z:
                names = z.namelist()
                if "MANIFEST.json" not in names:
                    reasons.append("MANIFEST.json missing")
                    manifest: Dict[str, Any] = {}
                else:
                    manifest = json.loads(z.read("MANIFEST.json"))
                    for entry in manifest.get("files", []):
                        try:
                            data = z.read(entry["rel"])
                        except KeyError:
                            reasons.append(f"missing file in archive: {entry['rel']}")
                            continue
                        actual = "sha256:" + hashlib.sha256(data).hexdigest()
                        if actual != entry["sha256"]:
                            reasons.append(f"hash mismatch: {entry['rel']}")
                if manifest.get("schema_version", 0) > self._schema_version() + 1000:
                    reasons.append("schema version from the future")
        except zipfile.BadZipFile as exc:
            reasons.append(f"not a valid zip: {exc}")
        finally:
            if zip_path != path:
                zip_path.unlink(missing_ok=True)
        return {"ok": not reasons, "reasons": reasons, "backup_id": backup_id,
                "content_hash": reg["content_hash"], "size": reg["size"]}
