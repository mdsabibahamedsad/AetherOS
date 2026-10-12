"""
Critic Agent — challenges assumptions, verifies reasoning, detects hallucinations,
and requests additional evidence for claims made during execution.

The Critic serves as the system's "skeptic" - it doesn't accept outputs
at face value but instead:
  - Identifies unstated assumptions in plans and reasoning
  - Verifies logical consistency and soundness
  - Detects potential hallucinations (unsupported claims, fabricated sources)
  - Requests evidence for unsupported assertions
  - Evaluates confidence levels for critical decisions
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class CriticismSeverity(enum.IntEnum):
    QUESTION = 0
    CONCERN = 1
    CHALLENGE = 2
    REJECTION = 3


class CriticismCategory(enum.Enum):
    ASSUMPTION = "assumption"
    HALLUCINATION = "hallucination"
    LOGICAL_FALLACY = "logical_fallacy"
    INCOMPLETE_EVIDENCE = "incomplete_evidence"
    CONTRADICTION = "contradiction"
    BIAS = "bias"
    UNCERTAINTY = "uncertainty"
    SOURCE_QUALITY = "source_quality"


@dataclass
class Criticism:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    category: CriticismCategory = CriticismCategory.ASSUMPTION
    severity: CriticismSeverity = CriticismSeverity.CONCERN
    target: str = ""
    claim: str = ""
    criticism: str = ""
    evidence_requested: str = ""
    resolved: bool = False
    resolution: str = ""
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None


@dataclass
class ReasoningTrace:
    premise: str = ""
    conclusion: str = ""
    steps: List[str] = field(default_factory=list)
    confidence: float = 1.0
    assumptions: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)


class CriticAgent:
    """Challenges assumptions, detects hallucinations, verifies reasoning.

    Provides structured criticism of agent outputs to improve quality
    and correctness.

    Usage:
        critic = CriticAgent(event_bus)
        criticisms = critic.analyze_claim("The sky is green because of atmospheric scattering")
        criticisms = critic.verify_reasoning(reasoning_trace)
        criticisms = critic.check_hallucinations(content, known_facts)
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._criticisms: Dict[str, Criticism] = {}
        self._known_facts: Dict[str, float] = {}
        self._reasoning_traces: Dict[str, ReasoningTrace] = {}
        self._suspicious_patterns: List[str] = [
            "according to my research",
            "as we all know",
            "it is well known that",
            "studies show that",
            "research indicates",
            "experts agree",
            "it's obvious that",
            "clearly",
            "undoubtedly",
            "without a doubt",
        ]

    # ------------------------------------------------------------------
    # Claim analysis
    # ------------------------------------------------------------------

    def analyze_claim(self, claim: str, context: Dict[str, Any] = None) -> Criticism:
        context = context or {}
        findings = []

        claim_lower = claim.lower()

        for pattern in self._suspicious_patterns:
            if pattern in claim_lower:
                findings.append(Criticism(
                    category=CriticismCategory.HALLUCINATION,
                    severity=CriticismSeverity.CONCERN,
                    target="claim",
                    claim=claim[:200],
                    criticism=f"Uses hedge phrase '{pattern}' which may indicate unsupported assertion",
                    evidence_requested=f"Provide specific sources that support: '{claim[:100]}'",
                ))

        if context.get("domain"):
            domain = context["domain"].lower()
            domain_keywords = {
                "science": ["prove", "definitely", "always", "never"],
                "medicine": ["cure", "guaranteed", "miracle", "breakthrough"],
                "technology": ["revolutionary", "disruptive", "game-changing", "perfect"],
            }
            keywords = domain_keywords.get(domain, [])
            for kw in keywords:
                if kw in claim_lower:
                    findings.append(Criticism(
                        category=CriticismCategory.BIAS,
                        severity=CriticismSeverity.QUESTION,
                        target="claim",
                        claim=claim[:200],
                        criticism=f"Uses exaggerated language ('{kw}') common in {domain} context",
                        evidence_requested=f"Provide specific, measurable evidence for the claim",
                    ))

        if "always" in claim_lower or "never" in claim_lower:
            findings.append(Criticism(
                category=CriticismCategory.LOGICAL_FALLACY,
                severity=CriticismSeverity.CONCERN,
                target="claim",
                claim=claim[:200],
                criticism="Uses absolute terms ('always'/'never') which may indicate overgeneralization",
                evidence_requested="Specify conditions and edge cases for this claim",
            ))

        if not findings:
            findings.append(Criticism(
                category=CriticismCategory.UNCERTAINTY,
                severity=CriticismSeverity.QUESTION,
                target="claim",
                claim=claim[:200],
                criticism="No obvious issues detected, but claim should be verified against known facts",
                evidence_requested="Provide sources or reasoning chain for this claim",
            ))

        criticism = findings[0]
        with self._lock:
            self._criticisms[criticism.id] = criticism
        return criticism

    # ------------------------------------------------------------------
    # Hallucination detection
    # ------------------------------------------------------------------

    def check_hallucinations(self, content: str,
                             known_facts: Dict[str, Any] = None) -> List[Criticism]:
        context_facts = dict(self._known_facts)
        if known_facts:
            context_facts.update(known_facts)

        findings: List[Criticism] = []
        content_lower = content.lower()

        for fact_key, fact_value in context_facts.items():
            if isinstance(fact_value, str) and fact_value.lower() in content_lower:
                continue
            if isinstance(fact_value, (int, float)) and str(fact_value) in content:
                continue
            if fact_key.lower() in content_lower:
                findings.append(Criticism(
                    category=CriticismCategory.HALLUCINATION,
                    severity=CriticismSeverity.CHALLENGE,
                    target="content",
                    claim=f"Content references '{fact_key}' but may contradict known facts",
                    criticism=f"Known fact: {fact_key}={fact_value}. Content should be verified.",
                    evidence_requested=f"Verify claim against known value for '{fact_key}'",
                ))

        lines = content.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                if len(stripped) > 200 and "," not in stripped[100:]:
                    findings.append(Criticism(
                        category=CriticismCategory.INCOMPLETE_EVIDENCE,
                        severity=CriticismSeverity.CONCERN,
                        target="content",
                        claim=stripped[:150],
                        criticism=f"Line {i+1}: long unsupported bullet point may be hallucinated",
                        evidence_requested=f"Provide specific citations for the claim on line {i+1}",
                    ))

        return findings

    def add_known_fact(self, key: str, value: Any,
                       confidence: float = 1.0) -> None:
        with self._lock:
            self._known_facts[key] = value

    # ------------------------------------------------------------------
    # Reasoning verification
    # ------------------------------------------------------------------

    def verify_reasoning(self, trace: ReasoningTrace) -> List[Criticism]:
        findings: List[Criticism] = []
        self._reasoning_traces[trace.premise[:100]] = trace

        if not trace.steps:
            findings.append(Criticism(
                category=CriticismCategory.LOGICAL_FALLACY,
                severity=CriticismSeverity.CHALLENGE,
                target="reasoning",
                claim=trace.conclusion[:200],
                criticism="Reasoning has no intermediate steps - gap between premise and conclusion",
                evidence_requested="Break down the reasoning into explicit logical steps",
            ))

        if trace.assumptions:
            for assumption in trace.assumptions:
                if "assume" in assumption.lower() or "assuming" in assumption.lower():
                    findings.append(Criticism(
                        category=CriticismCategory.ASSUMPTION,
                        severity=CriticismSeverity.QUESTION,
                        target="reasoning",
                        claim=assumption[:200],
                        criticism=f"States an assumption explicitly: '{assumption[:100]}'",
                        evidence_requested=f"Justify or verify this assumption: {assumption[:100]}",
                    ))

        if trace.gaps:
            for gap in trace.gaps:
                findings.append(Criticism(
                    category=CriticismCategory.INCOMPLETE_EVIDENCE,
                    severity=CriticismSeverity.CONCERN,
                    target="reasoning",
                    claim=gap[:200],
                    criticism=f"Identified gap in reasoning: {gap[:100]}",
                    evidence_requested=f"Fill the reasoning gap: {gap[:100]}",
                ))

        if trace.confidence < 0.5:
            findings.append(Criticism(
                category=CriticismCategory.UNCERTAINTY,
                severity=CriticismSeverity.CONCERN,
                target="reasoning",
                claim=trace.conclusion[:200],
                criticism=f"Low confidence reasoning ({trace.confidence:.2f})",
                evidence_requested="Provide additional evidence to increase confidence",
            ))

        if not findings:
            findings.append(Criticism(
                category=CriticismCategory.LOGICAL_FALLACY,
                severity=CriticismSeverity.QUESTION,
                target="reasoning",
                claim=trace.conclusion[:200],
                criticism="Check for hidden assumptions in the reasoning chain",
                evidence_requested="List all assumptions made during reasoning",
            ))

        for f in findings:
            with self._lock:
                self._criticisms[f.id] = f
        return findings

    # ------------------------------------------------------------------
    # Contradiction detection
    # ------------------------------------------------------------------

    def find_contradictions(self, statements: List[str]) -> List[Criticism]:
        findings: List[Criticism] = []
        for i, s1 in enumerate(statements):
            for j, s2 in enumerate(statements):
                if i >= j:
                    continue
                contradiction = self._check_contradiction(s1, s2)
                if contradiction:
                    findings.append(Criticism(
                        category=CriticismCategory.CONTRADICTION,
                        severity=CriticismSeverity.CHALLENGE,
                        target="statements",
                        claim=f"Statement {i} vs Statement {j}",
                        criticism=f"Contradiction detected: '{s1[:60]}' vs '{s2[:60]}'",
                        evidence_requested="Reconcile or clarify the contradiction",
                    ))
        return findings

    def _check_contradiction(self, s1: str, s2: str) -> bool:
        negation_pairs = [
            ("is", "is not"), ("is", "isn't"), ("are", "are not"),
            ("can", "cannot"), ("can", "can't"), ("will", "will not"),
            ("has", "has no"), ("have", "have no"),
            ("supports", "does not support"),
            ("enabled", "disabled"),
            ("true", "false"),
            ("valid", "invalid"),
            ("include", "exclude"),
            ("uses", "does not use"),
        ]
        s1_lower = s1.lower()
        s2_lower = s2.lower()
        for pos, neg in negation_pairs:
            if pos in s1_lower and neg in s2_lower:
                return True
            if neg in s1_lower and pos in s2_lower:
                return True
        return False

    # ------------------------------------------------------------------
    # Evidence evaluation
    # ------------------------------------------------------------------

    def evaluate_evidence(self, claim: str,
                          evidence: List[str]) -> List[Criticism]:
        findings: List[Criticism] = []
        if not evidence:
            findings.append(Criticism(
                category=CriticismCategory.INCOMPLETE_EVIDENCE,
                severity=CriticismSeverity.CHALLENGE,
                target="evidence",
                claim=claim[:200],
                criticism="No evidence provided for claim",
                evidence_requested="Provide at least one piece of supporting evidence",
            ))
            return findings

        for i, ev in enumerate(evidence):
            if len(ev) < 20:
                findings.append(Criticism(
                    category=CriticismCategory.SOURCE_QUALITY,
                    severity=CriticismSeverity.CONCERN,
                    target="evidence",
                    claim=ev[:200],
                    criticism=f"Evidence #{i+1} is too brief ({len(ev)} chars) to be meaningful",
                    evidence_requested=f"Provide detailed evidence for claim: {claim[:80]}",
                ))

        return findings

    # ------------------------------------------------------------------
    # Quality analysis
    # ------------------------------------------------------------------

    def analyze_plan_assumptions(self, plan: Dict[str, Any]) -> List[Criticism]:
        findings: List[Criticism] = []
        steps = plan.get("steps", [])

        if not plan.get("resource_estimate"):
            findings.append(Criticism(
                category=CriticismCategory.ASSUMPTION,
                severity=CriticismSeverity.QUESTION,
                target="plan",
                claim=plan.get("goal", "")[:200],
                criticism="Plan has no resource estimate - assumes unlimited resources",
                evidence_requested="Add estimated time, compute, and personnel requirements",
            ))

        for i, step in enumerate(steps):
            description = step.get("description", "")
            if "assume" in description.lower() or "assuming" in description.lower():
                findings.append(Criticism(
                    category=CriticismCategory.ASSUMPTION,
                    severity=CriticismSeverity.CONCERN,
                    target="plan_step",
                    claim=description[:200],
                    criticism=f"Step {i+1} contains an explicit assumption: '{description[:80]}'",
                    evidence_requested=f"Verify the assumption in step {i+1}",
                ))

        return findings

    # ------------------------------------------------------------------
    # Criticism lifecycle
    # ------------------------------------------------------------------

    def get_criticism(self, criticism_id: str) -> Optional[Criticism]:
        with self._lock:
            return self._criticisms.get(criticism_id)

    def resolve_criticism(self, criticism_id: str,
                          resolution: str) -> bool:
        with self._lock:
            criticism = self._criticisms.get(criticism_id)
            if criticism is None or criticism.resolved:
                return False
            criticism.resolved = True
            criticism.resolution = resolution
            criticism.resolved_at = time.time()
        return True

    def list_criticisms(self, category: CriticismCategory = None,
                        severity: CriticismSeverity = None,
                        unresolved_only: bool = False,
                        limit: int = 100) -> List[Criticism]:
        with self._lock:
            criticisms = list(self._criticisms.values())
        if category:
            criticisms = [c for c in criticisms if c.category == category]
        if severity:
            criticisms = [c for c in criticisms if c.severity == severity]
        if unresolved_only:
            criticisms = [c for c in criticisms if not c.resolved]
        criticisms.sort(key=lambda c: (c.severity, c.created_at), reverse=True)
        return criticisms[:limit]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._criticisms)
            resolved = sum(1 for c in self._criticisms.values() if c.resolved)
            by_category: Dict[str, int] = {}
            for c in self._criticisms.values():
                by_category[c.category.value] = by_category.get(c.category.value, 0) + 1
        return {
            "total_criticisms": total,
            "resolved": resolved,
            "unresolved": total - resolved,
            "by_category": by_category,
            "known_facts": len(self._known_facts),
        }