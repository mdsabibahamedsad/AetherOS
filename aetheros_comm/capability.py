"""
Agent Communication Fabric — capability sets and capability-based routing
(master spec steps 10 and 11).

Tasks are routed to agents that declare the required capabilities, never by
hardcoding a single agent name where capability routing is possible. The
router also applies trust-zone and status filters so a candidate must be
active, healthy, and permitted to communicate.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .identity import AgentRegistry, AgentStatus
from .types import TrustZone
from .authz import capability_matches


class CapabilitySet:
    """An immutable-ish set of capability strings.

    Capabilities are ``category:action`` tokens (e.g. ``repository_read``,
    ``security_analysis``, ``code_analysis``) used for least-privilege
    matching and routing.
    """

    def __init__(self, capabilities: Optional[Iterable[str]] = None) -> None:
        self._caps: Set[str] = set(capabilities or ())

    def add(self, capability: str) -> None:
        self._caps.add(capability)

    def remove(self, capability: str) -> None:
        self._caps.discard(capability)

    def has(self, capability: str) -> bool:
        return capability in self._caps

    def has_all(self, required: Iterable[str]) -> bool:
        return set(required).issubset(self._caps)

    def has_any(self, required: Iterable[str]) -> bool:
        return bool(set(required) & self._caps)

    def intersection(self, other: Iterable[str]) -> "CapabilitySet":
        return CapabilitySet(self._caps & set(other))

    def to_list(self) -> List[str]:
        return sorted(self._caps)

    def __contains__(self, item: str) -> bool:
        return item in self._caps

    def __len__(self) -> int:
        return len(self._caps)

    def __iter__(self):
        return iter(self._caps)

    def __repr__(self) -> str:  # pragma: no cover
        return f"CapabilitySet({sorted(self._caps)!r})"


class CapabilityRouter:
    """Routes a task to agents that satisfy its required capabilities.

    Filters, in order:
        1. Registered and ACTIVE
        2. Declares every required capability
        3. Trust-zone policy permits the requester to reach the candidate
           (cross-zone communication requires explicit policy — step 12)
    """

    def __init__(self, registry: AgentRegistry,
                 trust_policy=None) -> None:
        self._registry = registry
        self._trust_policy = trust_policy

    def candidates(self, required: Sequence[str],
                   requester_agent_id: str = "",
                   requester_zone: Optional[TrustZone] = None,
                   exclude: Optional[Iterable[str]] = None) -> List[str]:
        """Return matching agent ids, best-fit first.

        ``requester_zone`` is the requester's trust zone used to filter
        cross-zone candidates. If ``trust_policy`` is None no zone filter is
        applied (callers that pass one get zone enforcement).
        """
        required_set = set(required)
        excluded = set(exclude or ())
        result: List[Tuple[int, str]] = []
        requester_zone = requester_zone or (
            TrustZone.from_str(self._registry.get(requester_agent_id).trustZone)
            if requester_agent_id and self._registry.get(requester_agent_id)
            else TrustZone.ZONE_1)
        for identity in self._registry._agents.values():
            if identity.agentId in excluded:
                continue
            if identity.status != AgentStatus.ACTIVE:
                continue
            if not all(
                    any(capability_matches(c, cap)
                        for c in identity.capabilities)
                    for cap in required_set):
                continue
            if self._trust_policy is not None:
                candidate_zone = TrustZone.from_str(identity.trustZone)
                allowed = self._trust_policy.can_communicate(
                    requester_zone, candidate_zone)
                if not allowed and required_set:
                    allowed = any(
                        self._trust_policy.can_communicate(
                            requester_zone, candidate_zone, cap)
                        for cap in required_set)
                if not allowed:
                    continue
            # Best fit: candidates with the fewest *extra* capabilities first.
            extra = len(set(identity.capabilities) - required_set)
            result.append((extra, identity.agentId))
        result.sort(key=lambda item: (item[0], item[1]))
        return [aid for _, aid in result]

    def route(self, required: Sequence[str],
              requester_agent_id: str = "",
              requester_zone: Optional[TrustZone] = None,
              preferred: Sequence[str] = (),
              exclude: Optional[Iterable[str]] = None) -> Optional[str]:
        """Pick a single candidate, preferring ``preferred`` order first."""
        candidates = self.candidates(
            required, requester_agent_id=requester_agent_id,
            requester_zone=requester_zone, exclude=exclude)
        if not candidates:
            return None
        for aid in preferred:
            if aid in candidates:
                return aid
        return candidates[0]

    def fallback_chain(self, required: Sequence[str],
                       requester_agent_id: str = "",
                       requester_zone: Optional[TrustZone] = None,
                       exclude: Optional[Iterable[str]] = None) -> List[str]:
        """Return an ordered fallback chain (step 38) for a task.

        The chain respects capabilities, status, and trust-zone policy. The
        caller (orchestrator) may append a single-agent degraded mode or
        human approval as the terminal step.
        """
        return self.candidates(
            required, requester_agent_id=requester_agent_id,
            requester_zone=requester_zone, exclude=exclude)