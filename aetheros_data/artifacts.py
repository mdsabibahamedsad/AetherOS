"""Content-addressed artifact store (sections 22-24, 94).

Large binaries live on the filesystem under ``<HOME>/data/artifacts/`` keyed
by content hash; only metadata lives in SQLite. Versions form a parent chain;
important artifacts are never silently overwritten.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home
from aetheros_data.engine import StorageEngine


def _home_artifacts() -> Path:
    p = get_aetheros_home() / "data" / "artifacts"
    p.mkdir(parents=True, exist_ok=True)
    return p


class ArtifactStore:
    def __init__(self, engine: StorageEngine, root: Optional[Path] = None) -> None:
        self.e = engine
        self.root = Path(root) if root else _home_artifacts()

    def put(self, data: bytes, owner: str = "", classification: str = "internal",
            provenance: Optional[Dict[str, Any]] = None, parent: str = "",
            filename: str = "") -> Dict[str, Any]:
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        existing = self.e._conn().execute(
            "SELECT * FROM artifacts WHERE content_hash=? ORDER BY version DESC LIMIT 1",
            (digest,)).fetchone()
        version = 1
        if parent:
            prow = self.e._conn().execute("SELECT version FROM artifacts WHERE artifact_id=?",
                                          (parent,)).fetchone()
            if prow:
                version = int(prow["version"]) + 1
        elif existing is not None:
            # Deduplication: same bytes already stored — return canonical record.
            return dict(existing)
        aid = f"art_{uuid.uuid4().hex[:12]}"
        rel = Path(digest.replace(":", "_")[:2]) / digest.replace(":", "_")
        dest = self.root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)
        mime = mimetypes.guess_type(filename or aid)[0] or "application/octet-stream"
        meta = {"filename": filename}
        with self.e.transaction() as conn:
            conn.execute(
                "INSERT INTO artifacts (artifact_id, content_hash, mime, size, rel_path,"
                " metadata, owner, classification, provenance, parent, version, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, digest, mime, len(data), str(rel), json.dumps(meta), owner,
                 classification, json.dumps(provenance or {}), parent, version, time.time()),
            )
            self.e.append_event("artifact", aid, "artifact.created",
                                {"artifact_id": aid, "content_hash": digest, "size": len(data)},
                                conn=conn)
        row = self.e._conn().execute("SELECT * FROM artifacts WHERE artifact_id=?", (aid,)).fetchone()
        return dict(row)

    def get_bytes(self, artifact_id: str, verify: bool = True) -> bytes:
        row = self.e._conn().execute("SELECT * FROM artifacts WHERE artifact_id=?",
                                     (artifact_id,)).fetchone()
        if row is None:
            raise KeyError(artifact_id)
        data = (self.root / row["rel_path"]).read_bytes()
        if verify:
            digest = "sha256:" + hashlib.sha256(data).hexdigest()
            if digest != row["content_hash"]:
                raise ValueError(f"artifact {artifact_id} failed integrity verification")
        return data

    def history(self, artifact_id: str) -> List[Dict[str, Any]]:
        """Walk the parent chain newest-first."""
        out: List[Dict[str, Any]] = []
        cur: Optional[str] = artifact_id
        while cur:
            row = self.e._conn().execute("SELECT * FROM artifacts WHERE artifact_id=?",
                                         (cur,)).fetchone()
            if row is None:
                break
            d = dict(row)
            out.append(d)
            cur = d.get("parent") or None
        return out
