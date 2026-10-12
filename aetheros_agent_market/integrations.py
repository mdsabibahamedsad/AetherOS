"""System integrations (spec 26, 41-43, 101-103).

Thin adapters over REAL subsystems — no rewrites, no duplication:
- Swarm: marketplace candidates as planner proposals (data, never
  auto-spawn) + evidence-claim mapping for verifier roles.
- Automation: validated scheduled-delegation specs executed through the
  full gated pipeline (no step skippable).
- Research: narrow research delegation with enforced citation policy.
- Memory: marketplace facts stored with provenance (evidence store
  primary; memory service when available).
- Model routing: local-vs-remote comparison DATA for the router
  (the router decides; identity stays distinct).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .flow import FlowError, MarketplaceFlow


# -- swarm (spec 26) ----------------------------------------------------------
def swarm_member_proposals(flow: MarketplaceFlow, task: Dict[str, Any],
                           limit: int = 3) -> List[Dict[str, Any]]:
    """Ranked marketplace candidates as swarm-planner input.

    Returns scored candidates WITH explanations and vetoes. The swarm
    orchestrator decides membership under its own policy; this function
    never spawns anything (no agent-count maximization).
    """
    rec = flow.recommend(task, limit=limit)
    return [{"agent_id": c["agent_id"], "service_id": c["service_id"],
             "source": c["source"], "score": c["score"],
             "why": c.get("breakdown", {}),
             "origin": "marketplace"} for c in rec["candidates"]]


def swarm_evidence_claim(contract_id: str, verification: Dict[str, Any],
                         agent_id: str = "") -> Dict[str, Any]:
    """Map a marketplace verification result onto the swarm evidence
    carrier (claim+evidence+source+citation+confidence+agent)."""
    passed = bool(verification.get("passed", False))
    return {"claim": f"marketplace delegation {contract_id} "
                     f"{'verified' if passed else 'FAILED verification'}",
            "evidence": verification.get("details", {}),
            "source": f"marketplace:{contract_id}",
            "citation": "",
            "confidence": 1.0 if passed else 0.0,
            "agent": agent_id or "marketplace"}


# -- automation (spec 41) -------------------------------------------------------
def scheduled_delegation_spec(task: Dict[str, Any],
                              selection: Dict[str, Any]) -> Dict[str, Any]:
    """Validate + freeze a delegation spec for scheduled execution.

    Returns the spec with a checklist the automation engine must honor.
    Execution itself goes through MarketplaceFlow.delegate (all gates).
    """
    for key in ("summary",):
        if not task.get(key):
            raise ValueError(f"automation task missing {key}")
    for key in ("service_id", "agent_id"):
        if not selection.get(key):
            raise ValueError(f"automation selection missing {key}")
    return {"task": dict(task), "selection": dict(selection),
            "gates": ["discover", "rank", "validate", "quote", "contract",
                      "budget", "approval?", "execute", "verify", "settle",
                      "evidence", "reputation"],
            "version": 1}


def run_scheduled(flow: MarketplaceFlow, spec: Dict[str, Any],
                  approved_by: str = "") -> Dict[str, Any]:
    """Execute a frozen spec through the FULL pipeline (spec 41: no step
    may be skipped — delegate() enforces every gate)."""
    if spec.get("version") != 1:
        raise ValueError("unsupported automation spec version")
    return flow.delegate(spec["task"], spec["selection"],
                         approved_by=approved_by)


# -- research (spec 42) -----------------------------------------------------------
def research_subtask(flow: MarketplaceFlow, question: str,
                     selection: Dict[str, Any],
                     min_citations: int = 2,
                     approved_by: str = "") -> Dict[str, Any]:
    """Delegate narrow research with enforced citation verification.

    Marketplace evidence requirements are never bypassed: the contract
    mandates citation_presence and the platform re-checks locally.
    """
    if not question or len(question) > 4000:
        raise ValueError("research question required (<=4000 chars)")
    task = {"summary": question, "capabilities": ["research.web_search"],
            "data_class": "INTERNAL",
            "verification_requirements": ["schema", "citation_presence"],
            "success_criteria": [],
            "payment_provider": "none", "requester": "research"}
    out = flow.delegate(task, selection, approved_by=approved_by)
    out["citation_policy"] = {"min_citations": min_citations,
                              "strategy": "citation_presence"}
    return out


# -- memory (spec 43) ---------------------------------------------------------------
def remember_marketplace_fact(flow: MarketplaceFlow, fact: str,
                              agent_id: str = "",
                              kind: str = "preference") -> Dict[str, Any]:
    """Store a marketplace fact WITH provenance.

    Primary store is the evidence chain (always works). If the memory
    service is importable, a mirrored record is written; otherwise the
    evidence reference is returned and memory sync is reported as
    unavailable (never faked).
    """
    if not fact or len(fact) > 2000:
        raise ValueError("fact required (<=2000 chars)")
    ev = flow.evidence.put("event", fact.encode("utf-8"),
                           actor=agent_id or "local",
                           summary=f"marketplace {kind}: {fact[:200]}")
    mirrored = False
    try:
        from aetheros_memory_intelligence.service import MemoryService
        svc = MemoryService()
        svc.initialize()
        svc.store(f"[marketplace:{kind}] {fact}",
                  metadata={"evidence_id": ev.evidence_id,
                            "agent_id": agent_id, "provenance": "marketplace"})
        mirrored = True
    except Exception:
        mirrored = False
    return {"evidence_id": ev.evidence_id, "mirrored_to_memory": mirrored}


# -- model routing (spec 102) ----------------------------------------------------------
def routing_comparison(flow: MarketplaceFlow, task: Dict[str, Any]) -> Dict[str, Any]:
    """Local-vs-remote comparison DATA for the model router.

    Returns measured/known quantities with explicit uncertainty; the
    router makes the decision. Marketplace identity and model identity
    stay distinct (spec 102).
    """
    rec = flow.recommend(task, limit=3)
    best = rec["candidates"][0] if rec["candidates"] else None
    return {
        "local": rec["local"],
        "remote_best": ({
            "agent_id": best["agent_id"], "score": best["score"],
            "explanation": best.get("breakdown", {}),
        } if best else None),
        "uncertainty": "remote latency/cost are quotes+history, not guarantees; "
                       "local figures measured at runtime",
    }
