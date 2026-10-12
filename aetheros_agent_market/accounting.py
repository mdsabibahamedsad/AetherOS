"""Cost accounting: estimated vs actual with variance (spec section 40).

Tracks agent/model/tool/network/execution/verification costs, refunds,
fees. NEVER claims actual cost before settlement: actuals come only
from captured/refunded ledger entries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas as S
from .ledger import Ledger
from .store import JsonStore


class CostAccounting:
    def __init__(self, home: Path, ledger: Optional[Ledger] = None) -> None:
        self._estimates = JsonStore(Path(home) / "cost_estimates.json")
        self._ledger = ledger or Ledger(Path(home) / "ledger.jsonl")

    def record_estimate(self, delegation_id: str, breakdown: Dict[str, int],
                        currency: str = "USD") -> Dict[str, Any]:
        """breakdown: {agent,model,tool,network,execution,verification} minor units."""
        S.check_currency(currency)
        total = 0
        clean: Dict[str, int] = {}
        for k, v in breakdown.items():
            S.check_amount_minor(v)
            clean[k] = v
            total += v
        rec = {"delegation_id": delegation_id, "breakdown": clean,
               "total_minor": total, "currency": currency}
        self._estimates.put(delegation_id, rec)
        return rec

    def actuals(self, delegation_id: str) -> Dict[str, Any]:
        """Actuals derived ONLY from settled ledger entries."""
        captured = 0
        refunded = 0
        settled = False
        currency = ""
        for e in self._ledger.entries(limit=100000):
            if e.delegation_id != delegation_id:
                continue
            currency = currency or e.currency
            if e.event == "CAPTURED":
                captured += e.amount_minor
                settled = True  # state-based: free tasks settle at 0
            elif e.event == "REFUNDED":
                refunded += e.amount_minor
                settled = True
        return {"delegation_id": delegation_id, "captured_minor": captured,
                "refunded_minor": refunded, "net_minor": captured - refunded,
                "currency": currency or "USD", "settled": settled}

    def variance(self, delegation_id: str) -> Dict[str, Any]:
        est = self._estimates.get(delegation_id) or {"total_minor": 0, "currency": "USD"}
        act = self.actuals(delegation_id)
        return {"delegation_id": delegation_id,
                "estimated_minor": est["total_minor"],
                "actual_minor": act["net_minor"] if act["settled"] else None,
                "variance_minor": (act["net_minor"] - est["total_minor"])
                if act["settled"] else None,
                "settled": act["settled"],
                "currency": est.get("currency", "USD")}

    def summary(self) -> Dict[str, Any]:
        spent = refunded = 0
        currency = "USD"
        n_captured = n_refunded = 0
        for e in self._ledger.entries(limit=100000):
            currency = e.currency or currency
            if e.event == "CAPTURED":
                spent += e.amount_minor
                n_captured += 1
            elif e.event == "REFUNDED":
                refunded += e.amount_minor
                n_refunded += 1
        return {"total_spent_minor": spent, "total_refunded_minor": refunded,
                "net_minor": spent - refunded, "captures": n_captured,
                "refunds": n_refunded, "currency": currency}
