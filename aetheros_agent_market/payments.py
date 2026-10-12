"""Payment abstraction (spec sections 13 + 17).

Abstract economic layer — NO hardcoded payment provider. Interface:
quote/authorize/capture/refund/void/getTransaction/reconcile.
Implementations: NoPayment, InternalCredits, OrganizationBudget.
External providers integrate via PaymentProvider (see sdk/).

Lifecycle: authorize -> execute -> verify -> capture; on verification
failure -> refund/void/dispute. Escrow is an ABSTRACTION claimed only
when a provider implements conditional settlement (none ships one, so
we document PLANNED and enforce authorize-before-capture ordering).
"""

from __future__ import annotations

import abc
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas as S
from .store import JsonStore


class PaymentError(Exception):
    pass


class PaymentProvider(abc.ABC):
    """Provider interface (spec 13). All amounts minor units."""

    name: str = "abstract"
    supports_escrow: bool = False

    @abc.abstractmethod
    def quote(self, service_id: str, inputs: Dict[str, Any]) -> S.Quote: ...
    @abc.abstractmethod
    def authorize(self, quote: S.Quote, idempotency_key: str) -> S.Transaction: ...
    @abc.abstractmethod
    def capture(self, transaction_id: str, idempotency_key: str) -> S.Transaction: ...
    @abc.abstractmethod
    def refund(self, transaction_id: str, amount_minor: Optional[int],
               idempotency_key: str, reason: str = "") -> S.Transaction: ...
    @abc.abstractmethod
    def void(self, transaction_id: str, idempotency_key: str) -> S.Transaction: ...
    @abc.abstractmethod
    def get_transaction(self, transaction_id: str) -> Optional[S.Transaction]: ...
    @abc.abstractmethod
    def reconcile(self) -> Dict[str, Any]: ...


