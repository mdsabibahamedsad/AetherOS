"""Agent registry: 16 Master-42 roles with capability/tool/permission profiles.

Definitions declare capabilities, default tools, permissions (least
privilege), model hints, context needs, cost/latency profiles and risk.
Selection is capability-driven (never "spawn everything").
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_swarm.models import AgentInstance


@dataclass
class AgentDefinition:
    role: str
    capabilities: List[str]
    default_tools: List[str]
    permissions: List[str]
    model_hint: str = ""
    context_need: str = "minimal"
    cost_per_1k: float = 0.002
    latency_class: str = "standard"
    risk_level: str = "low"
    max_parallel: int = 4
    description: str = ""


DEFINITIONS: List[AgentDefinition] = [
    AgentDefinition("orchestrator", ["plan", "delegate", "synthesize", "decide"],
                    ["swarm_status"], ["read"], cost_per_1k=0.006,
                    latency_class="reasoning", description="Owns the overall task."),
    AgentDefinition("planner", ["decompose", "sequence", "estimate"],
                    [], ["read"], cost_per_1k=0.006, latency_class="reasoning",
                    description="Breaks goals into executable subtasks."),
    AgentDefinition("researcher", ["web_search", "fetch", "cite", "compare_sources"],
                    ["web_search", "web_extract"], ["network", "read"],
                    cost_per_1k=0.001, latency_class="fast",
                    description="Gathers evidence (Master 40 integration)."),
    AgentDefinition("analyst", ["summarize", "compare", "tabulate", "statistics"],
                    [], ["read"], cost_per_1k=0.002, description="Analyzes information."),
    AgentDefinition("coder", ["write_code", "edit_code", "run_tests", "refactor"],
                    ["read_file", "patch", "terminal"], ["filesystem_read", "filesystem_write", "terminal"],
                    risk_level="medium", cost_per_1k=0.003, description="Writes/modifies code."),
    AgentDefinition("reviewer", ["review_code", "review_text", "critique"],
                    ["read_file"], ["read", "filesystem_read"], cost_per_1k=0.004,
                    latency_class="reasoning", description="Reviews work."),
    AgentDefinition("verifier", ["run_tests", "check_claims", "validate_schema", "reproduce"],
                    ["read_file", "terminal"], ["read", "filesystem_read", "terminal"],
                    cost_per_1k=0.002, description="Tests claims, code, artifacts."),
    AgentDefinition("browser_agent", ["navigate", "click", "type", "extract"],
                    ["browser_navigate"], ["network", "browser", "read"],
                    risk_level="medium", description="Uses browser infra (Master 39)."),
    AgentDefinition("computer_agent", ["screenshot", "click_at", "type_text", "verify_ui"],
                    ["computer_use"], ["read"], risk_level="high", max_parallel=1,
                    description="Desktop/computer control (Master 39)."),
    AgentDefinition("terminal_agent", ["run_command", "inspect_output"],
                    ["terminal"], ["terminal", "read"], risk_level="medium",
                    description="Terminal tasks."),
    AgentDefinition("file_agent", ["read", "write", "organize", "parse"],
                    ["read_file", "search_files"], ["filesystem_read"],
                    description="File operations."),
    AgentDefinition("data_agent", ["query", "aggregate", "plot", "clean"],
                    ["read_file", "execute_code"], ["filesystem_read", "read"],
                    description="Data analysis."),
    AgentDefinition("writer", ["draft", "edit", "format", "summarize"],
                    [], ["read"], cost_per_1k=0.001, latency_class="fast",
                    description="Produces final documents."),
    AgentDefinition("security_agent", ["audit", "threat_model", "attack_sim", "review_perms"],
                    ["read_file", "search_files"], ["read", "filesystem_read"],
                    cost_per_1k=0.004, latency_class="reasoning",
                    description="Audits security risks (read-only)."),
    AgentDefinition("memory_agent", ["recall", "store_candidate", "build_context"],
                    ["memory2_search", "memory2_get"], ["read"],
                    description="Scoped Master-41 memory access."),
    AgentDefinition("synthesizer", ["merge", "resolve", "finalize"],
                    [], ["read"], cost_per_1k=0.004, latency_class="reasoning",
                    description="Combines verified outputs."),
]


class AgentRegistry:
    def __init__(self, definitions: Optional[List[AgentDefinition]] = None) -> None:
        self._defs: Dict[str, AgentDefinition] = {d.role: d for d in (definitions or DEFINITIONS)}
        self._agents: Dict[str, AgentInstance] = {}
        self._last_seen: Dict[str, float] = {}

    def register(self, definition: AgentDefinition) -> None:
        self._defs[definition.role] = definition

    def unregister(self, role: str) -> bool:
        return self._defs.pop(role, None) is not None

    def discover(self) -> List[str]:
        return sorted(self._defs)

    def get(self, role: str) -> Optional[AgentDefinition]:
        return self._defs.get(role)

    def find_by_capability(self, capability: str) -> List[AgentDefinition]:
        return [d for d in self._defs.values() if capability in d.capabilities]

    def find_by_role(self, role: str) -> Optional[AgentDefinition]:
        return self._defs.get(role)

    def match(self, required_capabilities: List[str]) -> List[AgentDefinition]:
        """Roles covering the most required capabilities first (set cover greedy)."""
        scored = [(len(set(d.capabilities) & set(required_capabilities)), d)
                  for d in self._defs.values()]
        return [d for s, d in sorted(scored, key=lambda x: -x[0]) if s > 0]

    def track(self, agent: AgentInstance) -> None:
        self._agents[agent.id] = agent
        self._last_seen[agent.id] = time.time()

    def heartbeat(self, agent_id: str, health: str = "healthy") -> None:
        if agent_id in self._agents:
            self._agents[agent_id].health = health
            self._last_seen[agent_id] = time.time()

    def health(self) -> Dict[str, Any]:
        now = time.time()
        return {"roles": len(self._defs), "tracked": len(self._agents),
                "agents": {aid: {"role": a.role, "status": a.status.value,
                                 "health": a.health, "age_s": round(now - self._last_seen.get(aid, now), 1)}
                           for aid, a in self._agents.items()}}

    def remove(self, agent_id: str) -> bool:
        self._last_seen.pop(agent_id, None)
        return self._agents.pop(agent_id, None) is not None
