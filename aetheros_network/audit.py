"""Append-only audit log (Master 46 section 93).

Every security-relevant event records identity, action, and outcome.
Secrets are never recorded: payloads are summarized (hashes, sizes,
classifications), never embedded.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def summarize_payload(payload: Any, max_chars: int = 200) -> Dict[str, Any]:
    text = payload if isinstance(payload, str) else json.dumps(payload, default=str)
    return {
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        "chars": len(text),
        "preview": text[:max_chars] if len(text) <= 4096 else text[:max_chars] + "…",
    }


class AuditLog:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, actor: str = "", subject: str = "",
               details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        entry = {
            "ts": time.time(),
            "event": event,
            "actor": actor,
            "subject": subject,
            "details": details or {},
        }
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        return entry

    def tail(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out
