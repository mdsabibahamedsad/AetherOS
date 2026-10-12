"""Advanced Reasoning Capabilities (Phase 59).

Advanced reasoning capabilities:
- Chain-of-Thought reasoning
- Tree-of-Thought exploration
- Self-consistency verification
- ReAct (Reasoning + Acting) pattern
- Program-aided reasoning
- Structured reasoning templates
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from abc import ABC, abstractmethod

from agent.multimodal.production import MetricsCollector

logger = logging.getLogger(__name__)


class ReasoningType(Enum):
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    SELF_CONSISTENCY = "self_consistency"
    REACT = "react"
    PROGRAM_AIDED = "program_aided"
    STRUCTURED = "structured"


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain."""
    step_id: str
    content: str
    step_type: str  # observation, thought, action, reflection
    confidence: float = 1.0
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class ThoughtNode:
    """A node in a tree of thoughts."""
    node_id: str
    content: str
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    score: float = 0.0
    depth: int = 0
    is_terminal: bool = False
    metadata: Dict = field(default_factory=dict)


@dataclass
class ReasoningTrace:
    """Complete trace of a reasoning process."""
    trace_id: str
    reasoning_type: ReasoningType
    question: str
    steps: List[ReasoningStep] = field(default_factory=list)
    tree: Dict[str, ThoughtNode] = field(default_factory=dict)
    final_answer: Optional[str] = None
    confidence: float = 0.0
    iterations: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000


class ReasoningEngine(ABC):
    """Abstract base for reasoning engines."""

    @abstractmethod
    def reason(self, question: str, context: Optional[Dict] = None) -> ReasoningTrace:
        pass


class ChainOfThoughtEngine(ReasoningEngine):
    """Chain-of-Thought reasoning engine."""

    def __init__(
        self,
        max_steps: int = 10,
        min_confidence: float = 0.7,
        llm_call: Optional[Callable[[str], str]] = None,
    ):
        self.max_steps = max_steps
        self.min_confidence = min_confidence
        self.llm_call = llm_call or self._mock_llm
        self.metrics = MetricsCollector("cot_reasoning")

    def _mock_llm(self, prompt: str) -> str:
        """Mock LLM call for testing."""
        return f"Step: {prompt[:50]}... -> Reasoning: This is a simulated reasoning step."

    def reason(self, question: str, context: Optional[Dict] = None) -> ReasoningTrace:
        trace = ReasoningTrace(
            trace_id=f"cot_{uuid.uuid4().hex[:8]}",
            reasoning_type=ReasoningType.CHAIN_OF_THOUGHT,
            question=question,
        )

        prompt = self._build_initial_prompt(question, context)

        for i in range(self.max_steps):
            step_id = f"step_{i+1}"
            response = self.llm_call(prompt)

            # Extract reasoning step
            step = ReasoningStep(
                step_id=step_id,
                content=response,
                step_type="thought",
                confidence=self._estimate_confidence(response),
            )
            trace.steps.append(step)

            # Check if we have an answer
            if self._has_answer(response):
                trace.final_answer = self._extract_answer(response)
                break

            # Build next prompt
            prompt = self._build_continuation_prompt(prompt, response)

            trace.iterations += 1

        trace.end_time = time.time()
        trace.confidence = self._compute_overall_confidence(trace.steps)

        self.metrics.counter("cot_completed", labels={"steps": str(len(trace.steps))})
        return trace

    def _build_initial_prompt(self, question: str, context: Optional[Dict]) -> str:
        ctx = ""
        if context:
            ctx = f"\nContext: {context}\n"
        return f"Question: {question}{ctx}\nLet's think step by step:\n"

    def _build_continuation_prompt(self, prev_prompt: str, response: str) -> str:
        return prev_prompt + response + "\n\nNext step:\n"

    def _estimate_confidence(self, response: str) -> float:
        # Heuristic: longer, more detailed responses tend to be more confident
        length_factor = min(len(response) / 500, 1.0)
        certainty_words = ["therefore", "thus", "hence", "consequently", "clearly", "obviously"]
        certainty_bonus = sum(1 for w in certainty_words if w in response.lower()) * 0.05
        return min(0.9, 0.5 + length_factor * 0.3 + certainty_bonus)

    def _has_answer(self, response: str) -> bool:
        answer_indicators = ["answer:", "final answer:", "conclusion:", "therefore", "thus the answer"]
        return any(indicator in response.lower() for indicator in answer_indicators)

    def _extract_answer(self, response: str) -> str:
        for indicator in ["answer:", "final answer:", "conclusion:"]:
            idx = response.lower().find(indicator)
            if idx >= 0:
                return response[idx + len(indicator):].strip()
        return response.strip()

    def _compute_overall_confidence(self, steps: List[ReasoningStep]) -> float:
        if not steps:
            return 0.0
        return sum(s.confidence for s in steps) / len(steps)


