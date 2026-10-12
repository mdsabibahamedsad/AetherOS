"""Dynamic pricing models + normalization (spec section 10).

Provider-declared models: FIXED, PER_REQUEST, PER_TOKEN, PER_SECOND,
PER_ARTIFACT, PER_UNIT, TIERED, SUBSCRIPTION, CUSTOM. Normalizes to
comparable per-task estimates in a single currency. Currency conversion
is NEVER silent: explicit FX table required, missing rate => error.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

PRICING_MODELS = ("FIXED", "PER_REQUEST", "PER_TOKEN", "PER_SECOND",
                  "PER_ARTIFACT", "PER_UNIT", "TIERED", "SUBSCRIPTION",
                  "CUSTOM")


@dataclass
class PriceEstimate:
    """Comparable estimate. NEVER a settlement amount."""

    amount_minor: int
    currency: str
    model: str
    basis: str = ""          # e.g. "3 requests @ 100", "est. 2000 tokens"
    estimated: bool = True   # always True: estimates are not quotes
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FxTable:
    """Explicit currency conversion. No rate => error, never a guess."""

    def __init__(self, base: str = "USD",
                 rates: Optional[Dict[str, float]] = None) -> None:
        if not base or len(base) != 3 or not base.isupper():
            raise ValueError("base must be a 3-letter uppercase code")
        self.base = base
        self.rates: Dict[str, float] = {}
        for k, v in (rates or {}).items():
            self.set_rate(k, v)

    def set_rate(self, currency: str, per_base_unit: float) -> None:
        """Rate = units of `currency` per 1 unit of base."""
        if not currency or len(currency) != 3 or not currency.isupper():
            raise ValueError(f"bad currency: {currency!r}")
        if not isinstance(per_base_unit, (int, float)) or per_base_unit <= 0:
            raise ValueError("rate must be positive")
        self.rates[currency] = float(per_base_unit)

    def to_base_minor(self, amount_minor: int, currency: str) -> int:
        if currency == self.base:
            return int(amount_minor)
        rate = self.rates.get(currency)
        if rate is None:
            raise ValueError(
                f"no FX rate for {currency}->{self.base}: refusing silent conversion")
        return int(round(amount_minor / rate))


def _check_minor(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative int minor amount")
    return value


def normalize_price(declaration: Dict[str, Any],
                    usage: Optional[Dict[str, Any]] = None,
                    fx: Optional[FxTable] = None,
                    target_currency: str = "USD") -> PriceEstimate:
    """Normalize a provider price declaration to a comparable estimate.

    declaration: {model, currency, amount_minor|unit_minor|tiers|...}.
    usage: expected consumption {requests, tokens, seconds, artifacts,
      units} for rate-based models. CUSTOM without an estimator errors.
    """
    usage = usage or {}
    if not isinstance(declaration, dict):
        raise ValueError("price declaration must be an object")
    model = str(declaration.get("model", "")).upper()
    if model not in PRICING_MODELS:
        raise ValueError(f"unknown pricing model: {model!r}")
    currency = str(declaration.get("currency", target_currency)).upper()
    if len(currency) != 3:
        raise ValueError(f"bad currency: {currency!r}")
    warnings: List[str] = []
    basis = ""
    if model == "FIXED":
        amount = _check_minor(declaration.get("amount_minor", 0), "amount_minor")
        basis = "fixed per task"
    elif model == "PER_REQUEST":
        unit = _check_minor(declaration.get("unit_minor", 0), "unit_minor")
        n = int(usage.get("requests", 1))
        if n < 1:
            raise ValueError("usage.requests must be >= 1")
        amount = unit * n
        basis = f"{n} request(s) @ {unit}"
    elif model == "PER_TOKEN":
        unit = _check_minor(declaration.get("unit_minor", 0), "unit_minor")
        tokens = int(usage.get("tokens", 0))
        if tokens <= 0:
            raise ValueError("PER_TOKEN needs usage.tokens estimate")
        amount = unit * tokens
        basis = f"ESTIMATED {tokens} tokens @ {unit}"
        warnings.append("token usage is estimated, not measured")
    elif model == "PER_SECOND":
        unit = _check_minor(declaration.get("unit_minor", 0), "unit_minor")
        seconds = float(usage.get("seconds", 0))
        if seconds <= 0:
            raise ValueError("PER_SECOND needs usage.seconds estimate")
        import math
        amount = unit * int(math.ceil(seconds))
        basis = f"ESTIMATED {seconds}s @ {unit}/s"
        warnings.append("duration is estimated, not measured")
    elif model == "PER_ARTIFACT":
        unit = _check_minor(declaration.get("unit_minor", 0), "unit_minor")
        n = int(usage.get("artifacts", 1))
        if n < 1:
            raise ValueError("usage.artifacts must be >= 1")
        amount = unit * n
        basis = f"{n} artifact(s) @ {unit}"
    elif model == "PER_UNIT":
        unit = _check_minor(declaration.get("unit_minor", 0), "unit_minor")
        unit_name = str(declaration.get("unit_name", "unit"))
        n = int(usage.get("units", 1))
        if n < 1:
            raise ValueError("usage.units must be >= 1")
        amount = unit * n
        basis = f"{n} {unit_name}(s) @ {unit}"
    elif model == "TIERED":
        tiers = declaration.get("tiers", [])
        if not isinstance(tiers, list) or not tiers:
            raise ValueError("TIERED needs a non-empty tiers list")
        n = int(usage.get("units", usage.get("requests", 1)))
        amount = _apply_tiers(tiers, n)
        basis = f"{n} unit(s) across {len(tiers)} tier(s)"
    elif model == "SUBSCRIPTION":
        amount = _check_minor(declaration.get("amount_minor", 0), "amount_minor")
        period = str(declaration.get("period", "month"))
        basis = f"subscription per {period} (amortized share unknown)"
        warnings.append("subscription cost is NOT amortized per task here; "
                        "compare separately")
    else:  # CUSTOM
        estimator = declaration.get("estimator")
        if estimator == "quote":
            amount = _check_minor(declaration.get("amount_minor", 0), "amount_minor")
            basis = "provider quote (exact, not estimated)"
            warnings.append("quote-backed: verify via quoting engine before settlement")
        else:
            raise ValueError("CUSTOM pricing needs estimator='quote' + amount_minor")
    if currency != target_currency:
        if fx is None:
            raise ValueError(
                f"cross-currency {currency}->{target_currency} without FX table: refused")
        amount = fx.to_base_minor(amount, currency)
        warnings.append(f"converted {currency}->{target_currency} at explicit table rate")
        currency = target_currency
    return PriceEstimate(amount_minor=amount, currency=currency,
                         model=model, basis=basis, estimated=True,
                         warnings=warnings)


def _apply_tiers(tiers: List[Dict[str, Any]], n: int) -> int:
    """Marginal tier pricing: [{up_to, unit_minor}]. up_to=null => rest."""
    total = 0
    prev = 0
    remaining = n
    for tier in tiers:
        if remaining <= 0:
            break
        if not isinstance(tier, dict):
            raise ValueError("tier must be an object")
        unit = _check_minor(tier.get("unit_minor", 0), "tier.unit_minor")
        up_to = tier.get("up_to")
        if up_to is None:
            total += unit * remaining
            remaining = 0
        else:
            up_to = int(up_to)
            if up_to <= prev:
                raise ValueError("tiers must ascend")
            take = min(remaining, up_to - prev)
            total += unit * take
            remaining -= take
            prev = up_to
    if remaining > 0:
        raise ValueError("tier schedule does not cover requested units")
    return total