class _BaseProvider(PaymentProvider):
    """Idempotent in-memory provider core shared by built-ins."""

    def __init__(self, home: Path, name: str) -> None:
        self.name = name
        self._tx = JsonStore(Path(home) / f"tx_{name}.json")
        self._idem: Dict[str, str] = {}  # idempotency_key -> transaction_id
        self._rebuild_idem()

    def _rebuild_idem(self) -> None:
        for raw in self._tx.values():
            if raw.get("idempotency_key"):
                self._idem.setdefault(raw["idempotency_key"], raw["transaction_id"])

    def _save(self, tx: S.Transaction) -> S.Transaction:
        tx.updated_at = time.time()
        self._tx.put(tx.transaction_id, tx.to_dict())
        if tx.idempotency_key:
            self._idem.setdefault(tx.idempotency_key, tx.transaction_id)
        return tx

    def _by_idem(self, key: str) -> Optional[S.Transaction]:
        tid = self._idem.get(key)
        if tid:
            raw = self._tx.get(tid)
            if raw:
                return S.Transaction.from_dict(raw)
        return None

    def get_transaction(self, transaction_id: str) -> Optional[S.Transaction]:
        raw = self._tx.get(transaction_id)
        return S.Transaction.from_dict(raw) if raw else None

    def transactions_for_contract(self, contract_id: str) -> List[S.Transaction]:
        out = []
        for raw in self._tx.values():
            if raw.get("contract_id") == contract_id:
                out.append(S.Transaction.from_dict(raw))
        return out

    def reconcile(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        totals: Dict[str, int] = {}
        for raw in self._tx.values():
            st = raw.get("status", "?")
            counts[st] = counts.get(st, 0) + 1
            totals[raw.get("currency", "?")] = totals.get(raw.get("currency", "?"), 0) + raw.get("amount_minor", 0)
        return {"provider": self.name, "counts": counts, "totals_minor": totals}


class NoPaymentProvider(_BaseProvider):
    """Free tasks. Still creates idempotent zero-amount transactions so
    free executions are auditable, never invisible (spec 16)."""

    def __init__(self, home: Path) -> None:
        super().__init__(home, "none")

    def quote(self, service_id: str, inputs: Dict[str, Any]) -> S.Quote:
        return S.Quote(quote_id=S.new_id("quote"), service_id=service_id,
                       agent_id=str(inputs.get("agent_id", "")),
                       price_minor=0, currency="USD",
                       idempotency_key=S.new_id("idem"))

    def authorize(self, quote: S.Quote, idempotency_key: str) -> S.Transaction:
        if quote.total_minor != 0:
            raise PaymentError("NoPayment cannot authorize a non-zero quote")
        existing = self._by_idem(idempotency_key)
        if existing:
            return existing
        return self._save(S.Transaction(
            transaction_id=S.new_id("tx"), contract_id=quote.contract_id,
            agent_id=quote.agent_id, provider="none", amount_minor=0,
            currency=quote.currency, status="authorized",
            idempotency_key=idempotency_key))

    def capture(self, transaction_id: str, idempotency_key: str) -> S.Transaction:
        tx = self.get_transaction(transaction_id)
        if tx is None:
            raise PaymentError("unknown transaction")
        existing = self._by_idem(f"capture:{idempotency_key}")
        if existing and existing.status == "captured":
            return existing
        if tx.status != "authorized":
            raise PaymentError(f"cannot capture from {tx.status}")
        tx.status = "captured"
        tx.idempotency_key = tx.idempotency_key  # keep original key
        saved = self._save(tx)
        self._idem[f"capture:{idempotency_key}"] = saved.transaction_id
        return saved

    def refund(self, transaction_id: str, amount_minor: Optional[int],
               idempotency_key: str, reason: str = "") -> S.Transaction:
        tx = self.get_transaction(transaction_id)
        if tx is None:
            raise PaymentError("unknown transaction")
        if tx.amount_minor != 0:
            raise PaymentError("NoPayment has nothing to refund")
        tx.status = "refunded"
        return self._save(tx)

    def void(self, transaction_id: str, idempotency_key: str) -> S.Transaction:
        tx = self.get_transaction(transaction_id)
        if tx is None:
            raise PaymentError("unknown transaction")
        if tx.status not in ("quoted", "authorized"):
            raise PaymentError(f"cannot void from {tx.status}")
        tx.status = "voided"
        return self._save(tx)


class InternalCreditsProvider(_BaseProvider):
    """Dev/test credit pool with real balance accounting. Balances are
    local integers — NOT real money, NOT a payment rail (documented)."""

    def __init__(self, home: Path, initial_minor: int = 0) -> None:
        super().__init__(home, "credits")
        self._bal = JsonStore(Path(home) / "credits_balance.json")
        if self._bal.get("balance_minor") is None:
            self._bal.put("balance_minor", initial_minor)

    def balance(self) -> int:
        return int(self._bal.get("balance_minor") or 0)

    def top_up(self, amount_minor: int) -> int:
        S.check_amount_minor(amount_minor)
        bal = self.balance() + amount_minor
        self._bal.put("balance_minor", bal)
        return bal

    def quote(self, service_id: str, inputs: Dict[str, Any]) -> S.Quote:
        raise PaymentError("credits provider does not issue quotes; use the quoting engine")

    def authorize(self, quote: S.Quote, idempotency_key: str) -> S.Transaction:
        existing = self._by_idem(idempotency_key)
        if existing:
            return existing
        if quote.total_minor > self.balance():
            raise PaymentError(f"insufficient credits: need {quote.total_minor}, have {self.balance()}")
        self._bal.put("balance_minor", self.balance() - quote.total_minor)
        return self._save(S.Transaction(
            transaction_id=S.new_id("tx"), contract_id=quote.contract_id,
            agent_id=quote.agent_id, provider="credits",
            amount_minor=quote.total_minor, currency=quote.currency,
            status="authorized", idempotency_key=idempotency_key))

    def capture(self, transaction_id: str, idempotency_key: str) -> S.Transaction:
        tx = self.get_transaction(transaction_id)
        if tx is None:
            raise PaymentError("unknown transaction")
        existing = self._by_idem(f"capture:{idempotency_key}")
        if existing is not None and existing.transaction_id == transaction_id \
                and existing.status == "captured":
            return existing  # idempotent replay: no balance movement
        if tx.status != "authorized":
            raise PaymentError(f"cannot capture from {tx.status}")
        tx.status = "captured"
        saved = self._save(tx)
        self._idem[f"capture:{idempotency_key}"] = saved.transaction_id
        return saved

    def refund(self, transaction_id: str, amount_minor: Optional[int],
               idempotency_key: str, reason: str = "") -> S.Transaction:
        tx = self.get_transaction(transaction_id)
        if tx is None:
            raise PaymentError("unknown transaction")
        if tx.status not in ("authorized", "captured"):
            raise PaymentError(f"cannot refund from {tx.status}")
        amt = tx.amount_minor if amount_minor is None else amount_minor
        S.check_amount_minor(amt)
        if amt > tx.amount_minor:
            raise PaymentError("refund exceeds captured amount")
        self._bal.put("balance_minor", self.balance() + amt)
        tx.status = "refunded" if amt == tx.amount_minor else tx.status
        return self._save(tx)

    def void(self, transaction_id: str, idempotency_key: str) -> S.Transaction:
        tx = self.get_transaction(transaction_id)
        if tx is None:
            raise PaymentError("unknown transaction")
        if tx.status != "authorized":
            raise PaymentError(f"cannot void from {tx.status}")
        self._bal.put("balance_minor", self.balance() + tx.amount_minor)
        tx.status = "voided"
        return self._save(tx)


class OrganizationBudgetProvider(_BaseProvider):
    """Charges against an OrganizationBudget envelope (no real rail).

    Real enforcement comes from BudgetManager limits; this provider
    records the transaction and reservation refs deterministically.
    """

    def __init__(self, home: Path) -> None:
        super().__init__(home, "org_budget")

    def quote(self, service_id: str, inputs: Dict[str, Any]) -> S.Quote:
        raise PaymentError("org budget provider does not issue quotes; use the quoting engine")

    def authorize(self, quote: S.Quote, idempotency_key: str) -> S.Transaction:
        existing = self._by_idem(idempotency_key)
        if existing:
            return existing
        return self._save(S.Transaction(
            transaction_id=S.new_id("tx"), contract_id=quote.contract_id,
            agent_id=quote.agent_id, provider="org_budget",
            amount_minor=quote.total_minor, currency=quote.currency,
            status="authorized", idempotency_key=idempotency_key))

    def capture(self, transaction_id: str, idempotency_key: str) -> S.Transaction:
        tx = self.get_transaction(transaction_id)
        if tx is None:
            raise PaymentError("unknown transaction")
        existing = self._by_idem(f"capture:{idempotency_key}")
        if existing is not None and existing.transaction_id == transaction_id \
                and existing.status == "captured":
            return existing  # idempotent replay
        if tx.status != "authorized":
            raise PaymentError(f"cannot capture from {tx.status}")
        tx.status = "captured"
        saved = self._save(tx)
        self._idem[f"capture:{idempotency_key}"] = saved.transaction_id
        return saved

    def refund(self, transaction_id: str, amount_minor: Optional[int],
               idempotency_key: str, reason: str = "") -> S.Transaction:
        tx = self.get_transaction(transaction_id)
        if tx is None:
            raise PaymentError("unknown transaction")
        if tx.status not in ("authorized", "captured"):
            raise PaymentError(f"cannot refund from {tx.status}")
        tx.status = "refunded"
        return self._save(tx)

    def void(self, transaction_id: str, idempotency_key: str) -> S.Transaction:
        tx = self.get_transaction(transaction_id)
        if tx is None:
            raise PaymentError("unknown transaction")
        if tx.status != "authorized":
            raise PaymentError(f"cannot void from {tx.status}")
        tx.status = "voided"
        return self._save(tx)


PROVIDERS: Dict[str, str] = {
    "none": "NoPaymentProvider (free, auditable)",
    "credits": "InternalCreditsProvider (local test credits, NOT real money)",
    "org_budget": "OrganizationBudgetProvider (budget envelope, no real rail)",
}


def get_provider(name: str, home: Path, **kwargs) -> PaymentProvider:
    if name == "none":
        return NoPaymentProvider(home)
    if name == "credits":
        return InternalCreditsProvider(home, **kwargs)
    if name == "org_budget":
        return OrganizationBudgetProvider(home)
    raise ValueError(f"unknown payment provider: {name!r}. "
                     f"Available: {sorted(PROVIDERS)}. External providers plug in via PaymentProvider.")
