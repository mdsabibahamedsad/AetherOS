"""Rollout controller (P9, P68-71): staged canary rollout with
threshold-triggered automatic rollback + post-rollback validation.

Feature flags are read from a plain config mapping (P9) — the existing
config.yaml is the flag source; no new flag subsystem is invented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from agent.quality.models import RolloutStage, RolloutState


@dataclass
class RolloutPolicy:
    """Explicit, configurable thresholds (P21 doctrine — nothing hard-coded
    as universal). Breaching ANY monitor at a stage halts and rolls back."""

    stages: List[RolloutStage] = field(default_factory=lambda: [
        RolloutStage.CANARY, RolloutStage.MEDIUM, RolloutStage.FULL,
    ])
    monitors: Dict[str, float] = field(default_factory=lambda: {
        "error_rate": 0.05,
        "latency_p95_ms": 2000.0,
        "task_success_rate": 0.90,
        "security_events": 0.0,
    })
    higher_is_better: frozenset = frozenset({"task_success_rate"})


class RolloutController:
    def __init__(self, policy: Optional[RolloutPolicy] = None,
                 flags: Optional[Dict[str, Any]] = None):
        self.policy = policy or RolloutPolicy()
        self.flags = dict(flags or {})     # P9: config-driven feature flags
        self.state: Optional[RolloutState] = None
        self.events: List[str] = []

    # -- feature flags (P9) -------------------------------------------------------

    def flag_enabled(self, name: str, *, percent_env: int = 100) -> bool:
        raw = self.flags.get(name, False)
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            # fractions (0.5) and percents (50) both mean "50% of envs";
            # enabled when this env's bucket falls under the rollout share
            threshold = float(raw) * 100 if raw <= 1 else float(raw)
            return percent_env < threshold
        return bool(raw)

    # -- rollout (P68-70) ------------------------------------------------------------

    def start(self, version: str) -> RolloutState:
        self.state = RolloutState(version=version, stage=RolloutStage.CANARY)
        self.events.append(f"rollout started: {version} @ canary")
        return self.state

    def advance(self, observed: Dict[str, float]) -> RolloutState:
        """Evaluate monitors; advance stage or auto-rollback (P70)."""
        assert self.state is not None, "start() first"
        breach = self._breach(observed)
        if breach:
            self.events.append(
                f"threshold breached at {self.state.stage.value}: {breach}")
            return self.rollback(observed, reason=breach)
        order = self.policy.stages
        idx = order.index(self.state.stage) if self.state.stage in order else -1
        if idx + 1 < len(order):
            self.state.stage = order[idx + 1]
            self.events.append(f"advanced to {self.state.stage.value}")
        else:
            self.events.append("already at full rollout")
        return self.state

    def _breach(self, observed: Dict[str, float]) -> str:
        for metric, limit in self.policy.monitors.items():
            if metric not in observed:
                continue
            value = observed[metric]
            if metric in self.policy.higher_is_better:
                if value < limit:
                    return f"{metric}={value} below {limit}"
            elif value > limit:
                return f"{metric}={value} above {limit}"
        return ""

    # -- rollback (P70-71) ---------------------------------------------------------------

    def rollback(self, observed: Dict[str, float], *,
                 reason: str = "manual") -> RolloutState:
        assert self.state is not None
        self.state.breached = bool(reason and reason != "manual")
        self.state.rolled_back = True
        self.state.stage = RolloutStage.NONE
        self.events.append(f"ROLLBACK: {reason}; restored known-good version")
        # P71 validation checklist
        self.state.validation = self.validate_rollback(observed)
        return self.state

    def validate_rollback(self, observed: Dict[str, float]) -> Dict[str, bool]:
        """P71 — service health, data integrity, task recovery, security."""
        return {
            "service_health": observed.get("error_rate", 0.0) <=
            self.policy.monitors.get("error_rate", 0.05),
            "data_integrity": observed.get("data_integrity_failures", 0) == 0,
            "task_recovery": observed.get("task_success_rate", 0.0) >=
            self.policy.monitors.get("task_success_rate", 0.90),
            "security_state": observed.get("security_events", 0) == 0,
        }