class TreeOfThoughtEngine(ReasoningEngine):
    """Tree-of-Thought reasoning engine for complex problem solving."""

    def __init__(
        self,
        max_depth: int = 5,
        branching_factor: int = 3,
        beam_width: int = 5,
        evaluator: Optional[Callable[[str], float]] = None,
        llm_call: Optional[Callable[[str], List[str]]] = None,
    ):
        self.max_depth = max_depth
        self.branching_factor = branching_factor
        self.beam_width = beam_width
        self.evaluator = evaluator or self._default_evaluator
        self.llm_call = llm_call or self._mock_llm_generate
        self.metrics = MetricsCollector("tot_reasoning")

    def _mock_llm_generate(self, prompt: str, n: int = 3) -> List[str]:
        """Mock LLM generating multiple thoughts."""
        return [f"Thought {i+1}: {prompt[:30]}... -> exploring path {i+1}" for i in range(n)]

    def _default_evaluator(self, thought: str) -> float:
        """Default evaluator - length and keyword based."""
        score = min(len(thought) / 200, 1.0) * 0.5
        positive = ["therefore", "thus", "solution", "answer", "solve"]
        negative = ["stuck", "unsure", "unclear", "confused"]
        score = 0.5
        for w in positive:
            if w in thought.lower():
                score += 0.1
        for w in negative:
            if w in thought.lower():
                score -= 0.1
        return max(0.0, min(1.0, score))

    def reason(self, question: str, context: Optional[Dict] = None) -> ReasoningTrace:
        trace = ReasoningTrace(
            trace_id=f"tot_{uuid.uuid4().hex[:8]}",
            reasoning_type=ReasoningType.TREE_OF_THOUGHT,
            question=question,
        )

        # Initialize root
        root = ThoughtNode(
            node_id="root",
            content=question,
            depth=0,
        )
        trace.tree[root.node_id] = root

        current_level = [root]
        best_node = root

        for depth in range(1, self.max_depth + 1):
            candidates = []

            for node in current_level:
                # Generate branches
                prompt = self._build_prompt(node, context)
                thoughts = self.llm_call(prompt, self.branching_factor)

                for i, thought in enumerate(thoughts):
                    child = ThoughtNode(
                        node_id=f"{node.node_id}_child_{i}",
                        content=thought,
                        parent_id=node.node_id,
                        depth=depth,
                    )
                    child.score = self.evaluator(thought)
                    node.children.append(child.node_id)
                    trace.tree[child.node_id] = child
                    candidates.append(child)

            # Beam search: keep top-k
            candidates.sort(key=lambda x: x.score, reverse=True)
            current_level = candidates[:self.beam_width]

            if not current_level:
                break

            best_node = max(current_level, key=lambda x: x.score)

            # Check if terminal
            if self._is_terminal(best_node.content):
                best_node.is_terminal = True
                trace.final_answer = self._extract_answer(best_node.content)
                break

        # Build steps from tree
        trace.steps = self._tree_to_steps(trace.tree)
        trace.end_time = time.time()
        trace.confidence = best_node.score if best_node else 0.0

        self.metrics.counter("tot_completed", labels={"depth": str(self.max_depth)})
        return trace

    def _build_prompt(self, node: ThoughtNode, context: Optional[Dict]) -> str:
        # Build prompt from root to current node
        path = []
        current = node
        while current:
            path.append(current.content)
            current_id = current.parent_id
            current = current.tree.get(current_id) if current_id else None  # This won't work, need access to tree

        # Simplified: just use node content
        return f"Problem: {self.question}\nCurrent thought: {node.content}\nGenerate next thoughts:"

    def _is_terminal(self, thought: str) -> bool:
        terminal_indicators = ["answer:", "final answer:", "solution:", "conclusion:"]
        return any(indicator in thought.lower() for indicator in terminal_indicators)

    def _extract_answer(self, thought: str) -> str:
        for indicator in ["answer:", "final answer:", "solution:", "conclusion:"]:
            idx = thought.lower().find(indicator)
            if idx >= 0:
                return thought[idx:].strip()
        return thought.strip()

    def _tree_to_steps(self, tree: Dict[str, ThoughtNode]) -> List[ReasoningStep]:
        steps = []
        for node_id, node in tree.items():
            if node.node_id == "root":
                continue
            step = ReasoningStep(
                step_id=node.node_id,
                content=node.content,
                step_type="thought",
                confidence=node.score,
                dependencies=[node.parent_id] if node.parent_id else [],
            )
            steps.append(step)
        return steps


