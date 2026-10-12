"""Specialist agent catalog (P3, P63-67).

Static manifests binding the named specialists to real roles/capabilities and
the existing adapter surface (core AIAgent / delegate_tool / automation /
research / computer-use). Manifests are DATA for the planner; runtime
authority always comes from GrantedCapabilities + policy.

Also: performance/reputation stats (P66-67) — routing signals only, never
permission signals.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.orchestration.swarm_guards import (
    ALL_CAPABILITIES,
    Capability,
    risk_from_capabilities,
)
from agent.orchestration.types import AgentRole


@dataclass
class SpecialistManifest:
    """P2-flavored manifest for a named specialist."""

    agent_id: str
    name: str
    role: AgentRole
    version: str = "1.0.0"
    description: str = ""
    capabilities: frozenset = frozenset()
    tools: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    memory_scope: str = "task"          # task|project|user (never global)
    network_scope: str = "none"         # none|search|full
    filesystem_scope: str = "none"      # none|read|workspace|full
    supported_tasks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    max_parallel_tasks: int = 1
    default_timeout_seconds: float = 600.0
    budget_defaults: Dict[str, Any] = field(default_factory=dict)
    health_status: str = "healthy"      # healthy|degraded|unavailable|misconfigured|rate_limited|failed

    @property
    def risk_level(self):
        return risk_from_capabilities(self.capabilities)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "version": self.version,
            "description": self.description,
            "capabilities": sorted(self.capabilities),
            "tools": list(self.tools),
            "permissions": list(self.permissions),
            "memory_scope": self.memory_scope,
            "network_scope": self.network_scope,
            "filesystem_scope": self.filesystem_scope,
            "risk_level": self.risk_level.value,
            "supported_tasks": list(self.supported_tasks),
            "dependencies": list(self.dependencies),
            "max_parallel_tasks": self.max_parallel_tasks,
            "default_timeout_seconds": self.default_timeout_seconds,
            "budget_defaults": dict(self.budget_defaults),
            "health_status": self.health_status,
        }


def _caps(*names: str) -> frozenset:
    return frozenset(names)


SPECIALISTS: Dict[str, SpecialistManifest] = {}


def _register(m: SpecialistManifest) -> None:
    unknown = m.capabilities - ALL_CAPABILITIES
    if unknown:
        raise ValueError(f"{m.agent_id}: unknown capabilities {sorted(unknown)}")
    SPECIALISTS[m.agent_id] = m


_register(SpecialistManifest(
    agent_id="swarm.planner", name="PlannerAgent", role=AgentRole.PLANNER,
    description="Decomposes objectives into a validated task graph.",
    capabilities=_caps(Capability.MEMORY_READ),
    supported_tasks=["planning", "decomposition"],
))
_register(SpecialistManifest(
    agent_id="swarm.research", name="ResearchAgent", role=AgentRole.RESEARCH,
    description="Evidence-backed research via the Master 17 engine.",
    capabilities=_caps(Capability.WEB_SEARCH, Capability.RESEARCH,
                       Capability.MEMORY_READ),
    tools=["web_search", "web_extract"],
    network_scope="search",
    supported_tasks=["research", "evidence-collection"],
))
_register(SpecialistManifest(
    agent_id="swarm.browser", name="BrowserAgent", role=AgentRole.BROWSER,
    description="Reads/interacts with pages through existing browser security.",
    capabilities=_caps(Capability.BROWSER_READ, Capability.BROWSER_INTERACT,
                       Capability.RESEARCH),
    tools=["browser_navigate", "browser_read"],
    network_scope="search",
    supported_tasks=["browsing", "page-extraction"],
))
_register(SpecialistManifest(
    agent_id="swarm.computer_use", name="ComputerUseAgent",
    role=AgentRole.COORDINATOR,
    description="UI actions via Master 15 control + confirmation layers.",
    capabilities=_caps(Capability.COMPUTER_CONTROL, Capability.FILE_READ),
    tools=["computer_control"],
    filesystem_scope="read",
    supported_tasks=["ui-automation"],
    default_timeout_seconds=300.0,
))
_register(SpecialistManifest(
    agent_id="swarm.coding", name="CodingAgent", role=AgentRole.CODING,
    description="Modifies relevant files only; runs tests; reports changes.",
    capabilities=_caps(Capability.CODE_EDIT, Capability.FILE_READ,
                       Capability.FILE_WRITE, Capability.SHELL_EXECUTE,
                       Capability.TEST_EXECUTE),
    tools=["read_file", "edit_file", "terminal"],
    filesystem_scope="workspace",
    supported_tasks=["coding", "refactoring"],
    budget_defaults={"max_files_changed": 10},
))
_register(SpecialistManifest(
    agent_id="swarm.testing", name="TestingAgent", role=AgentRole.QA,
    description="Runs targeted/integration/regression tests; triages failures.",
    capabilities=_caps(Capability.TEST_EXECUTE, Capability.FILE_READ,
                       Capability.SHELL_EXECUTE),
    tools=["terminal"],
    filesystem_scope="read",
    supported_tasks=["testing", "verification-support"],
))
_register(SpecialistManifest(
    agent_id="swarm.documentation", name="DocumentationAgent",
    role=AgentRole.WRITER,
    description="Updates only documentation relevant to the change set.",
    capabilities=_caps(Capability.FILE_READ, Capability.FILE_WRITE,
                       Capability.MEMORY_READ),
    tools=["read_file", "edit_file"],
    filesystem_scope="workspace",
    supported_tasks=["documentation"],
))
_register(SpecialistManifest(
    agent_id="swarm.data", name="DataAgent", role=AgentRole.DATA,
    description="Structured data extraction and transformation.",
    capabilities=_caps(Capability.FILE_READ, Capability.CODE_EDIT,
                       Capability.NETWORK_ACCESS),
    supported_tasks=["data-processing"],
))
_register(SpecialistManifest(
    agent_id="swarm.analysis", name="AnalysisAgent", role=AgentRole.ANALYSIS,
    description="Analyzes artifacts/results and produces structured findings.",
    capabilities=_caps(Capability.FILE_READ, Capability.MEMORY_READ),
    supported_tasks=["analysis"],
))
_register(SpecialistManifest(
    agent_id="swarm.verifier", name="VerificationAgent",
    role=AgentRole.VERIFICATION,
    description="Independent verification of produced work (P26).",
    capabilities=_caps(Capability.FILE_READ, Capability.TEST_EXECUTE,
                       Capability.MEMORY_READ),
    supported_tasks=["verification"],
))
_register(SpecialistManifest(
    agent_id="swarm.critic", name="CriticAgent", role=AgentRole.CRITIC,
    description="Adversarial review: assumptions, missing evidence, edge cases.",
    capabilities=_caps(),
    supported_tasks=["critique"],
))
_register(SpecialistManifest(
    agent_id="swarm.security", name="SecurityAgent", role=AgentRole.SECURITY,
    description="Inspects boundaries/permissions/exfiltration; never weakens controls.",
    capabilities=_caps(Capability.FILE_READ, Capability.MEMORY_READ),
    supported_tasks=["security-review"],
))
_register(SpecialistManifest(
    agent_id="swarm.monitoring", name="MonitoringAgent",
    role=AgentRole.MONITORING,
    description="Observes latency/errors/resources/progress/health.",
    capabilities=_caps(),
    supported_tasks=["monitoring"],
))
_register(SpecialistManifest(
    agent_id="swarm.recovery", name="RecoveryAgent", role=AgentRole.RECOVERY,
    description="Chooses retry/rollback/re-scope/replan after failures.",
    capabilities=_caps(Capability.MEMORY_READ),
    supported_tasks=["recovery"],
))
_register(SpecialistManifest(
    agent_id="swarm.synthesis", name="SynthesisAgent", role=AgentRole.SYNTHESIS,
    description="Combines verified outputs preserving conflicts/citations (P88).",
    capabilities=_caps(Capability.MEMORY_READ),
    supported_tasks=["synthesis"],
))


def get_specialists() -> Dict[str, SpecialistManifest]:
    return dict(SPECIALISTS)


def select_team(required_capabilities: frozenset, *,
                max_agents: int = 4,
                exclude: Optional[set] = None) -> List[SpecialistManifest]:
    """P63-65 — capability-based team formation (never by name alone).

    Greedy cover: pick the specialist adding the most uncovered required
    capabilities; skip unhealthy agents.
    """
    remaining = set(required_capabilities)
    chosen: List[SpecialistManifest] = []
    pool = [m for aid, m in SPECIALISTS.items()
            if aid not in (exclude or set()) and m.health_status == "healthy"]
    while remaining and len(chosen) < max_agents:
        best = None
        best_cover = set()
        for m in pool:
            if m in chosen:
                continue
            cover = remaining & set(m.capabilities)
            if cover and len(cover) > len(best_cover):
                best, best_cover = m, cover
        if best is None:
            break
        chosen.append(best)
        remaining -= set(best.capabilities)
    return chosen


@dataclass
class ReputationRecord:
    """P66-67 — routing signals ONLY. Never consulted by guards/policy."""

    success_count: int = 0
    failure_count: int = 0
    verification_pass_count: int = 0
    total_latency: float = 0.0
    total_cost_usd: float = 0.0
    updated_at: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return round(self.success_count / total, 3) if total else 0.0

    @property
    def avg_latency(self) -> float:
        return round(self.total_latency / self.success_count, 3) \
            if self.success_count else 0.0


class ReputationStore:
    def __init__(self):
        self._records: Dict[str, ReputationRecord] = {}

    def record(self, agent_id: str, *, success: bool,
               verified: bool = False, latency: float = 0.0,
               cost_usd: float = 0.0) -> ReputationRecord:
        rec = self._records.setdefault(agent_id, ReputationRecord())
        if success:
            rec.success_count += 1
            rec.total_latency += latency
            rec.total_cost_usd += cost_usd
            if verified:
                rec.verification_pass_count += 1
        else:
            rec.failure_count += 1
        rec.updated_at = time.time()
        return rec

    def get(self, agent_id: str) -> ReputationRecord:
        return self._records.get(agent_id, ReputationRecord())
