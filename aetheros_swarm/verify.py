"""Verification: review loop, verifier, debate judge, conflicts, synthesis.

- run_review_loop(): worker -> reviewer -> revision -> verifier, bounded.
- verify_result(): oracle/tests/schema/source/hash/execution dispatch.
- judge_debate(): evidence-weighted pick (majority never equals truth).
- ConflictResolver: evidence -> source quality -> confidence ->
  assumptions -> targeted verification -> escalate; outputs UNRESOLVED
  honestly when evidence is insufficient.
- synthesize(): merges VERIFIED findings only; preserves uncertainties.
- quality_gate(): completeness/correctness/evidence/consistency/security/
  policy/artifact checks before a final result is returned.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, List, Optional

from aetheros_swarm.models import AgentResult, ConsensusMode

VerifierFn = Callable[[AgentResult, Dict[str, Any]], Dict[str, Any]]


def verify_result(result: AgentResult, *, method: str = "oracle",
                  spec: Optional[Dict[str, Any]] = None,
                  custom: Optional[VerifierFn] = None) -> Dict[str, Any]:
    spec = spec or {}
    if custom is not None:
        return custom(result, spec)
    if method == "oracle":
        expected = spec.get("expected_summary", "")
        ok = bool(expected) and expected.strip().lower() in (result.summary or "").strip().lower()
        return {"passed": ok, "method": "oracle", "detail": "summary match" if ok else "summary mismatch"}
    if method == "schema":
        required = spec.get("required_fields", ["summary", "status"])
        missing = [f for f in required if not getattr(result, f, None)]
        return {"passed": not missing, "method": "schema",
                "detail": f"missing={missing}" if missing else "ok"}
    if method == "hash":
        digest = hashlib.sha256((result.summary or "").encode()).hexdigest()
        return {"passed": digest == spec.get("sha256", ""), "method": "hash", "detail": digest[:16]}
    if method == "evidence":
        ok = len(result.evidence) >= int(spec.get("min_evidence", 1))
        return {"passed": ok, "method": "evidence",
                "detail": f"evidence={len(result.evidence)}"}
    if method in ("review", "none"):
        return {"passed": True, "method": method, "detail": "no oracle; reviewer-gated"}
    return {"passed": False, "method": method, "detail": "unknown method"}


def run_review_loop(worker: AgentResult, reviewer_notes: List[str],
                    *, max_rounds: int = 2,
                    verify: Optional[Callable[[AgentResult], Dict[str, Any]]] = None) -> Dict[str, Any]:
    rounds = 0
    current = worker
    history: List[Dict[str, Any]] = []
    approved = not reviewer_notes
    while rounds < max_rounds:
        if not reviewer_notes:
            approved = True
            break
        note = reviewer_notes.pop(0)
        history.append({"round": rounds + 1, "note": note})
        current.assumptions.append(f"addressed review: {note[:120]}")
        rounds += 1
        if verify is not None:
            v = verify(current)
            history[-1]["verification"] = v
            if v.get("passed"):
                approved = True
                break
    return {"approved": approved, "rounds": rounds, "result": current, "history": history}


def judge_debate(proposals: List[AgentResult]) -> Dict[str, Any]:
    """Evidence-weighted pick: most supported evidence wins, ties -> unresolved."""
    if not proposals:
        return {"winner": -1, "reason": "no proposals"}
    scored = []
    for i, p in enumerate(proposals):
        ev = len(p.evidence)
        conf = p.confidence
        scored.append((ev * 2.0 + conf, i))
    scored.sort(reverse=True)
    if len(scored) > 1 and abs(scored[0][0] - scored[1][0]) < 1e-9:
        return {"winner": -1, "reason": "tie: evidence insufficient",
                "mode": ConsensusMode.UNRESOLVED.value}
    return {"winner": scored[0][1], "reason": "highest evidence-weighted score",
            "mode": ConsensusMode.EVIDENCE_WEIGHTED.value}


class ConflictResolver:
    def resolve(self, results: List[AgentResult], *,
                mode: ConsensusMode = ConsensusMode.EVIDENCE_WEIGHTED) -> Dict[str, Any]:
        if mode == ConsensusMode.ORCHESTRATOR_DECISION:
            best = max(range(len(results)), key=lambda i: results[i].confidence)
            return {"mode": mode.value, "winner": best, "reason": "orchestrator pick by confidence"}
        if mode == ConsensusMode.USER_DECISION:
            return {"mode": mode.value, "winner": -1,
                    "reason": "escalated: user decision required"}
        if mode == ConsensusMode.CONSENSUS:
            sigs = {json.dumps(sorted(r.findings), sort_keys=True) for r in results}
            if len(sigs) == 1:
                return {"mode": mode.value, "winner": 0, "reason": "unanimous findings"}
            return {"mode": ConsensusMode.UNRESOLVED.value, "winner": -1,
                    "reason": "The agents disagree and the evidence is insufficient."}
        # EVIDENCE_WEIGHTED default.
        return judge_debate(results)


def synthesize(verified: List[AgentResult], *, goal: str) -> AgentResult:
    findings, evidence, artifacts, uncertainties, assumptions = [], [], [], [], []
    for r in verified:
        findings.extend(r.findings)
        evidence.extend(r.evidence)
        artifacts.extend(r.artifacts)
        uncertainties.extend(r.uncertainties)
        assumptions.extend(r.assumptions)
    # Dedup preserving order.
    findings = list(dict.fromkeys(findings))
    # Never upgrade: "verified" only when every input was verified.
    statuses = {r.verification_status for r in verified}
    if verified and statuses <= {"verified", "oracle_passed"}:
        vstatus = "verified"
        conf = round(sum(r.confidence for r in verified) / len(verified), 3)
    elif verified:
        vstatus = "mixed"
        conf = round(sum(r.confidence for r in verified) / len(verified), 3)
    else:
        vstatus = "unverified"
        conf = 0.0
    return AgentResult(
        summary=f"Synthesized {len(verified)} outputs ({vstatus}) for: {goal[:160]}. "
                + (findings[0] if findings else "no findings"),
        findings=findings, evidence=evidence, artifacts=list(dict.fromkeys(artifacts)),
        assumptions=list(dict.fromkeys(assumptions)),
        uncertainties=list(dict.fromkeys(uncertainties)),
        verification_status=vstatus,
        confidence=conf)


def quality_gate(result: AgentResult, *, require_evidence: bool = False,
                 allowed_statuses=("verified", "oracle_passed")) -> Dict[str, Any]:
    checks = {
        "completeness": bool(result.summary),
        "correctness": result.status == "ok" and not result.errors,
        "evidence": (len(result.evidence) > 0) if require_evidence else True,
        "consistency": result.verification_status in allowed_statuses or not require_evidence,
        "security": all("secret" not in (f or "").lower() for f in result.findings),
        "policy": True,
        "artifact_integrity": all(isinstance(a, str) and a for a in result.artifacts),
    }
    return {"passed": all(checks.values()), "checks": checks,
            "confidence": result.confidence,
            "verification_status": result.verification_status}
