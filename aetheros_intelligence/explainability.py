"""
Explainability Framework for AetherOS Intelligence Engine.

Every recommendation and decision includes:
    - Why: The reasoning behind the recommendation
    - Confidence: How confident the system is
    - Alternatives: Other approaches considered
    - Tradeoffs: Pros and cons of each option

Design Principles:
    - Every recommendation is explainable
    - Confidence is always quantified
    - Alternatives are always presented
    - Tradeoffs are always surfaced
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Explanation:
    """A structured explanation for a recommendation or decision.

    Attributes:
        recommendation_id: Unique identifier
        decision: The recommendation or decision
        reason: Why this decision was made
        confidence: Confidence score (0.0 - 1.0)
        alternatives: Other approaches considered
        tradeoffs: Pros and cons
        factors: Key factors that influenced the decision
        supporting_evidence: Evidence supporting this decision
        limitations: Known limitations or caveats
        timestamp: When the explanation was generated
    """
    recommendation_id: str = field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:8]}")
    decision: str = ""
    reason: str = ""
    confidence: float = 0.0
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    tradeoffs: List[Dict[str, Any]] = field(default_factory=list)
    factors: List[Dict[str, Any]] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class ExplainabilityFramework:
    """Provides structured explanations for all recommendations.

    Usage::

        framework = ExplainabilityFramework()

        # Explain a decision
        explanation = framework.explain(
            decision="Use PostgreSQL for primary storage",
            confidence=0.92,
            alternatives=[
                {"title": "MongoDB", "reason": "Document store, flexible schema"},
                {"title": "Redis", "reason": "In-memory, fast reads"},
            ],
            tradeoffs=[
                {"pro": "ACID compliance", "con": "Vertical scaling limits"},
            ],
        )

        # Explain a full recommendation object
        explanation = framework.explain_recommendation({
            "action": "Refactor auth module",
            "reason": "High cyclomatic complexity",
            "confidence": 0.85,
        })
    """

    def __init__(self) -> None:
        self._explanations: Dict[str, Explanation] = {}
        self._factor_weights = {
            "performance": 0.9,
            "security": 0.95,
            "reliability": 0.9,
            "maintainability": 0.8,
            "cost": 0.7,
            "time_to_market": 0.6,
            "developer_experience": 0.5,
        }

    # ------------------------------------------------------------------
    # Main explain methods
    # ------------------------------------------------------------------

    def explain(self,
                recommendation_id: Optional[str] = None,
                decision: Optional[str] = None,
                confidence: Optional[float] = None,
                alternatives: Optional[List[Dict[str, Any]]] = None,
                tradeoffs: Optional[List[Dict[str, Any]]] = None,
                factors: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate a structured explanation.

        Args:
            recommendation_id: ID of a stored recommendation
            decision: The recommendation text
            confidence: Confidence score
            alternatives: Alternative approaches
            tradeoffs: Pros and cons
            factors: Key influencing factors

        Returns:
            Structured explanation dict
        """
        # Look up stored recommendation if ID provided
        if recommendation_id and recommendation_id in self._explanations:
            stored = self._explanations[recommendation_id]
            return self._to_dict(stored)

        # Generate new explanation
        alt = alternatives or []
        trd = tradeoffs or []
        fac = factors or self._derive_factors(decision or "")

        explanation = Explanation(
            decision=decision or "",
            confidence=confidence or self._estimate_confidence(decision or "", factors=fac),
            alternatives=alt,
            tradeoffs=trd,
            factors=fac,
            reason=self._generate_reason(decision or "", fac, trd, alt),
            supporting_evidence=self._gather_evidence(decision or ""),
            limitations=self._identify_limitations(decision or "", confidence),
        )

        self._explanations[explanation.recommendation_id] = explanation

        result = self._to_dict(explanation)
        result["fresh"] = True
        return result

    def explain_recommendation(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a full explanation from a recommendation object.

        Expected recommendation keys:
            - action: The recommended action
            - reason: Why it's recommended (optional)
            - confidence: Confidence level (optional)
            - context: Additional context (optional)

        Args:
            recommendation: Dict with recommendation fields

        Returns:
            Enhanced recommendation with explanation fields
        """
        action = recommendation.get("action", "")
        reason = recommendation.get("reason", "")
        confidence = recommendation.get("confidence")

        return self.explain(
            decision=action,
            confidence=confidence,
            factors=self._derive_factors(action),
            alternatives=self._generate_alternatives(action),
            tradeoffs=self._derive_tradeoffs(action),
        )

    # ------------------------------------------------------------------
    # Explanation generation helpers
    # ------------------------------------------------------------------

    def _generate_reason(self, decision: str,
                         factors: List[Dict[str, Any]],
                         tradeoffs: List[Dict[str, Any]],
                         alternatives: List[Dict[str, Any]]) -> str:
        """Generate a human-readable reason for the decision."""
        parts = []

        # Key factors
        if factors:
            top_factor = max(factors, key=lambda f: f.get("weight", 0))
            parts.append(
                f"Primary factor: {top_factor.get('name', 'unknown')} "
                f"(weight: {top_factor.get('weight', 0.5):.1f})"
            )

        # Tradeoff summary
        if tradeoffs:
            pros = [t.get("pro", "") for t in tradeoffs if t.get("pro")]
            if pros:
                parts.append(f"Key benefits: {'; '.join(pros[:2])}")

        # Alternative comparison
        if alternatives:
            alt_count = len(alternatives)
            parts.append(
                f"Evaluated {alt_count} alternative{'s' if alt_count > 1 else ''}"
            )

        return " | ".join(parts) or "Based on analysis of requirements and constraints."

    def _estimate_confidence(self, decision: str,
                             factors: Optional[List[Dict[str, Any]]] = None) -> float:
        """Estimate confidence based on factors and decision characteristics."""
        if factors:
            weighted = sum(
                f.get("weight", 0.5) * self._factor_weights.get(
                    f.get("name", "").lower(), 0.5
                )
                for f in factors
            )
            return round(min(max(weighted / len(factors), 0.1), 0.99), 2)

        # Heuristic based on decision text
        score = 0.7
        if len(decision) > 100:
            score += 0.1
        if any(w in decision.lower() for w in ["standard", "proven", "established"]):
            score += 0.1
        if any(w in decision.lower() for w in ["experimental", "maybe", "try"]):
            score -= 0.1
        return round(min(max(score, 0.1), 0.99), 2)

    def _derive_factors(self, decision: str) -> List[Dict[str, Any]]:
        """Derive influencing factors from a decision text."""
        factors = []

        factor_map = {
            "performance": ["fast", "speed", "perform", "latency", "throughput"],
            "security": ["secure", "security", "auth", "permission", "encrypt"],
            "reliability": ["reliable", "stable", "robust", "fault", "resilient"],
            "maintainability": ["maintain", "clean", "modular", "refactor"],
            "cost": ["cost", "budget", "price", "expensive", "cheap"],
            "compatibility": ["compat", "support", "legacy", "backward"],
            "scalability": ["scale", "grow", "load", "concurrent"],
        }

        decision_lower = decision.lower()
        for factor, keywords in factor_map.items():
            if any(kw in decision_lower for kw in keywords):
                weight = self._factor_weights.get(factor, 0.7)
                factors.append({
                    "name": factor.capitalize(),
                    "weight": weight,
                    "description": f"Factor identified from keywords",
                })

        if not factors:
            factors.append({
                "name": "General analysis",
                "weight": 0.6,
                "description": "Based on overall requirements assessment",
            })

        return factors

    def _derive_tradeoffs(self, decision: str) -> List[Dict[str, Any]]:
        """Derive common tradeoffs for a decision."""
        tradeoffs = []

        if "api" in decision.lower():
            tradeoffs.append({
                "pro": "Clear interface contract",
                "con": "Coupling between services",
            })
            tradeoffs.append({
                "pro": "Independent deployability",
                "con": "Network latency overhead",
            })

        if "database" in decision.lower():
            tradeoffs.append({
                "pro": "Data persistence and integrity",
                "con": "Operational complexity",
            })

        if "framework" in decision.lower():
            tradeoffs.append({
                "pro": "Faster development",
                "con": "Vendor lock-in risk",
            })

        if "cloud" in decision.lower():
            tradeoffs.append({
                "pro": "Elastic scalability",
                "con": "Higher variable costs",
            })

        if not tradeoffs:
            tradeoffs.append({
                "pro": "Alignment with requirements",
                "con": "Potential tradeoffs not fully analyzed",
            })

        return tradeoffs

    def _generate_alternatives(self, decision: str) -> List[Dict[str, Any]]:
        """Generate alternative approaches."""
        alternatives = []

        if "database" in decision.lower():
            alternatives.append({
                "title": "Use managed database service",
                "pro": "Reduced ops overhead",
                "con": "Higher cost, vendor dependency",
            })
            alternatives.append({
                "title": "Use in-memory cache layer",
                "pro": "Dramatic read performance",
                "con": "Data loss on restart",
            })

        if "deploy" in decision.lower():
            alternatives.append({
                "title": "Use CI/CD pipeline",
                "pro": "Automated, repeatable deployments",
                "con": "Setup complexity",
            })

        return alternatives

    def _gather_evidence(self, decision: str) -> List[str]:
        """Gather supporting evidence."""
        evidence = []
        if any(w in decision.lower() for w in ["standard", "proven", "established"]):
            evidence.append("Follows industry standard practices")
        if any(w in decision.lower() for w in ["documented", "known"]):
            evidence.append("Based on documented best practices")
        return evidence

    def _identify_limitations(self, decision: str,
                              confidence: Optional[float]) -> List[str]:
        """Identify known limitations."""
        limitations = []
        if confidence is not None and confidence < 0.8:
            limitations.append("Limited confidence in this recommendation")
        if len(decision) < 50:
            limitations.append("Limited detail in the recommendation context")
        return limitations

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _to_dict(self, explanation: Explanation) -> Dict[str, Any]:
        """Convert an Explanation to a dict."""
        return {
            "recommendation_id": explanation.recommendation_id,
            "decision": explanation.decision,
            "reason": explanation.reason,
            "confidence": explanation.confidence,
            "alternatives": explanation.alternatives,
            "tradeoffs": explanation.tradeoffs,
            "factors": explanation.factors,
            "supporting_evidence": explanation.supporting_evidence,
            "limitations": explanation.limitations,
            "timestamp": explanation.timestamp,
        }

    def get_explanation(self, recommendation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored explanation by ID."""
        explanation = self._explanations.get(recommendation_id)
        return self._to_dict(explanation) if explanation else None

    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent explanations."""
        items = list(self._explanations.values())
        items.reverse()
        return [self._to_dict(e) for e in items[:limit]]
