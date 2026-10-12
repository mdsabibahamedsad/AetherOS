"""Audit trail for the memory fabric.

An append-only, tamper-evident audit log of memory operations.  Each record
carries an HMAC over the previous record's hash, so retroactive modification
of the log is detectable.  The fabric's CLI/status surfaces can inspect it.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryAudit:
    """Append-only, hash-chained audit log."""

    LOG_NAME = "audit.jsonl"

    def __init__(
        self,
        root: Optional[Path] = None,
        *,
        enabled: bool = True,
        max_entries: int = 10000,
        secret: str = "",
    ) -> None:
        self._root = Path(root) if root else None
        self.enabled = enabled
        self.max_entries = max_entries
        # A per-install secret gives light tamper-evidence.  Tests inject one.
        self._secret = secret or "aetheros-memory-audit"
        self._lock = threading.RLock()
        self._last_hash = "GENESIS"
        self._entries: List[Dict[str, Any]] = []

    def _log_path(self) -> Path:
        if self._root is None:
            raise RuntimeError("audit root not set; call initialize() first")
        return self._root / self.LOG_NAME

    def initialize(self, root: Optional[Path] = None) -> None:
        if root is not None:
            self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        if self._log_path().exists():
            self._load_existing()

    def _chain_hash(self, prev_hash: str, payload_json: str) -> str:
        digest = hmac.new(
            self._secret.encode("utf-8"),
            f"{prev_hash}\n{payload_json}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return digest

    def record(self, *, operation: str, entry_id: str = "", actor: str = "",
               detail: Dict[str, Any] = None) -> None:
        if not self.enabled:
            return
        with self._lock:
            payload = {
                "ts": time.time(),
                "operation": operation,
                "entry_id": entry_id,
                "actor": actor,
                "detail": detail or {},
            }
            payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            record = {
                **payload,
                "prev_hash": self._last_hash,
                "hash": self._chain_hash(self._last_hash, payload_json),
            }
            self._last_hash = record["hash"]
            self._entries.append(record)
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[-self.max_entries:]
            self._flush([record])

    def _flush(self, records: List[Dict[str, Any]]) -> None:
        try:
            with open(self._log_path(), "a", encoding="utf-8") as fh:
                for r in records:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _load_existing(self) -> None:
        try:
            lines = self._log_path().read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        prev = "GENESIS"
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("prev_hash") == prev:
                self._last_hash = record.get("hash", self._last_hash)
                self._entries.append(record)
                prev = record.get("hash", prev)
            else:
                # Chain broken -> tamper detected.  Stop, mark flag.
                self._entries.append({**record, "_tamper": True})
                break

    def entries(self, *, operation: str = "", limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            selected = self._entries
            if operation:
                selected = [e for e in selected if e.get("operation") == operation]
            return list(selected[-limit:])

    def verify_chain(self) -> bool:
        """Re-verify the hash chain of the on-disk log."""
        try:
            lines = self._log_path().read_text(encoding="utf-8").splitlines()
        except OSError:
            return True
        prev = "GENESIS"
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return False
            if record.get("prev_hash") != prev:
                return False
            payload = {k: v for k, v in record.items() if k not in ("prev_hash", "hash")}
            payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            expected = self._chain_hash(prev, payload_json)
            if record.get("hash") != expected:
                return False
            prev = record.get("hash", prev)
        return True

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            ops: Dict[str, int] = {}
            for e in self._entries:
                ops[e.get("operation", "?")] = ops.get(e.get("operation", "?"), 0) + 1
            return {
                "entries": len(self._entries),
                "operations": ops,
                "chain_valid": self.verify_chain(),
                "enabled": self.enabled,
            }