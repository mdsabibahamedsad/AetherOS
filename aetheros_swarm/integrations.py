"""Master integrations (sections 25-26, 31-33, 62-67, 95): memory, evidence,
model routing/fallback hooks. Thin adapters over real subsystems — no
rewrites. Research/browser/computer teams are role compositions executed
by the orchestrator with real tool permissions; evidence propagation uses
the AgentResult.evidence claim carrier (claim+evidence+source+citation+
confidence+agent).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


def memory41_recall_adapter(service=None) -> Optional[Callable]:
    """Build a ContextSelector-compatible recall fn from Master-41 service."""
    if service is None:
        try:
            from aetheros_memory_intelligence.service import MemoryService
            service = MemoryService()
            service.initialize()
        except Exception:
            return None

    def recall(query: str, *, project_id: str = "", top_k: int = 5) -> Dict[str, Any]:
        from aetheros_memory_intelligence.record import RecordScope
        scope = RecordScope.PROJECT if project_id else RecordScope.USER
        return service.retrieve(query, scope=scope, project_id=project_id, top_k=top_k)

    return recall


def evidence_claim(*, claim: str, source: str, citation: str = "",
                   confidence: float = 0.5, agent: str = "",
                   research_run: str = "") -> Dict[str, Any]:
    """Master-40-compatible evidence carrier for cross-agent claims."""
    return {"claim": claim, "evidence": claim, "source": source,
            "citation": citation, "confidence": confidence,
            "agent": agent, "research_run": research_run}


# Model routing/fallback policy hook (Master 38 router integration point).
# Role -> ordered model preference; fallback walks the list preserving state.
ROLE_MODEL_CHAIN: Dict[str, List[str]] = {
    "planner": ["reasoning", "standard"],
    "researcher": ["efficient", "standard"],
    "coder": ["coding", "standard"],
    "reviewer": ["reasoning", "standard"],
    "writer": ["low-cost", "standard"],
    "synthesizer": ["low-cost", "standard"],
}


def model_chain_for(role: str) -> List[str]:
    return list(ROLE_MODEL_CHAIN.get(role, ["standard"]))


# Team compositions (sections 62-67): role lists consumed by TopologyEngine.
TEAM_COMPOSITIONS: Dict[str, List[str]] = {
    "research": ["researcher", "researcher", "analyst", "reviewer", "verifier", "synthesizer"],
    "coding": ["coder", "coder", "reviewer", "verifier"],
    "computer_use": ["planner", "browser_agent", "computer_agent", "verifier"],
    "documents": ["file_agent", "analyst", "reviewer", "writer"],
    "memory": ["memory_agent", "analyst", "verifier"],
    "security": ["coder", "security_agent", "verifier"],
}
