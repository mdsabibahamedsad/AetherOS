"""Self-Correction & Verification Loops (Phase 60).

Advanced self-correction and verification:
- Automated fact-checking
- Consistency checking
- Iterative refinement
- Error detection and correction
- Confidence calibration
- Verification loops with feedback
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from collections import defaultdict

from agent.multimodal.production import MetricsCollector
from agent.multimodal.provenance import ProvenanceTracker, EvidenceRef

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    VERIFIED = "verified"
    REFUTED = "refuted"
    UNCERTAIN = "uncertain"
    CONFLICTING = "conflicting"
    PENDING = "pending"


class CorrectionStrategy(Enum):
    REWRITE = "rewrite"              # Rewrite the claim
    CLARIFY = "clarify"              # Add clarification
    RETRACT = "retract"              # Retract the claim
    SUPPLEMENT = "supplement"        # Add missing information
    RESTRUCTURE = "restructure"      # Restructure the argument


@dataclass
class Claim:
    """A claim to be verified."""
    claim_id: str
    content: str
    source: str  # What generated this claim
    context: Dict = field(default_factory=dict)
    confidence: float = 0.5
    status: VerificationStatus = VerificationStatus.PENDING
    evidence: List[str] = field(default_factory=list)  # EvidenceRef IDs
    created_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Result of verifying a claim."""
    claim_id: str
    status: VerificationStatus
    confidence: float
    evidence_for: List[str] = field(default_factory=list)
    evidence_against: List[str] = field(default_factory=list)
    reasoning: str = ""
    corrections: List[str] = field(default_factory=list)
    verified_at: float = field(default_factory=time.time)


@dataclass
class CorrectionAction:
    """A correction action to apply."""
    action_id: str
    claim_id: str
    strategy: CorrectionStrategy
    original_text: str
    corrected_text: str
    rationale: str
    confidence: float
    applied: bool = False
    applied_at: Optional[float] = None


class FactChecker:
    """Fact-checking engine for verifying claims against evidence."""

    def __init__(
        self,
        evidence_store: Optional[Any] = None,
        llm_call: Optional[Callable[[str], str]] = None,
        similarity_threshold: float = 0.7,
    ):
        self.evidence_store = evidence_store
        self.llm_call = llm_call or self._mock_llm
        self.similarity_threshold = similarity_threshold
        self.metrics = MetricsCollector("fact_checker")

    def _mock_llm(self, prompt: str) -> str:
        return "Based on the evidence, the claim appears to be supported."

    def check_claim(
        self,
        claim: Claim,
        evidence: List[str],  # Evidence text/content
    ) -> VerificationResult:
        """Check a single claim against evidence."""
        start = time.time()

        # Find relevant evidence
        relevant_evidence = self._find_relevant_evidence(claim.content, evidence)

        # Use LLM to verify
        prompt = self._build_verification_prompt(claim, relevant_evidence)
        response = self.llm_call(prompt)

        # Parse result
        result = self._parse_verification(claim.claim_id, response, relevant_evidence)

        self.metrics.counter("fact_checks", labels={"status": result.status.value})
        self.metrics.histogram("fact_check_latency_ms", (time.time() - start) * 1000)

        return result

    def _find_relevant_evidence(self, claim: str, evidence: List[str]) -> List[str]:
        """Find evidence relevant to the claim using simple text overlap."""
        claim_words = set(claim.lower().split())
        scored = []
        for ev in evidence:
            ev_words = set(ev.lower().split())
            if not claim_words or not ev_words:
                continue
            overlap = len(claim_words & ev_words) / len(claim_words | ev_words)
            if overlap >= self.similarity_threshold:
                scored.append((overlap, ev))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:10]]

    def _build_verification_prompt(self, claim: Claim, evidence: List[str]) -> str:
        ev_text = "\n---\n".join(evidence) if evidence else "No evidence provided."
        return f"""Verify the following claim:

Claim: {claim.content}
Context: {claim.context}
Source: {claim.source}

Evidence:
{ev_text}

Determine if the claim is VERIFIED, REFUTED, UNCERTAIN, or CONFLICTING.
Provide reasoning and list supporting/refuting evidence.
Format:
STATUS: [VERIFIED/REFUTED/UNCERTAIN/CONFLICTING]
CONFIDENCE: [0.0-1.0]
REASONING: [explanation]
EVIDENCE_FOR: [list]
EVIDENCE_AGAINST: [list]"""

    def _parse_verification(
        self,
        claim_id: str,
        response: str,
        evidence: List[str],
    ) -> VerificationResult:
        status = VerificationStatus.UNCERTAIN
        confidence = 0.5
        reasoning = ""
        evidence_for = []
        evidence_against = []

        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("STATUS:"):
                status_str = line.replace("STATUS:", "").strip().upper()
                try:
                    status = VerificationStatus(status_str.lower())
                except ValueError:
                    pass
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                except ValueError:
                    pass
            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()
            elif line.startswith("EVIDENCE_FOR:"):
                evidence_for = [e.strip() for e in line.replace("EVIDENCE_FOR:", "").split(",") if e.strip()]
            elif line.startswith("EVIDENCE_AGAINST:"):
                evidence_against = [e.strip() for e in line.replace("EVIDENCE_AGAINST:", "").split(",") if e.strip()]

        return VerificationResult(
            claim_id=claim_id,
            status=status,
            confidence=max(0.0, min(1.0, confidence)),
            evidence_for=evidence_for,
            evidence_against=evidence_against,
            reasoning=reasoning,
        )

    def batch_check(self, claims: List[Claim], evidence: List[str]) -> List[VerificationResult]:
        """Check multiple claims."""
        results = []
        for claim in claims:
            result = self.check_claim(claim, evidence)
            results.append(result)
        return results


