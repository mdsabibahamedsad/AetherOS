"""Reasoning Engine — normal, thinking, deep reasoning, planning, reflection, self-correction.

Multiple reasoning modes for different task complexity levels.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aetheros_runtime.reasoning")


class ReasoningMode(enum.Enum):
    NORMAL = "normal"
    THINKING = "thinking"
    DEEP = "deep"
    PLANNING = "planning"
    REFLECTION = "reflection"
    SELF_CORRECT = "self_correct"


@dataclass
class ReasoningStep:
    index: int = 0
    content: str = ""
    mode: str = "thinking"
    confidence: float = 0.0
    elapsed_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningResult:
    conclusion: str = ""
    steps: List[ReasoningStep] = field(default_factory=list)
    confidence: float = 0.0
    mode: ReasoningMode = ReasoningMode.NORMAL
    elapsed_ms: float = 0.0
    token_count: int = 0
    error: str = ""


ReasoningProvider = Callable[[str, ReasoningMode], str]


class ReasoningEngine:
    """Multi-mode reasoning engine.

    Modes:
    - Normal: direct response, no extra reasoning
    - Thinking: step-by-step reasoning with visible chain-of-thought
    - Deep: thorough multi-step analysis for complex problems
    - Planning: task decomposition and plan generation
    - Reflection: review and critique of previous reasoning
    - Self-correct: iterative improvement with error detection
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._providers: Dict[ReasoningMode, ReasoningProvider] = {}
        self._history: List[ReasoningResult] = []
        self._max_history: int = 100

    # ------------------------------------------------------------------
    # Provider registration
    # ------------------------------------------------------------------

    def register_provider(self, mode: ReasoningMode, provider: ReasoningProvider) -> None:
        with self._lock:
            self._providers[mode] = provider

    def get_provider(self, mode: ReasoningMode) -> Optional[ReasoningProvider]:
        with self._lock:
            return self._providers.get(mode)

    # ------------------------------------------------------------------
    # Reasoning execution
    # ------------------------------------------------------------------

    def reason(
        self,
        query: str,
        mode: ReasoningMode = ReasoningMode.NORMAL,
    ) -> ReasoningResult:
        start = time.monotonic()

        if mode == ReasoningMode.THINKING:
            result = self._thinking_reason(query)
        elif mode == ReasoningMode.DEEP:
            result = self._deep_reason(query)
        elif mode == ReasoningMode.PLANNING:
            result = self._planning_reason(query)
        elif mode == ReasoningMode.REFLECTION:
            result = self._reflection_reason(query)
        elif mode == ReasoningMode.SELF_CORRECT:
            result = self._self_correct_reason(query)
        else:
            result = self._normal_reason(query)

        result.elapsed_ms = (time.monotonic() - start) * 1000
        result.mode = mode

        provider = self.get_provider(mode)
        if provider:
            try:
                provider_result = provider(query, mode)
                if provider_result:
                    result.conclusion = provider_result
            except Exception as exc:
                logger.warning("Reasoning provider %s failed: %s", mode.value, exc)

        with self._lock:
            self._history.append(result)
            if len(self._history) > self._max_history:
                self._history.pop(0)

        return result

    def _normal_reason(self, query: str) -> ReasoningResult:
        return ReasoningResult(
            conclusion=query,
            steps=[ReasoningStep(index=0, content="Direct response", mode="normal", confidence=1.0)],
            confidence=1.0,
        )

    def _thinking_reason(self, query: str) -> ReasoningResult:
        steps = [
            ReasoningStep(index=0, content=f"Understanding query: {query[:100]}", mode="understanding"),
            ReasoningStep(index=1, content="Analyzing context and requirements", mode="analysis"),
            ReasoningStep(index=2, content="Formulating response", mode="synthesis"),
        ]
        return ReasoningResult(
            conclusion=f"[Reasoned response for: {query[:100]}]",
            steps=steps,
            confidence=0.85,
        )

    def _deep_reason(self, query: str) -> ReasoningResult:
        steps = [
            ReasoningStep(index=0, content=f"Problem decomposition: {query[:100]}", mode="decomposition"),
            ReasoningStep(index=1, content="Gathering relevant context and evidence", mode="research"),
            ReasoningStep(index=2, content="Multi-step logical analysis", mode="analysis"),
            ReasoningStep(index=3, content="Evaluating alternatives and edge cases", mode="evaluation"),
            ReasoningStep(index=4, content="Synthesizing final conclusion", mode="synthesis"),
        ]
        return ReasoningResult(
            conclusion=f"[Deep reasoned response for: {query[:100]}]",
            steps=steps,
            confidence=0.9,
        )

    def _planning_reason(self, query: str) -> ReasoningResult:
        steps = [
            ReasoningStep(index=0, content=f"Goal identification: {query[:100]}", mode="goal_setting"),
            ReasoningStep(index=1, content="Breaking down into subtasks", mode="decomposition"),
            ReasoningStep(index=2, content="Ordering and dependency mapping", mode="ordering"),
            ReasoningStep(index=3, content="Resource and constraint analysis", mode="constraint_analysis"),
        ]
        return ReasoningResult(
            conclusion=self._format_plan(steps, query),
            steps=steps,
            confidence=0.85,
        )

    def _reflection_reason(self, query: str) -> ReasoningResult:
        steps = [
            ReasoningStep(index=0, content=f"Initial assessment: {query[:100]}", mode="assessment"),
            ReasoningStep(index=1, content="Critical review of assumptions", mode="critique"),
            ReasoningStep(index=2, content="Identifying gaps and improvements", mode="gap_analysis"),
        ]
        return ReasoningResult(
            conclusion=f"[Reflection on: {query[:100]}]",
            steps=steps,
            confidence=0.8,
        )

    def _self_correct_reason(self, query: str) -> ReasoningResult:
        steps = [
            ReasoningStep(index=0, content=f"Initial reasoning attempt", mode="attempt"),
            ReasoningStep(index=1, content="Error detection and analysis", mode="error_detection"),
            ReasoningStep(index=2, content="Correction and refinement", mode="correction"),
            ReasoningStep(index=3, content="Verification of corrected result", mode="verification"),
        ]
        return ReasoningResult(
            conclusion=f"[Self-corrected response for: {query[:100]}]",
            steps=steps,
            confidence=0.9,
        )

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, limit: int = 10) -> List[ReasoningResult]:
        with self._lock:
            return list(self._history[-limit:])

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _format_plan(steps: List[ReasoningStep], query: str) -> str:
        lines = [f"Plan for: {query[:100]}", ""]
        for i, step in enumerate(steps):
            lines.append(f"{i + 1}. {step.content}")
        return "\n".join(lines)

    def health_check(self) -> bool:
        return True

    def summary(self) -> str:
        with self._lock:
            return f"Reasoning Engine: {len(self._history)} reasoning sessions, {len(self._providers)} custom providers"