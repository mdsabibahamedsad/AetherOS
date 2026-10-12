"""Development-only economy simulation (spec section 67).

SIMULATION data is visibly marked at every layer, stored in an
ISOLATED directory, and can NEVER touch the production ledger,
budgets, contracts, or reputation stores. Any attempt to point the
simulator at the production home raises.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas as S

SIMULATION_MARK = "SIMULATION"


def simulation_home(base: Optional[Path] = None) -> Path:
    from .store import market_home
    home = Path(base) if base else (market_home() / "simulation")
    home.mkdir(parents=True, exist_ok=True)
    marker = home / "SIMULATION_MARKER"
    if not marker.exists():
        marker.write_text(f"{SIMULATION_MARK}: development fixtures only. "
                          "Never production data.\n", encoding="utf-8")
    return home


def _guard(home: Path) -> None:
    from .store import market_home
    if Path(home).resolve() == market_home().resolve():
        raise PermissionError("simulation refused: production home is not a simulation target")
    if (Path(home) / "ledger.jsonl").exists() and not (Path(home) / "SIMULATION_MARKER").exists():
        raise PermissionError("simulation refused: target looks like a production store")


class MarketSimulator:
    """Deterministic, seeded fixture economy for UI/dev testing."""

    def __init__(self, home: Optional[Path] = None, seed: int = 7) -> None:
        self.home = simulation_home(home)
        _guard(self.home)
        self.seed = seed

    def fixture_agents(self, n: int = 5) -> List[Dict[str, Any]]:
        import random
        rng = random.Random(self.seed)
        out = []
        for i in range(n):
            out.append({
                "identity_id": f"{SIMULATION_MARK}-identity-{i}",
                "agent_id": f"{SIMULATION_MARK}-agent-{i}",
                "display_name": f"{SIMULATION_MARK} Agent {i}",
                "issuer": SIMULATION_MARK,
                "verification_status": "unverified",
                "price_minor": rng.choice([0, 100, 500, 2000]),
                "currency": "USD",
                "reliability": round(rng.uniform(0.5, 0.99), 2),
                "latency_ms": rng.choice([200, 800, 2500]),
                "simulation": True,
            })
        return out

    def fixture_quote(self, agent_price_minor: int) -> Dict[str, Any]:
        return {"quote_id": f"{SIMULATION_MARK}-quote",
                "price_minor": agent_price_minor, "currency": "USD",
                "simulation": True, "created_at": time.time()}

    def ledger(self) -> List[Dict[str, Any]]:
        """The simulator has NO ledger access: returns a marked empty view."""
        return [{"simulation": True, "note": "simulated economy keeps no production ledger"}]