class ConsistencyChecker:
    """Checks for logical consistency across claims."""

    def __init__(self, llm_call: Optional[Callable[[str], str]] = None):
        self.llm_call = llm_call or self._mock_llm
        self.metrics = MetricsCollector("consistency_checker")

    def _mock_llm(self, prompt: str) -> str:
        return "CONSISTENT: The claims do not contradict each other."

    def check_consistency(self, claims: List[Claim]) -> Dict[str, Any]:
        """Check a set of claims for internal consistency."""
        if len(claims) < 2:
            return {"consistent": True, "conflicts": [], "message": "Single claim, trivially consistent"}

        # Build prompt with all claims
        claims_text = "\n".join(f"{i+1}. {c.content}" for i, c in enumerate(claims))
        prompt = f"""Analyze the following claims for logical consistency:

{claims_text}

Are these claims logically consistent with each other? Identify any contradictions.
Format:
CONSISTENT: [true/false]
CONFLICTS: [list of conflicting claim indices and explanation]
REASONING: [explanation]"""

        response = self.llm_call(prompt)
        return self._parse_consistency(response)

    def _parse_consistency(self, response: str) -> Dict[str, Any]:
        consistent = True
        conflicts = []
        reasoning = ""

        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("CONSISTENT:"):
                consistent = line.replace("CONSISTENT:", "").strip().lower() == "true"
            elif line.startswith("CONFLICTS:"):
                conflicts_text = line.replace("CONFLICTS:", "").strip()
                # Simple parsing
                conflicts = [c.strip() for c in conflicts_text.split(";") if c.strip()]
            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()

        return {
            "consistent": consistent,
            "conflicts": conflicts,
            "reasoning": reasoning,
        }

    def find_contradictions(self, claims: List[Claim]) -> List[Tuple[int, int, str]]:
        """Find pairwise contradictions between claims."""
        contradictions = []
        for i, claim_a in enumerate(claims):
            for j, claim_b in enumerate(claims[i+1:], i+1):
                # Check for direct contradiction using LLM
                prompt = f"""Do these two claims contradict each other?

Claim A: {claim_a.content}
Claim B: {claim_b.content}

Answer YES or NO with brief explanation."""
                response = self.llm_call(prompt)
                if "YES" in response.upper():
                    contradictions.append((i, j, response))
        return contradictions