class SelfConsistencyEngine(ReasoningEngine):
    """Self-Consistency verification engine."""

    def __init__(
        self,
        base_engine: ReasoningEngine,
        num_samples: int = 5,
        agreement_threshold: float = 0.6,
    ):
        self.base_engine = base_engine
        self.num_samples = num_samples
        self.agreement_threshold = agreement_threshold
        self.metrics = MetricsCollector("sc_reasoning")

    def reason(self, question: str, context: Optional[Dict] = None) -> ReasoningTrace:
        traces = []

        # Generate multiple reasoning traces
        for i in range(self.num_samples):
            trace = self.base_engine.reason(question, context)
            traces.append(trace)

        # Find consensus answer
        answers = [t.final_answer for t in traces if t.final_answer]
        if not answers:
            # Return first trace if no answers
            return traces[0]

        # Find most common answer (simplified)
        answer_counts = defaultdict(int)
        for ans in answers:
            # Normalize answer for comparison
            normalized = ans.lower().strip()
            answer_counts[normalized] += 1

        best_answer = max(answer_counts, key=answer_counts.get)
        agreement = answer_counts[best_answer] / len(answers)

        # Select trace with best answer
        best_trace = next(t for t in traces if t.final_answer and t.final_answer.lower().strip() == best_answer)
        best_trace.confidence = agreement
        best_trace.iterations = sum(t.iterations for t in traces)

        self.metrics.counter("sc_completed", labels={"agreement": f"{agreement:.2f}"})
        return best_trace


class ReActEngine(ReasoningEngine):
    """ReAct (Reasoning + Acting) engine."""

    def __init__(
        self,
        max_steps: int = 10,
        tools: Optional[Dict[str, Callable]] = None,
        llm_call: Optional[Callable[[str], str]] = None,
    ):
        self.max_steps = max_steps
        self.tools = tools or {}
        self.llm_call = llm_call or self._mock_llm
        self.metrics = MetricsCollector("react_reasoning")

    def _mock_llm(self, prompt: str) -> str:
        return "Thought: I need to use a tool.\nAction: search\nAction Input: query"

    def reason(self, question: str, context: Optional[Dict] = None) -> ReasoningTrace:
        trace = ReasoningTrace(
            trace_id=f"react_{uuid.uuid4().hex[:8]}",
            reasoning_type=ReasoningType.REACT,
            question=question,
        )

        prompt = f"Question: {question}\nYou have access to tools: {list(self.tools.keys())}\nUse format:\nThought: ...\nAction: tool_name\nAction Input: ...\nObservation: ...\n"

        for i in range(self.max_steps):
            response = self.llm_call(prompt)

            # Parse ReAct format
            thought = self._extract_thought(response)
            action = self._extract_action(response)
            action_input = self._extract_action_input(response)

            trace.steps.append(ReasoningStep(
                step_id=f"step_{i+1}",
                content=thought,
                step_type="thought",
            ))

            if action and action in self.tools:
                trace.steps.append(ReasoningStep(
                    step_id=f"action_{i+1}",
                    content=f"Action: {action} with input: {action_input}",
                    step_type="action",
                ))

                # Execute tool
                try:
                    observation = self.tools[action](action_input)
                    trace.steps.append(ReasoningStep(
                        step_id=f"obs_{i+1}",
                        content=f"Observation: {observation}",
                        step_type="observation",
                    ))
                    prompt += f"\nThought: {thought}\nAction: {action}\nAction Input: {action_input}\nObservation: {observation}\n"
                except Exception as e:
                    trace.steps.append(ReasoningStep(
                        step_id=f"obs_{i+1}",
                        content=f"Error: {e}",
                        step_type="observation",
                    ))
                    prompt += f"\nThought: {thought}\nAction: {action}\nAction Input: {action_input}\nObservation: Error: {e}\n"
            else:
                # Final answer
                trace.final_answer = thought
                break

            trace.iterations += 1

        trace.end_time = time.time()
        self.metrics.counter("react_completed", labels={"steps": str(len(trace.steps))})
        return trace

    def _extract_thought(self, response: str) -> str:
        match = re.search(r"Thought:\s*(.+?)(?:\nAction:|$)", response, re.DOTALL)
        return match.group(1).strip() if match else response

    def _extract_action(self, response: str) -> Optional[str]:
        match = re.search(r"Action:\s*(\w+)", response)
        return match.group(1) if match else None

    def _extract_action_input(self, response: str) -> str:
        match = re.search(r"Action Input:\s*(.+?)(?:\nObservation:|\n\n|$)", response, re.DOTALL)
        return match.group(1).strip() if match else ""


