"""Evidence store + provenance graph (spec section 20).

Task -> Contract -> Agent -> Inputs -> Execution -> Outputs -> Evidence
-> Verification -> Payment -> Reputation. Payloads are content-hashed;
secrets are never stored (DLP-scanned on ingest, redacted summaries).
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas as S
from .store import JsonStore

try:
    from aetheros_network.policy import dlp_scan as _dlp_scan
except Exception:  # pragma: no cover
    def _dlp_scan(text: str):  # type: ignore[misc]
        return []


class EvidenceStore:
    def __init__(self, home: Path) -> None:
        home = Path(home)
        self._dir = home / "evidence_blobs"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index = JsonStore(home / "evidence.json")

    def put(self, kind: str, payload: bytes, delegation_id: str = "",
            contract_id: str = "", task_id: str = "", actor: str = "",
            summary: str = "", correlation_id: str = "") -> S.Evidence:
        if kind not in ("input", "output", "artifact", "quote", "verification",
                        "payment", "event"):
            raise ValueError(f"bad evidence kind: {kind!r}")
        if len(payload) > 50 * 1024 * 1024:
            raise ValueError("evidence payload exceeds 50MB cap")
        digest = hashlib.sha256(payload).hexdigest()
        # DLP on text-like payloads: refuse secrets, store only hash + note.
        try:
            text = payload.decode("utf-8", errors="strict")
            findings = _dlp_scan(text[:100000])
            if findings and kind in ("input", "output", "event"):
                raise PermissionError(
                    f"evidence refused: secret-like content "
                    f"({[f['type'] for f in findings]}); minimize/redact first")
        except UnicodeDecodeError:
            pass  # binary: hash only, summary required
        blob_path = self._dir / digest
        if not blob_path.exists():
            blob_path.write_bytes(payload)
        ev = S.Evidence(
            evidence_id=S.new_id("ev"), kind=kind, delegation_id=delegation_id,
            contract_id=contract_id, task_id=task_id, actor=actor,
            sha256="sha256:" + digest, size_bytes=len(payload),
            summary=summary[:1000], ref=f"evidence_blobs/{digest}",
            correlation_id=correlation_id or S.new_id("corr"),
            created_at=time.time(),
        )
        self._index.put(ev.evidence_id, ev.to_dict())
        return ev

    def get(self, evidence_id: str) -> Optional[S.Evidence]:
        raw = self._index.get(evidence_id)
        return S.Evidence.from_dict(raw) if raw else None

    def blob(self, evidence: S.Evidence) -> Optional[bytes]:
        p = self._dir / evidence.sha256.replace("sha256:", "")
        return p.read_bytes() if p.exists() else None

    def verify_blob(self, evidence: S.Evidence) -> bool:
        data = self.blob(evidence)
        if data is None:
            return False
        return "sha256:" + hashlib.sha256(data).hexdigest() == evidence.sha256 \
            and len(data) == evidence.size_bytes

    def chain(self, delegation_id: str) -> List[S.Evidence]:
        out = []
        for raw in self._index.values():
            if raw.get("delegation_id") == delegation_id:
                out.append(S.Evidence.from_dict(raw))
        return sorted(out, key=lambda e: e.created_at)
