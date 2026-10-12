"""Feature flags, emergency stop, kill switch, safe mode (spec 94-96, 120).

Defaults are SAFE: marketplace discovery is readable, but remote
delegation, paid agents, auto-negotiation, auto-payment, external
registries and org marketplace features start DISABLED until the
operator enables them explicitly. Every change is audited.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from .store import JsonStore

FLAGS = (
    "marketplace",
    "remote_delegation",
    "paid_agents",
    "automatic_negotiation",
    "automatic_payment",
    "external_registries",
    "organization_marketplace",
)

# Safe defaults: everything that can spend money or touch remotes is OFF.
DEFAULTS = {
    "marketplace": True,            # local search/inspection only
    "remote_delegation": False,
    "paid_agents": False,
    "automatic_negotiation": False,
    "automatic_payment": False,
    "external_registries": False,
    "organization_marketplace": False,
}

KILL_SWITCHES = (
    "provider", "registry", "payments", "external_delegation",
    "automatic_purchasing",
)


class FeatureFlags:
    def __init__(self, home: Path) -> None:
        self._flags = JsonStore(Path(home) / "feature_flags.json")
        self._audit = JsonStore(Path(home) / "flag_audit.json")
        for name, default in DEFAULTS.items():
            if self._flags.get(name) is None:
                self._flags.put(name, {"enabled": default, "updated_at": time.time(),
                                       "by": "defaults"})

    def is_enabled(self, name: str) -> bool:
        if name not in FLAGS:
            raise ValueError(f"unknown flag: {name!r}")
        rec = self._flags.get(name) or {}
        return bool(rec.get("enabled", DEFAULTS[name]))

    def set(self, name: str, enabled: bool, by: str = "") -> None:
        if name not in FLAGS:
            raise ValueError(f"unknown flag: {name!r}")
        self._flags.put(name, {"enabled": bool(enabled),
                               "updated_at": time.time(), "by": by})
        log = self._audit.get("log") or []
        log.append({"at": time.time(), "flag": name,
                    "enabled": bool(enabled), "by": by})
        self._audit.put("log", log[-1000:])

    def require(self, name: str) -> None:
        if not self.is_enabled(name):
            raise PermissionError(f"feature disabled by policy: {name}")

    def audit_log(self) -> List[Dict[str, Any]]:
        return self._audit.get("log") or []


class KillSwitch:
    """Operator emergency controls. All actions audited (spec 96)."""

    def __init__(self, home: Path, flags: FeatureFlags) -> None:
        self._state = JsonStore(Path(home) / "kill_switch.json")
        self._flags = flags

    def engage(self, target: str, by: str = "", reason: str = "") -> Dict[str, Any]:
        if target not in KILL_SWITCHES:
            raise ValueError(f"unknown kill target: {target!r}")
        mapping = {
            "provider": [],  # provider-scoped: handled by caller with provider id
            "registry": ["external_registries", "organization_marketplace"],
            "payments": ["paid_agents", "automatic_payment"],
            "external_delegation": ["remote_delegation"],
            "automatic_purchasing": ["automatic_payment", "automatic_negotiation"],
        }
        for flag in mapping[target]:
            self._flags.set(flag, False, by=f"kill:{by}")
        rec = {"target": target, "engaged": True, "by": by,
               "reason": reason[:500], "at": time.time()}
        log = self._state.get("log") or []
        log.append(rec)
        self._state.put("log", log[-500:])
        return rec

    def stop_all_marketplace_activity(self, by: str = "") -> Dict[str, Any]:
        """STOP ALL MARKETPLACE ACTIVITY: no new delegations, payments,
        negotiation, or retries. In-flight work is cancelled via the
        network gateway by the caller (safe handling, sec 95)."""
        for flag in ("remote_delegation", "paid_agents", "automatic_negotiation",
                     "automatic_payment"):
            self._flags.set(flag, False, by=f"stop_all:{by}")
        rec = {"target": "all", "engaged": True, "by": by, "at": time.time()}
        log = self._state.get("log") or []
        log.append(rec)
        self._state.put("log", log[-500:])
        return rec

    def log(self) -> List[Dict[str, Any]]:
        return self._state.get("log") or []


def safe_mode_active(flags: FeatureFlags) -> bool:
    """Safe mode: paid execution + auto delegation/purchasing disabled."""
    return not flags.is_enabled("paid_agents") \
        and not flags.is_enabled("automatic_payment") \
        and not flags.is_enabled("remote_delegation")
