"""
Agent Communication Fabric — trust zones (master spec step 12).

Logical zones ``ZONE_0`` .. ``ZONE_4``. Agents never communicate across zones
implicitly — cross-zone communication requires an explicit policy allowance,
and the allowance is capability-scoped (an allowance grants a specific
capability, not blanket access).
"""

from __future__ import annotations

import threading
from typing import Dict, Set, Tuple

from .types import TrustZone


class TrustZonePolicy:
    """Policy governing inter-zone communication.

    Same-zone communication is allowed by default. Cross-zone communication
    is denied unless an explicit allowance exists for the pair (optionally
    scoped to a capability).
    """

    def __init__(self) -> None:
        self._allow: Dict[Tuple[TrustZone, TrustZone], Set[str]] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Policy configuration
    # ------------------------------------------------------------------

    def allow_cross_zone(self, source: TrustZone, target: TrustZone,
                         capabilities: Tuple[str, ...] = ()) -> None:
        """Allow ``source`` -> ``target`` communication.

        When ``capabilities`` is empty the allowance is unconditional for the
        pair; otherwise only messages that require one of the listed
        capabilities may cross.
        """
        with self._lock:
            self._allow.setdefault((source, target), set()).update(capabilities)

    def deny_cross_zone(self, source: TrustZone, target: TrustZone) -> None:
        """Remove any allowance for ``source`` -> ``target``."""
        with self._lock:
            self._allow.pop((source, target), None)

    def clear(self) -> None:
        with self._lock:
            self._allow.clear()

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def is_cross_zone(self, source: TrustZone, target: TrustZone) -> bool:
        return source != target

    def can_communicate(self, source: TrustZone, target: TrustZone,
                        capability: str = "") -> bool:
        """Whether a message may flow ``source`` -> ``target``.

        Rules:
          - same zone: allowed.
          - source is ZONE_4 (security/control plane): allowed (control plane
            may always reach agents; the reverse is governed by the same
            explicit-policy rule so a normal agent still cannot reach ZONE_4
            without an allowance).
          - target is ZONE_0 (untrusted): explicit policy only.
          - otherwise: explicit allowance for the pair, either unconditional
            or covering ``capability``.
        """
        if not self.is_cross_zone(source, target):
            return True
        if source == TrustZone.ZONE_4:
            return True
        with self._lock:
            caps = self._allow.get((source, target))
            if caps is None:
                return False
            if not caps:
                return True  # unconditional allowance
            return bool(capability) and capability in caps

    def allowed_cross_zones(self, source: TrustZone) -> Tuple[TrustZone, ...]:
        """Return target zones ``source`` may reach."""
        with self._lock:
            return tuple(target for (s, target) in self._allow
                         if s == source)

    def policy_map(self) -> Dict[str, Dict[str, Set[str]]]:
        with self._lock:
            return {
                f"{s.value}->{t.value}": set(caps)
                for (s, t), caps in self._allow.items()
            }