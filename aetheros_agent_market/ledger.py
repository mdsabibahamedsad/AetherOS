"""Append-only economic ledger (spec sections 39 + 92 + 93 + 119).

Hash-chained JSONL: every entry commits to the previous hash.
Corrections are compensating entries (ADJUSTED), never edits.
Corruption detection verifies the chain; on mismatch the marketplace
enters safe mode rather than silently repairing financial history.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas as S

GENESIS_PREV = "GENESIS"


class Ledger:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("", encoding="utf-8")

    def _read_all(self) -> List[Dict[str, Any]]:
        out = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                out.append({"_corrupt_line": line[:200]})
        return out

    def head_hash(self) -> str:
        entries = self._read_all()
        if not entries:
            return GENESIS_PREV
        last = entries[-1]
        return str(last.get("entry_hash", "MISSING"))

    def append(self, event: str, transaction_id: str = "",
               contract_id: str = "", delegation_id: str = "",
               task_id: str = "", agent_id: str = "",
               amount_minor: int = 0, currency: str = "USD",
               idempotency_key: str = "", note: str = "") -> S.LedgerEntry:
        if event not in S.LEDGER_EVENTS:
            raise ValueError(f"bad ledger event: {event!r}")
        S.check_amount_minor(amount_minor)
        if currency:
            S.check_currency(currency)
        # Idempotency: same key returns existing entry (no duplicate settlement).
        if idempotency_key:
            for raw in self._read_all():
                if raw.get("idempotency_key") == idempotency_key and raw.get("event") == event:
                    return S.LedgerEntry.from_dict(raw)
        entry = S.LedgerEntry(
            entry_id=S.new_id("ledger"), event=event,
            transaction_id=transaction_id, contract_id=contract_id,
            delegation_id=delegation_id, task_id=task_id, agent_id=agent_id,
            amount_minor=amount_minor, currency=currency,
            idempotency_key=idempotency_key, prev_hash=self.head_hash(),
            note=note[:500], created_at=time.time(),
        )
        entry.entry_hash = "sha256:" + hashlib.sha256(entry.canonical_bytes()).hexdigest()
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), sort_keys=True) + "\n")
        return entry

    def adjust(self, original_entry_id: str, amount_delta_minor: int,
               reason: str, **refs: str) -> S.LedgerEntry:
        """Compensating entry. Signed delta allowed here only (corrections)."""
        if not isinstance(amount_delta_minor, int) or isinstance(amount_delta_minor, bool):
            raise ValueError("amount delta must be int")
        # LedgerEntry requires non-negative amounts; encode direction in note
        # + a follow-up entry pair. Keep it simple and explicit:
        direction = "credit" if amount_delta_minor >= 0 else "debit"
        return self.append(
            "ADJUSTED", note=f"adjusts {original_entry_id} {direction} "
                             f"{abs(amount_delta_minor)}: {reason}"[:500],
            amount_minor=abs(amount_delta_minor),
            transaction_id=refs.get("transaction_id", ""),
            contract_id=refs.get("contract_id", ""),
            delegation_id=refs.get("delegation_id", ""),
            task_id=refs.get("task_id", ""),
            agent_id=refs.get("agent_id", ""),
            currency=refs.get("currency", "USD"),
            idempotency_key=refs.get("idempotency_key", S.new_id("idem")),
        )

    def verify_chain(self) -> Dict[str, Any]:
        """Returns {ok, entries, first_bad}. Deterministic corruption check."""
        entries = self._read_all()
        prev = GENESIS_PREV
        for i, raw in enumerate(entries):
            if "_corrupt_line" in raw:
                return {"ok": False, "entries": len(entries), "first_bad": i,
                        "reason": "unparsable line"}
            try:
                entry = S.LedgerEntry.from_dict(raw)
            except ValueError as e:
                return {"ok": False, "entries": len(entries), "first_bad": i,
                        "reason": f"schema: {e}"}
            if entry.prev_hash != prev:
                return {"ok": False, "entries": len(entries), "first_bad": i,
                        "reason": "prev_hash mismatch (tamper or corruption)"}
            recomputed = "sha256:" + hashlib.sha256(entry.canonical_bytes()).hexdigest()
            if recomputed != entry.entry_hash:
                return {"ok": False, "entries": len(entries), "first_bad": i,
                        "reason": "entry_hash mismatch (tamper or corruption)"}
            prev = entry.entry_hash
        return {"ok": True, "entries": len(entries), "first_bad": -1, "reason": ""}

    def entries(self, transaction_id: str = "",
                limit: int = 500) -> List[S.LedgerEntry]:
        out = []
        for raw in reversed(self._read_all()):
            if "_corrupt_line" in raw:
                continue
            try:
                e = S.LedgerEntry.from_dict(raw)
            except ValueError:
                continue
            if transaction_id and e.transaction_id != transaction_id:
                continue
            out.append(e)
            if len(out) >= limit:
                break
        return out