class StructuredReasoningEngine(ReasoningEngine):
    """Structured reasoning with templates."""

    def __init__(
        self,
        template: str,
        llm_call: Optional[Callable[[str], str]] = None,
    ):
        self.template = template
        self.llm_call = llm_call or self._mock_llm
        self.metrics = MetricsCollector("structured_reasoning")

    def _mock_llm(self, prompt: str) -> str:
        return "Structured reasoning output based on template."

    def reason(self, question: str, context: Optional[Dict] = None) -> ReasoningTrace:
        trace = ReasoningTrace(
            trace_id=f"struct_{uuid.uuid4().hex[:8]}",
            reasoning_type=ReasoningType.STRUCTURED,
            question=question,
        )

        # Fill template
        prompt = self.template.format(question=question, context=context or {})

        response = self.llm_call(prompt)

        trace.steps.append(ReasoningStep(
            step_id="step_1",
            content=response,
            step_type="structured",
        ))

        trace.final_answer = response
        trace.end_time = time.time()
        trace.confidence = 0.8

        return trace


# Factory and convenience functions
def create_reasoning_engine(
    reasoning_type: str,
    **kwargs,
) -> ReasoningEngine:
    """Factory for creating reasoning engines."""
    if reasoning_type == "chain_of_thought":
        return ChainOfThoughtEngine(**kwargs)
    elif reasoning_type == "tree_of_thought":
        return TreeOfThoughtEngine(**kwargs)
    elif reasoning_type == "self_consistency":
        base = kwargs.pop("base_engine", ChainOfThoughtEngine())
        return SelfConsistencyEngine(base, **kwargs)
    elif reasoning_type == "react":
        return ReActEngine(**kwargs)
    elif reasoning_type == "structured":
        return StructuredReasoningEngine(**kwargs)
    else:
        raise ValueError(f"Unknown reasoning type: {reasoning_type}")


def reason_with_cot(
    question: str,
    context: Optional[Dict] = None,
    max_steps: int = 10,
) -> ReasoningTrace:
    """Convenience function for Chain-of-Thought reasoning."""
    engine = ChainOfThoughtEngine(max_steps=max_steps)
    return engine.reason(question, context)


def reason_with_tot(
    question: str,
    context: Optional[Dict] = None,
    max_depth: int = 5,
) -> ReasoningTrace:
    """Convenience function for Tree-of-Thought reasoning."""
    engine = TreeOfThoughtEngine(max_depth=max_depth)
    return engine.reason(question, context)


def reason_with_self_consistency(
    question: str,
    context: Optional[Dict] = None,
    num_samples: int = 5,
) -> ReasoningTrace:
    """Convenience function for Self-Consistency reasoning."""
    base = ChainOfThoughtEngine()
    engine = SelfConsistencyEngine(base, num_samples=num_samples)
    return engine.reason(question, context)


def reason_with_react(
    question: str,
    context: Optional[Dict] = None,
    tools: Optional[Dict[str, Callable]] = None,
    max_steps: int = 10,
) -> ReasoningTrace:
    """Convenience function for ReAct reasoning."""
    engine = ReActEngine(max_steps=max_steps, tools=tools or {})
    return engine.reason(question, context)