class IterativeRefiner:
    """Iteratively refines outputs through self-correction loops."""

    def __init__(
        self,
        generator: Callable[[str, Dict], str],
        critic: Callable[[str, Dict], Dict],
        max_iterations: int = 5,
        quality_threshold: float = 0.8,
    ):
        self.generator = generator
        self.critic = critic
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold
        self.metrics = MetricsCollector("iterative_refiner")

    def refine(
        self,
        initial_input: str,
        context: Optional[Dict] = None,
        initial_output: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Iteratively refine output until quality threshold met."""
        current_output = initial_output or self.generator(initial_input, context or {})
        history = []

        for iteration in range(self.max_iterations):
            # Critique current output
            critique = self.critic(current_output, {"input": initial_input, "context": context or {}})

            quality_score = critique.get("quality_score", 0.0)
            issues = critique.get("issues", [])
            suggestions = critique.get("suggestions", [])

            history.append({
                "iteration": iteration + 1,
                "output": current_output,
                "quality_score": quality_score,
                "issues": issues,
                "suggestions": suggestions,
            })

            if quality_score >= self.quality_threshold:
                return {
                    "final_output": current_output,
                    "iterations": iteration + 1,
                    "final_quality": quality_score,
                    "history": history,
                    "converged": True,
                }

            # Generate improved version
            refinement_prompt = self._build_refinement_prompt(
                current_output, critique, initial_input
            )
            current_output = self.generator(refinement_prompt, context or {})

        # Max iterations reached
        return {
            "final_output": current_output,
            "iterations": self.max_iterations,
            "final_quality": quality_score,
            "history": history,
            "converged": False,
        }

    def _build_refinement_prompt(
        self,
        current: str,
        critique: Dict,
        original: str,
    ) -> str:
        issues = "\n".join(f"- {i}" for i in critique.get("issues", []))
        suggestions = "\n".join(f"- {s}" for s in critique.get("suggestions", []))

        return f"""Original task: {original}

Current output:
{current}

Critique:
Issues:
{issues}

Suggestions:
{suggestions}

Please produce an improved version addressing all issues."""

    def refine_with_verification(
        self,
        initial_input: str,
        verifier: Callable[[str], Dict],
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Refine with verification at each step."""
        current_output = self.generator(initial_input, context or {})
        history = []

        for iteration in range(self.max_iterations):
            verification = verifier(current_output)

            if verification.get("verified", False):
                return {
                    "final_output": current_output,
                    "iterations": iteration + 1,
                    "verified": True,
                    "history": history,
                }

            issues = verification.get("issues", [])
            if not issues:
                break

            refinement_prompt = f"Fix these issues in the output:\n{issues}\n\nCurrent:\n{current_output}"
            current_output = self.generator(refinement_prompt, context or {})
            history.append({
                "iteration": iteration + 1,
                "output": current_output,
                "verification": verification,
            })

        return {
            "final_output": current_output,
            "iterations": self.max_iterations,
            "verified": False,
            "history": history,
        }


class ErrorDetector:
    """Detects various types of errors in generated content."""

    def __init__(self, llm_call: Optional[Callable[[str], str]] = None):
        self.llm_call = llm_call or self._mock_llm
        self.metrics = MetricsCollector("error_detector")

    def _mock_llm(self, prompt: str) -> str:
        return "No errors detected."

    def detect_errors(
        self,
        text: str,
        checks: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Detect various types of errors in text."""
        all_checks = [
            "factual_accuracy",
            "logical_consistency",
            "completeness",
            "clarity",
            "bias",
            "hallucination",
            "citation_accuracy",
        ]
        active_checks = checks or all_checks

        results = {}
        for check in active_checks:
            prompt = self._build_check_prompt(text, check)
            response = self.llm_call(prompt)
            results[check] = self._parse_check_result(response)

        # Overall assessment
        has_errors = any(r.get("has_issues", False) for r in results.values())
        severity = "high" if any(r.get("severity") == "high" for r in results.values()) else "low"

        return {
            "has_errors": has_errors,
            "severity": severity,
            "checks": results,
            "summary": self._summarize_errors(results),
        }

    def _build_check_prompt(self, text: str, check_type: str) -> str:
        check_prompts = {
            "factual_accuracy": "Check for factual errors in the text. Identify any statements that are factually incorrect.",
            "logical_consistency": "Check for logical contradictions or inconsistencies in the text.",
            "completeness": "Check if the text is complete or missing important information.",
            "clarity": "Check if the text is clear, well-structured, and easy to understand.",
            "bias": "Check for potential bias or unfair representation in the text.",
            "hallucination": "Check for fabricated or unsupported claims in the text.",
            "citation_accuracy": "Check if citations and references are accurate and properly formatted.",
        }
        prompt_text = check_prompts.get(check_type, "Check for issues in the text.")

        return f"""{prompt_text}

Text to check:
{text}

Format:
ISSUES_FOUND: [true/false]
SEVERITY: [high/medium/low]
ISSUES: [list of specific issues]
SUGGESTIONS: [list of improvement suggestions]"""

    def _parse_check_result(self, response: str) -> Dict[str, Any]:
        issues_found = False
        severity = "low"
        issues = []
        suggestions = []

        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("ISSUES_FOUND:"):
                issues_found = line.replace("ISSUES_FOUND:", "").strip().lower() == "true"
            elif line.startswith("SEVERITY:"):
                severity = line.replace("SEVERITY:", "").strip().lower()
            elif line.startswith("ISSUES:"):
                issues = [i.strip() for i in line.replace("ISSUES:", "").split(";") if i.strip()]
            elif line.startswith("SUGGESTIONS:"):
                suggestions = [s.strip() for s in line.replace("SUGGESTIONS:", "").split(";") if s.strip()]

        return {
            "has_issues": issues_found,
            "severity": severity,
            "issues": issues,
            "suggestions": suggestions,
        }

    def _summarize_errors(self, results: Dict) -> str:
        total_issues = sum(len(r.get("issues", [])) for r in results.values())
        high_severity = sum(1 for r in results.values() if r.get("severity") == "high")
        return f"Found {total_issues} total issues across {len(results)} checks ({high_severity} high severity)"


class CorrectionEngine:
    """Applies corrections based on verification and error detection."""

    def __init__(
        self,
        llm_call: Optional[Callable[[str], str]] = None,
        fact_checker: Optional[FactChecker] = None,
    ):
        self.llm_call = llm_call or self._mock_llm
        self.fact_checker = fact_checker or FactChecker()
        self.metrics = MetricsCollector("correction_engine")

    def _mock_llm(self, prompt: str) -> str:
        return "Corrected version of the text with issues fixed."

    def correct_claim(
        self,
        claim: Claim,
        verification: VerificationResult,
    ) -> CorrectionAction:
        """Generate a correction for a verified claim."""
        if verification.status == VerificationStatus.VERIFIED:
            return CorrectionAction(
                action_id=f"corr_{uuid.uuid4().hex[:8]}",
                claim_id=claim.claim_id,
                strategy=CorrectionStrategy.REWRITE,
                original_text=claim.content,
                corrected_text=claim.content,
                rationale="Claim verified, no correction needed",
                confidence=1.0,
                applied=True,
                applied_at=time.time(),
            )

        # Generate correction based on verification
        if verification.status == VerificationStatus.REFUTED:
            strategy = CorrectionStrategy.RETRACT
            rationale = f"Claim refuted: {verification.reasoning}"
        elif verification.status == VerificationStatus.CONFLICTING:
            strategy = CorrectionStrategy.CLARIFY
            rationale = f"Conflicting evidence: {verification.reasoning}"
        else:
            strategy = CorrectionStrategy.SUPPLEMENT
            rationale = f"Insufficient evidence: {verification.reasoning}"

        # Generate corrected text
        prompt = self._build_correction_prompt(claim, verification, strategy)
        corrected_text = self.llm_call(prompt)

        action = CorrectionAction(
            action_id=f"corr_{uuid.uuid4().hex[:8]}",
            claim_id=claim.claim_id,
            strategy=strategy,
            original_text=claim.content,
            corrected_text=corrected_text,
            rationale=rationale,
            confidence=verification.confidence,
        )

        self.metrics.counter("corrections", labels={"strategy": strategy.value})
        return action

    def _build_correction_prompt(
        self,
        claim: Claim,
        verification: VerificationResult,
        strategy: CorrectionStrategy,
    ) -> str:
        strategy_prompts = {
            CorrectionStrategy.REWRITE: "Rewrite the claim to be accurate based on the evidence.",
            CorrectionStrategy.CLARIFY: "Clarify the claim to resolve conflicts.",
            CorrectionStrategy.RETRACT: "Retract the claim and provide a corrected version.",
            CorrectionStrategy.SUPPLEMENT: "Add missing context to make the claim accurate.",
            CorrectionStrategy.RESTRUCTURE: "Restructure the argument to be logically sound.",
        }

        return f"""Original claim: {claim.content}
Verification status: {verification.status.value}
Verification reasoning: {verification.reasoning}
Correction strategy: {strategy.value}
Guidance: {strategy_prompts[strategy]}

Provide the corrected version:"""

    def apply_correction(self, claim: Claim, action: CorrectionAction) -> Claim:
        """Apply a correction action to a claim."""
        if action.applied:
            return claim

        claim.content = action.corrected_text
        claim.metadata["corrections"] = claim.metadata.get("corrections", [])
        claim.metadata["corrections"].append({
            "action_id": action.action_id,
            "strategy": action.strategy.value,
            "rationale": action.rationale,
            "applied_at": action.applied_at or time.time(),
        })
        action.applied = True
        action.applied_at = time.time()

        self.metrics.counter("corrections_applied")
        return claim


class VerificationLoop:
    """Complete verification and correction loop."""

    def __init__(
        self,
        fact_checker: Optional[FactChecker] = None,
        consistency_checker: Optional[ConsistencyChecker] = None,
        error_detector: Optional[ErrorDetector] = None,
        correction_engine: Optional[CorrectionEngine] = None,
        max_iterations: int = 3,
    ):
        self.fact_checker = fact_checker or FactChecker()
        self.consistency_checker = consistency_checker or ConsistencyChecker()
        self.error_detector = error_detector or ErrorDetector()
        self.correction_engine = correction_engine or CorrectionEngine()
        self.max_iterations = max_iterations
        self.metrics = MetricsCollector("verification_loop")

    def verify_and_correct(
        self,
        text: str,
        claims: Optional[List[Claim]] = None,
        evidence: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run complete verification and correction loop."""
        # Extract claims if not provided
        if claims is None:
            claims = self._extract_claims(text)

        if evidence is None:
            evidence = []

        history = []
        current_text = text

        for iteration in range(3):  # Max 3 iterations
            # 1. Fact-check claims
            verification_results = self.fact_checker.batch_check(claims, evidence)

            # 2. Check consistency
            consistency = self.consistency_checker.check_consistency(claims)

            # 3. Detect errors
            current_text = self._reconstruct_text(claims)
            errors = self.error_detector.detect_errors(current_text)

            # 4. Apply corrections
            corrections = []
            for claim, verification in zip(claims, verification_results):
                if verification.status != VerificationStatus.VERIFIED:
                    action = self.correction_engine.correct_claim(claim, verification)
                    if action.strategy != CorrectionStrategy.REWRITE:  # No-op for verified
                        self.correction_engine.apply_correction(claim, action)
                        corrections.append(action)

            history.append({
                "iteration": len(history) + 1,
                "verifications": len([v for v in verification_results if v.status == VerificationStatus.VERIFIED]),
                "consistency": consistency.get("consistent", False),
                "errors_found": errors.get("has_errors", False),
                "corrections_applied": len(corrections),
            })

            # Check convergence
            all_verified = all(v.status == VerificationStatus.VERIFIED for v in verification_results)
            if all_verified and consistency.get("consistent", True) and not errors.get("has_errors", False):
                break

        final_text = self._reconstruct_text(claims)
        return {
            "original_text": text,
            "corrected_text": final_text,
            "claims": claims,
            "iterations": len(history),
            "history": history,
            "final_verification": verification_results,
            "final_consistency": consistency,
            "final_errors": errors,
        }

    def _extract_claims(self, text: str) -> List[Claim]:
        """Extract claims from text (simplified)."""
        sentences = re.split(r'[.!?]+', text)
        claims = []
        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if len(sent) > 20:  # Only substantial sentences
                claims.append(Claim(
                    claim_id=f"claim_{i}",
                    content=sent,
                    source="extracted",
                ))
        return claims

    def _reconstruct_text(self, claims: List[Claim]) -> str:
        return " ".join(c.content for c in claims)


# Convenience functions
def verify_claims(claims: List[Claim], evidence: List[str]) -> List[VerificationResult]:
    checker = FactChecker()
    return checker.batch_check(claims, evidence)


def check_consistency(claims: List[Claim]) -> Dict[str, Any]:
    checker = ConsistencyChecker()
    return checker.check_consistency(claims)


def detect_errors(text: str, checks: Optional[List[str]] = None) -> Dict[str, Any]:
    detector = ErrorDetector()
    return detector.detect_errors(text, checks)


def refine_output(
    generator: Callable[[str, Dict], str],
    critic: Callable[[str, Dict], Dict],
    initial_input: str,
    context: Optional[Dict] = None,
    max_iterations: int = 5,
) -> Dict[str, Any]:
    refiner = IterativeRefiner(generator, critic)
    return refiner.refine(initial_input, context)


def verify_and_correct(
    text: str,
    evidence: Optional[List[str]] = None,
) -> Dict[str, Any]:
    loop = VerificationLoop()
    return loop.verify_and_correct(text, evidence=evidence)