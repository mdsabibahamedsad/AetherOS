"""Budget engine (spec sections 15 + 16 + 65).

Scopes: global|user|workspace|project|automation|agent|task|contract.
Limits: daily/weekly/monthly/per-task/per-agent + approval threshold.
Risk classes FREE/LOW/MEDIUM/HIGH/CRITICAL map deterministically to
NO/APPROVAL tiers. The LLM never decides payment approval (spec 10, 16).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import schemas as S
from .store import JsonStore

# Risk classes by amount (minor units). Defaults; tighten via budgets.
RISK_TIERS = (
    ("FREE", 0),
    ("LOW_COST", 500),        # <= $5
    ("MEDIUM_COST", 5000),    # <= $50
    ("HIGH_COST", 50000),     # <= $500
    ("CRITICAL_COST", None),  # above
)

APPROVAL_TIERS = ("NO_APPROVAL", "AUTO_APPROVAL", "CONDITIONAL_APPROVAL", "HUMAN_APPROVAL")


def risk_class(amount_minor: int) -> str:
    S.check_amount_minor(amount_minor)
    if amount_minor == 0:
        return "FREE"
    if amount_minor <= 500:
        return "LOW_COST"
    if amount_minor <= 5000:
        return "MEDIUM_COST"
    if amount_minor <= 50000:
        return "HIGH_COST"
    return "CRITICAL_COST"


class BudgetManager:
    def __init__(self, home: Path) -> None:
        self._budgets = JsonStore(Path(home) / "budgets.json")
        # reservations: {reservation_id: {budget_key, amount_minor, at}}
        self._reservations = JsonStore(Path(home) / "reservations.json")

    # -- budgets ----------------------------------------------------------
    def set_budget(self, budget: S.Budget) -> S.Budget:
        if not budget.budget_id:
            budget.budget_id = S.new_id("budget")
        S.check_currency(budget.currency)
        for attr in ("daily_limit_minor", "weekly_limit_minor", "monthly_limit_minor",
                     "per_task_limit_minor", "per_agent_limit_minor",
                     "approval_threshold_minor", "auto_approve_limit_minor",
                     "spent_minor", "reserved_minor"):
            S.check_amount_minor(getattr(budget, attr))
        key = f"{budget.scope}:{budget.scope_id}"
        self._budgets.put(key, budget.to_dict())
        return budget

    def get_budget(self, scope: str, scope_id: str = "") -> Optional[S.Budget]:
        raw = self._budgets.get(f"{scope}:{scope_id}")
        return S.Budget.from_dict(raw) if raw else None

    def all_budgets(self) -> List[S.Budget]:
        return [S.Budget.from_dict(r) for r in self._budgets.values()]

    # -- evaluation ---------------------------------------------------------
    def approval_tier(self, amount_minor: int,
                      budget: Optional[S.Budget] = None) -> str:
        """Deterministic policy: risk class + budget thresholds.

        - amount 0 => NO_APPROVAL only if provider is free AND policy allows;
          still recorded. (Free tasks are ledger events, not invisible.)
        - amount <= auto_approve_limit => AUTO_APPROVAL
        - amount <= approval_threshold => CONDITIONAL_APPROVAL
        - above => HUMAN_APPROVAL. CRITICAL_COST always HUMAN_APPROVAL.
        """
        risk = risk_class(amount_minor)
        if risk == "CRITICAL_COST":
            return "HUMAN_APPROVAL"
        if amount_minor == 0:
            return "NO_APPROVAL"
        if budget is None:
            return "HUMAN_APPROVAL"  # no budget configured => human decides
        if amount_minor <= budget.auto_approve_limit_minor and budget.auto_approve_limit_minor:
            return "AUTO_APPROVAL"
        if amount_minor <= budget.approval_threshold_minor or not budget.approval_threshold_minor:
            return "CONDITIONAL_APPROVAL" if budget.approval_threshold_minor else "HUMAN_APPROVAL"
        return "HUMAN_APPROVAL"

    def check_spend(self, amount_minor: int, scope: str,
                    scope_id: str = "") -> Tuple[bool, str]:
        """Enforce limits across ALL applicable scopes (global + specific).

        Returns (allowed, reason). Economic abuse controls (spec 65):
        per-task/per-agent caps, daily/weekly/monthly caps.
        """
        keys = [f"global:", f"{scope}:{scope_id}"]
        if scope != "user":
            keys.append("user:")
        for key in keys:
            raw = self._budgets.get(key)
            if raw is None:
                continue
            b = S.Budget.from_dict(raw)
            if b.per_task_limit_minor and amount_minor > b.per_task_limit_minor:
                return False, f"exceeds per-task limit {b.per_task_limit_minor} ({key})"
            if scope in ("agent", "task") and b.per_agent_limit_minor \
                    and amount_minor > b.per_agent_limit_minor:
                return False, f"exceeds per-agent limit ({key})"
            for window, limit in (("daily", b.daily_limit_minor),
                                  ("weekly", b.weekly_limit_minor),
                                  ("monthly", b.monthly_limit_minor)):
                if limit and b.spent_minor + b.reserved_minor + amount_minor > limit:
                    return False, f"would exceed {window} limit {limit} ({key})"
        return True, "within budget"

    def _applicable_keys(self, scope: str, scope_id: str) -> List[str]:
        keys = [f"global:", f"{scope}:{scope_id}"]
        if scope != "user":
            keys.append("user:")
        # De-duplicate while preserving order.
        return list(dict.fromkeys(keys))

    # -- reservations (authorize-hold) ---------------------------------------
    def reserve(self, amount_minor: int, scope: str,
                scope_id: str = "") -> str:
        ok, reason = self.check_spend(amount_minor, scope, scope_id)
        if not ok:
            raise PermissionError(f"budget denied: {reason}")
        keys = self._applicable_keys(scope, scope_id)
        for key in keys:
            raw = self._budgets.get(key)
            if raw is not None:
                b = S.Budget.from_dict(raw)
                b.reserved_minor += amount_minor
                self._budgets.put(key, b.to_dict())
        rid = S.new_id("rsv")
        self._reservations.put(rid, {"reservation_id": rid,
                                     "budget_keys": keys,
                                     "amount_minor": amount_minor,
                                     "at": time.time()})
        return rid

    def _apply_reservation(self, reservation_id: str, settle: bool) -> bool:
        rec = self._reservations.get(reservation_id)
        if rec is None:
            return False
        keys = rec.get("budget_keys") or ([rec["budget_key"]]
                                          if rec.get("budget_key") else [])
        for key in keys:
            raw = self._budgets.get(key)
            if raw is not None:
                b = S.Budget.from_dict(raw)
                b.reserved_minor = max(0, b.reserved_minor - rec["amount_minor"])
                if settle:
                    b.spent_minor += rec["amount_minor"]
                self._budgets.put(key, b.to_dict())
        return self._reservations.delete(reservation_id)

    def release(self, reservation_id: str) -> bool:
        return self._apply_reservation(reservation_id, settle=False)

    def settle(self, reservation_id: str) -> bool:
        """Convert a reservation into spent (called on capture)."""
        return self._apply_reservation(reservation_id, settle=True)

    def usage(self, scope: str, scope_id: str = "") -> Dict[str, Any]:
        raw = self._budgets.get(f"{scope}:{scope_id}")
        if raw is None:
            return {"configured": False}
        b = S.Budget.from_dict(raw)
        return {"configured": True, "spent_minor": b.spent_minor,
                "reserved_minor": b.reserved_minor, "currency": b.currency,
                "limits": {"daily": b.daily_limit_minor, "weekly": b.weekly_limit_minor,
                           "monthly": b.monthly_limit_minor,
                           "per_task": b.per_task_limit_minor,
                           "per_agent": b.per_agent_limit_minor}}
