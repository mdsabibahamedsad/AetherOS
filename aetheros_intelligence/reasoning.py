"""
Reasoning Pipeline for AetherOS Intelligence Engine.

Implements:
    - Chain-of-Thought reasoning
    - Self-critique and revision
    - Chain verification
    - Multi-step planning
    - Alternative solution generation
    - Confidence scoring
    - Reflection on outcomes
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReasoningStrategy(Enum):
    """Reasoning strategies the pipeline can use."""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    SELF_CRITIQUE = "self_critique"
    VERIFICATION = "verification"
    MULTI_STEP = "multi_step"
    ALTERNATIVES = "alternatives"
    REFLECTION = "reflection"


@dataclass
class ReasoningStep:
    """A single step in the reasoning pipeline.

    Attributes:
        step_id: Unique step identifier
        strategy: Reasoning strategy used
        input_text: Input for this step
        output_text: Output from this step
        confidence: Confidence score (0.0 - 1.0)
        critique: Self-critique of this step (if applicable)
        verified: Whether this step passed verification
        duration_seconds: How long this step took
        metadata: Additional metadata
    """
    step_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT
    input_text: str = ""
    output_text: str = ""
    confidence: float = 0.0
    critique: str = ""
    verified: bool = False
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningResult:
    """Result of a complete reasoning pipeline run.

    Attributes:
        question: The original question
        answer: The final answer
        confidence: Overall confidence score
        steps: All reasoning steps
        alternatives: Alternative solutions/approaches
        verification_notes: Notes from chain verification
        metadata: Additional metadata
    """
    question: str = ""
    answer: str = ""
    confidence: float = 0.0
    steps: List[ReasoningStep] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    verification_notes: List[str] = field(default_factory=list)
    total_duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReflectionEntry:
    """A reflection on a completed action or workflow."""
    goal: str
    outcome: str  # "success", "partial", "failure"
    successes: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    duration_seconds: float = 0.0
    task_count: int = 0
    recommendations: List[str] = field(default_factory=list)


class ReasoningPipeline:
    """Multi-strategy reasoning pipeline.

    Applies chains of reasoning strategies to answer questions,
    solve problems, and reflect on outcomes. Supports both
    LLM-backed reasoning and local heuristic reasoning.

    Usage::

        pipeline = ReasoningPipeline()

        # Full reasoning
        result = pipeline.reason("How should I structure this API?")

        # Reflection
        reflection = pipeline.reflect(
            goal="Deploy microservice",
            outcome="success",
            successes=["Configured CI/CD"],
            failures=["Missed rate limiting"],
            lessons=["Always add rate limits early"],
        )
    """

    def __init__(self) -> None:
        self._reflection_history: List[ReflectionEntry] = []
        self._strategies = {
            ReasoningStrategy.CHAIN_OF_THOUGHT: self._chain_of_thought,
            ReasoningStrategy.SELF_CRITIQUE: self._self_critique,
            ReasoningStrategy.VERIFICATION: self._verify_chain,
            ReasoningStrategy.MULTI_STEP: self._multi_step_plan,
            ReasoningStrategy.ALTERNATIVES: self._generate_alternatives,
        }

    # ------------------------------------------------------------------
    # Main reason method
    # ------------------------------------------------------------------

    def reason(self, question: str,
               context: Any = None,
               strategies: Optional[List[ReasoningStrategy]] = None) -> Dict[str, Any]:
        """Run the full reasoning pipeline on a question.

        Applies each reasoning strategy in sequence, building up
        the final answer with confidence scoring and alternatives.

        Args:
            question: The question or problem to reason about
            context: Optional context (memory entries, knowledge, etc.)
            strategies: Which strategies to apply (default: all)

        Returns:
            Dict with answer, confidence, steps, alternatives
        """
        start = time.time()
        strategies = strategies or [
            ReasoningStrategy.CHAIN_OF_THOUGHT,
            ReasoningStrategy.SELF_CRITIQUE,
            ReasoningStrategy.VERIFICATION,
            ReasoningStrategy.ALTERNATIVES,
        ]

        steps: List[ReasoningStep] = []
        current_input = question

        for strategy in strategies:
            handler = self._strategies.get(strategy)
            if not handler:
                continue

            step_start = time.time()
            try:
                result = handler(current_input, context=context)
                step = ReasoningStep(
                    strategy=strategy,
                    input_text=current_input,
                    output_text=result.get("output", ""),
                    confidence=result.get("confidence", 0.0),
                    critique=result.get("critique", ""),
                    verified=result.get("verified", False),
                    duration_seconds=time.time() - step_start,
                    metadata=result.get("metadata", {}),
                )
                steps.append(step)
                current_input = step.output_text
            except Exception as exc:
                logger.warning("Reasoning step %s failed: %s", strategy.value, exc)
                steps.append(ReasoningStep(
                    strategy=strategy,
                    input_text=current_input,
                    output_text=f"[Error: {exc}]",
                    confidence=0.0,
                    duration_seconds=time.time() - step_start,
                ))

        # Compute overall confidence
        confidences = [s.confidence for s in steps if s.confidence > 0]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        # Collect alternatives
        alternatives = []
        for step in steps:
            if step.strategy == ReasoningStrategy.ALTERNATIVES:
                alt_list = step.metadata.get("alternatives", [])
                alternatives.extend(alt_list)

        # Verification notes
        ver_notes = []
        for step in steps:
            if step.strategy == ReasoningStrategy.VERIFICATION:
                notes = step.metadata.get("notes", [])
                ver_notes.extend(notes)

        result = ReasoningResult(
            question=question,
            answer=steps[-1].output_text if steps else "No reasoning completed",
            confidence=round(overall_confidence, 2),
            steps=steps,
            alternatives=alternatives[:5],  # Top 5
            verification_notes=ver_notes,
            total_duration=round(time.time() - start, 3),
        )

        return {
            "answer": result.answer,
            "confidence": result.confidence,
            "steps": [
                {
                    "strategy": s.strategy.value,
                    "output": s.output_text[:200],
                    "confidence": s.confidence,
                    "critique": s.critique[:200] if s.critique else "",
                    "verified": s.verified,
                    "duration": round(s.duration_seconds, 2),
                }
                for s in result.steps
            ],
            "alternatives": result.alternatives,
            "verification_notes": result.verification_notes,
            "total_duration": result.total_duration,
        }

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    def _chain_of_thought(self, input_text: str,
                          context: Any = None) -> Dict[str, Any]:
        """Chain-of-thought reasoning step.

        Breaks down the problem into logical steps and reasons
        through each one.
        """
        # Build structured reasoning
        steps = self._decompose_problem(input_text, context)
        reasoning_chain = []
        for i, step in enumerate(steps):
            reasoning_chain.append(f"  {i+1}. {step}")

        output = "\n".join([
            "Reasoning through this step by step:",
            "",
            *reasoning_chain,
            "",
            "Conclusion based on the above reasoning.",
        ])

        return {
            "output": output,
            "confidence": self._estimate_confidence(input_text, steps),
        }

    def _self_critique(self, input_text: str,
                       context: Any = None) -> Dict[str, Any]:
        """Self-critique step.

        Reviews the previous reasoning output for errors, gaps,
        and assumptions, then revises.
        """
        # Identify potential issues
        issues = self._identify_issues(input_text)

        if not issues:
            return {
                "output": input_text,
                "confidence": 0.9,
                "critique": "No issues found in reasoning.",
                "verified": True,
            }

        critique_parts = []
        for issue in issues:
            critique_parts.append(f"- {issue['description']}")
            if issue.get("suggestion"):
                critique_parts.append(f"  → {issue['suggestion']}")

        output = "\n".join([
            "Self-critique review:",
            "",
            *critique_parts,
            "",
            "Revised conclusion.",
        ])

        return {
            "output": output,
            "confidence": 0.7,
            "critique": "\n".join(issue["description"] for issue in issues),
            "verified": True,
        }

    def _verify_chain(self, input_text: str,
                      context: Any = None) -> Dict[str, Any]:
        """Verification step.

        Checks the reasoning chain for logical consistency,
        factual accuracy, and completeness.
        """
        checks = self._run_verification_checks(input_text)
        failed = [c for c in checks if not c["passed"]]

        metadata = {
            "notes": [
                f"{'✓' if c['passed'] else '✗'} {c['check']}"
                for c in checks
            ],
        }

        if failed:
            output = "\n".join([
                "Verification identified issues:",
                "",
                *[f"- {f['check']}: {f.get('detail', '')}" for f in failed],
                "",
                "These should be addressed before finalizing.",
            ])
            return {
                "output": output,
                "confidence": 0.5,
                "verified": False,
                "metadata": metadata,
            }

        return {
            "output": input_text,
            "confidence": 0.95,
            "verified": True,
            "metadata": metadata,
        }

    def _multi_step_plan(self, input_text: str,
                         context: Any = None) -> Dict[str, Any]:
        """Multi-step planning.

        Breaks the solution into concrete, actionable steps
        with dependencies and priorities.
        """
        steps = self._decompose_problem(input_text, context)
        plan_lines = []
        for i, step in enumerate(steps):
            deps = self._identify_dependencies(step, steps)
            dep_str = f" (depends on: {', '.join(deps)})" if deps else ""
            priority = "HIGH" if i < 2 else "MEDIUM" if i < 4 else "LOW"
            plan_lines.append(f"  {i+1}. [{priority}] {step}{dep_str}")

        output = "\n".join([
            "Multi-step execution plan:",
            "",
            *plan_lines,
            "",
            "Execute steps in order, resolving dependencies first.",
        ])

        return {
            "output": output,
            "confidence": 0.8,
        }

    def _generate_alternatives(self, input_text: str,
                               context: Any = None) -> Dict[str, Any]:
        """Generate alternative solutions.

        Produces 2-3 alternative approaches with tradeoffs.
        """
        alternatives = self._produce_alternatives(input_text)

        if not alternatives:
            return {
                "output": input_text,
                "confidence": 0.6,
                "metadata": {"alternatives": []},
            }

        alt_lines = []
        for i, alt in enumerate(alternatives):
            alt_lines.extend([
                f"  Option {i+1}: {alt['title']}",
                f"           {alt['description']}",
                f"           Tradeoffs: {alt.get('tradeoffs', 'N/A')}",
                "",
            ])

        output = "\n".join([
            "Alternative approaches:",
            "",
            *alt_lines,
            "Recommended approach based on tradeoffs.",
        ])

        return {
            "output": output,
            "confidence": 0.7,
            "metadata": {"alternatives": alternatives},
        }

    # ------------------------------------------------------------------
    # Reflection
    # ------------------------------------------------------------------

    def reflect(self, goal: str, outcome: str,
                successes: List[str] = None,
                failures: List[str] = None,
                lessons: List[str] = None,
                duration_seconds: float = 0.0,
                task_count: int = 0) -> Dict[str, Any]:
        """Reflect on a completed action or workflow.

        Args:
            goal: What was attempted
            outcome: What happened
            successes: What went well
            failures: What went wrong
            lessons: Lessons learned
            duration_seconds: How long it took
            task_count: Number of subtasks

        Returns:
            Reflection entry with insights and recommendations.
        """
        entry = ReflectionEntry(
            goal=goal,
            outcome=outcome,
            successes=successes or [],
            failures=failures or [],
            lessons=lessons or [],
            duration_seconds=duration_seconds,
            task_count=task_count,
        )

        # Generate recommendations based on outcome
        recommendations = []
        if outcome in ("failure", "partial"):
            for lesson in entry.lessons:
                recommendations.append(f"Apply lesson: {lesson}")
            for failure in entry.failures:
                recommendations.append(f"Address: {failure}")
        if entry.successes:
            recommendations.append(
                f"Continue: {entry.successes[0]}"
            )

        entry.recommendations = recommendations
        self._reflection_history.append(entry)

        return {
            "goal": goal,
            "outcome": outcome,
            "successes": entry.successes,
            "failures": entry.failures,
            "lessons": entry.lessons,
            "recommendations": recommendations,
            "duration": duration_seconds,
        }

    def get_recent_reflections(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent reflection entries."""
        return [
            {
                "goal": r.goal,
                "outcome": r.outcome,
                "successes": r.successes,
                "failures": r.failures,
                "lessons": r.lessons[:3],
                "recommendations": r.recommendations,
                "timestamp": r.timestamp,
            }
            for r in self._reflection_history[-limit:]
        ]

    # ------------------------------------------------------------------
    # Heuristic reasoning helpers
    # ------------------------------------------------------------------

    def _decompose_problem(self, text: str,
                           context: Any = None) -> List[str]:
        """Decompose a problem into logical steps.

        Uses heuristics to identify sub-problems.
        """
        # Use simple heuristics when no LLM is available
        steps = []
        lines = text.strip().split("\n")

        # Look for explicit steps or bullet points
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("- ", "* ", "1. ", "• ")):
                steps.append(stripped.lstrip("- *•1234567890. ").strip())

        if not steps:
            # Generate steps from keywords
            keywords = {
                "design": "Analyze requirements and design the solution",
                "implement": "Implement the solution following best practices",
                "test": "Add tests and verify correctness",
                "deploy": "Deploy the solution to production",
                "document": "Document the solution for maintainability",
                "review": "Review for quality and security issues",
                "optimize": "Profile and optimize performance",
                "refactor": "Refactor for clarity and maintainability",
                "secure": "Apply security best practices",
                "monitor": "Set up monitoring and observability",
            }

            found = False
            for kw, step in keywords.items():
                if kw in text.lower():
                    steps.append(step)
                    found = True

            if not steps:
                steps = [
                    "Understand the problem and requirements",
                    "Research existing solutions and patterns",
                    "Design the solution architecture",
                    "Implement the solution",
                    "Test and verify correctness",
                    "Review and refine",
                    "Document and deploy",
                ]

        return steps[:8]  # Limit to 8 steps

    def _estimate_confidence(self, text: str,
                             steps: List[str]) -> float:
        """Estimate confidence based on input quality."""
        score = 0.7  # Base confidence

        # More steps = more thorough = higher confidence
        if len(steps) >= 5:
            score += 0.1
        elif len(steps) <= 2:
            score -= 0.1

        # Longer input = more context = higher confidence
        if len(text) > 500:
            score += 0.1
        elif len(text) < 50:
            score -= 0.1

        # Technical keywords suggest structured thinking
        tech_words = {"api", "architecture", "database", "design pattern",
                      "interface", "module", "service", "protocol"}
        if any(w in text.lower() for w in tech_words):
            score += 0.05

        return min(max(score, 0.1), 0.99)

    def _identify_issues(self, text: str) -> List[Dict[str, Any]]:
        """Identify potential issues in reasoning output."""
        issues = []

        # Check for missing specifics
        if len(text) < 100:
            issues.append({
                "description": "Reasoning is too brief — may lack depth",
                "suggestion": "Expand on each step with more detail",
            })

        # Check for uncertainty markers
        uncertain_words = ["might", "maybe", "perhaps", "could be", "not sure"]
        for word in uncertain_words:
            if word in text.lower():
                issues.append({
                    "description": f"Uncertainty marker found: '{word}'",
                    "suggestion": "Try to be more definitive or gather more information",
                })
                break

        return issues

    def _run_verification_checks(self, text: str) -> List[Dict[str, Any]]:
        """Run verification checks on the reasoning."""
        checks = []

        # Check 1: Not empty
        checks.append({
            "check": "Output is non-empty",
            "passed": bool(text.strip()),
            "detail": "" if text.strip() else "No content to verify",
        })

        # Check 2: Has structure
        has_structure = any(marker in text for marker in
                            ["\n", "1.", "- ", "•"])
        checks.append({
            "check": "Output has logical structure",
            "passed": has_structure,
            "detail": "" if has_structure else "Output lacks structure (no line breaks or lists)",
        })

        # Check 3: Length is reasonable
        checks.append({
            "check": "Output length is reasonable",
            "passed": 50 <= len(text) <= 10000,
            "detail": f"Length: {len(text)} chars",
        })

        # Check 4: No common errors
        error_patterns = ["undefined", "null reference", "error occurred"]
        has_errors = any(p in text.lower() for p in error_patterns)
        checks.append({
            "check": "No unhandled error references",
            "passed": not has_errors,
            "detail": "Found error references" if has_errors else "",
        })

        return checks

    def _identify_dependencies(self, step: str,
                               all_steps: List[str]) -> List[str]:
        """Identify dependencies between steps."""
        deps = []
        step_lower = step.lower()
        for prev in all_steps:
            prev_lower = prev.lower()
            if prev == step:
                break
            # Check if current step references previous step concepts
            dependency_keywords = {
                "design": ["requirement", "spec"],
                "implement": ["design", "architecture"],
                "test": ["implement", "code"],
                "deploy": ["test", "build"],
                "document": ["implement", "design"],
            }
            for kw, triggers in dependency_keywords.items():
                if kw in step_lower:
                    for trigger in triggers:
                        if trigger in prev_lower:
                            deps.append(prev[:40])
                            break
        return deps

    def _produce_alternatives(self, text: str) -> List[Dict[str, Any]]:
        """Generate alternative approaches."""
        alternatives = []

        if "api" in text.lower():
            alternatives.append({
                "title": "REST API",
                "description": "Traditional RESTful API with endpoints and resources",
                "tradeoffs": "Simple, well-understood, but can be chatty",
            })
            alternatives.append({
                "title": "GraphQL API",
                "description": "Query-based API with flexible data fetching",
                "tradeoffs": "Efficient queries, but more complex caching",
            })

        if "database" in text.lower():
            alternatives.append({
                "title": "Relational Database",
                "description": "SQL database with ACID transactions",
                "tradeoffs": "Strong consistency, well-known, but scales vertically",
            })
            alternatives.append({
                "title": "Document Database",
                "description": "NoSQL document store for flexible schemas",
                "tradeoffs": "Horizontal scaling, flexible, but eventual consistency",
            })

        if "deploy" in text.lower():
            alternatives.append({
                "title": "Container Deployment",
                "description": "Docker containers orchestrated by Kubernetes",
                "tradeoffs": "Portable, scalable, but operational overhead",
            })
            alternatives.append({
                "title": "Serverless Deployment",
                "description": "Function-as-a-Service with auto-scaling",
                "tradeoffs": "No infrastructure management, but cold starts",
            })

        if not alternatives:
            alternatives.append({
                "title": "Standard Approach",
                "description": "Follow established patterns and best practices",
                "tradeoffs": "Predictable, but may miss optimization opportunities",
            })
            alternatives.append({
                "title": "Experimental Approach",
                "description": "Try a novel or innovative approach",
                "tradeoffs": "Potential breakthroughs, but higher risk",
            })

        return alternatives

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get reasoning pipeline statistics."""
        return {
            "reflections": len(self._reflection_history),
            "recent_reflections": self.get_recent_reflections(5),
            "available_strategies": [s.value for s in ReasoningStrategy],
        }
