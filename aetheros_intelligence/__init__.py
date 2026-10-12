"""
Aether Intelligence Engine
=========================

The cognitive layer of AetherOS. Integrates planning, reasoning, learning,
knowledge, and multi-agent subsystems into a unified intelligence pipeline.

Architecture::

    aetheros_intelligence/
        __init__.py          IntelligenceEngine + version
        planning.py          Task Planning (hierarchical, goal decomposition)
        reasoning.py         Reasoning Pipeline (reflection, self-critique,
                              chain verification, confidence scoring)
        context.py           Context Awareness Engine
        model_router.py      Model Router (automatic model selection)
        local_ai.py          Local AI (Ollama, llama.cpp, vLLM, etc.)
        learning.py          Learning System (user-approved)
        developer_ai.py      Developer AI (code analysis, docs, tests)
        workflow_ai.py       Workflow AI (optimization, suggestions)
        automation_ai.py     Automation AI (task observation, suggestions)
        explainability.py    Explainability Framework
        research.py          Research Mode (multi-source)
        project_understanding.py  Project Understanding
        cli/                 CLI command integrations
        web_ui/              Web dashboard integrations

Design Principles:
    - Everything modular — each subsystem is independently usable
    - Everything observable — all reasoning steps logged
    - Everything permission-based — user controls all learning
    - Everything privacy-first — no data leaves without consent
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

__version__: str = "1.1.0"


class IntelligenceEngine:
    """Unified interface for the Aether Intelligence Engine.

    Orchestrates all intelligence capabilities: planning, reasoning,
    context awareness, model routing, local AI, learning, developer AI,
    workflow AI, automation AI, research, project understanding,
    and explainability.

    Usage::

        from aetheros_intelligence import IntelligenceEngine

        engine = IntelligenceEngine()
        engine.initialize()

        # Planning
        plan = engine.plan("Build a CLI tool")

        # Reasoning
        result = engine.reason("How should I structure this API?")

        # Context
        ctx = engine.get_context(session_id="sess_123")

        # Research
        report = engine.research("Latest Python async patterns")

        # Learning
        engine.observe("coding_style", "Uses snake_case")
        engine.approve_learning(sample_id)

        # Local AI
        result = engine.local_infer("llama3.2", "What is Python?")
    """

    def __init__(self) -> None:
        self._initialized = False
        self._planning = None
        self._reasoning = None
        self._context = None
        self._model_router = None
        self._local_ai = None
        self._learning = None
        self._developer_ai = None
        self._workflow_ai = None
        self._automation_ai = None
        self._research = None
        self._project_understanding = None
        self._explainability = None
        self._coordinator = None

    def initialize(self) -> bool:
        """Initialize all intelligence subsystems.

        Returns:
            True if all subsystems initialized successfully
        """
        if self._initialized:
            return True

        try:
            from aetheros_intelligence.planning import PlanningEngine
            from aetheros_intelligence.reasoning import ReasoningPipeline
            from aetheros_intelligence.context import ContextEngine
            from aetheros_intelligence.model_router import ModelRouter
            from aetheros_intelligence.local_ai import LocalAI
            from aetheros_intelligence.learning import LearningEngine
            from aetheros_intelligence.developer_ai import DeveloperAI
            from aetheros_intelligence.workflow_ai import WorkflowAI
            from aetheros_intelligence.automation_ai import AutomationAI
            from aetheros_intelligence.research import ResearchMode
            from aetheros_intelligence.project_understanding import ProjectUnderstanding
            from aetheros_intelligence.explainability import ExplainabilityFramework

            self._planning = PlanningEngine()
            self._reasoning = ReasoningPipeline()
            self._context = ContextEngine()
            self._model_router = ModelRouter()
            self._local_ai = LocalAI()
            self._learning = LearningEngine()
            self._developer_ai = DeveloperAI()
            self._workflow_ai = WorkflowAI()
            self._automation_ai = AutomationAI()
            self._research = ResearchMode()
            self._project_understanding = ProjectUnderstanding()
            self._explainability = ExplainabilityFramework()

            self._initialized = True
            logger.info("IntelligenceEngine v%s initialized (%d subsystems)",
                        __version__, 13)
            return True

        except Exception as exc:
            logger.error("IntelligenceEngine: initialization failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def plan(self, goal: str, description: str = "",
             context: dict = None, priority: str = "medium") -> dict:
        """Create a plan from a goal."""
        if not self._initialized:
            self.initialize()
        return self._planning.create_plan(goal, description, context, priority)

    def get_plan(self, plan_id: str) -> Optional[dict]:
        return self._planning.get_plan(plan_id)

    def list_plans(self, include_completed: bool = False, limit: int = 10) -> list:
        return self._planning.list_plans(include_completed, limit)

    def execute_next(self, plan_id: str, agent: str = "") -> dict:
        return self._planning.execute_next(plan_id, agent)

    def get_plan_status(self, plan_id: str = None) -> dict:
        return self._planning.get_plan_status(plan_id)

    def refine_plan(self, plan_id: str, feedback: str) -> Optional[dict]:
        return self._planning.refine_plan(plan_id, feedback)

    # ------------------------------------------------------------------
    # Reasoning
    # ------------------------------------------------------------------

    def reason(self, question: str, context: Any = None) -> dict:
        if not self._initialized:
            self.initialize()
        return self._reasoning.reason(question, context=context)

    def reflect(self, goal: str, outcome: str,
                successes: list = None, failures: list = None,
                lessons: list = None) -> dict:
        return self._reasoning.reflect(
            goal=goal, outcome=outcome,
            successes=successes, failures=failures, lessons=lessons,
        )

    def get_recent_reflections(self, limit: int = 10) -> list:
        return self._reasoning.get_recent_reflections(limit)

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def get_context(self, session_id: str = "", workspace_path: str = "",
                    goal: str = "", plan_id: str = "", task: str = "") -> dict:
        if not self._initialized:
            self.initialize()
        return self._context.build_context(
            session_id=session_id, workspace_path=workspace_path,
            goal=goal, plan_id=plan_id, task=task,
        )

    def enrich_context(self, additional_context: dict) -> dict:
        return self._context.enrich_context(additional_context)

    # ------------------------------------------------------------------
    # Model Router
    # ------------------------------------------------------------------

    def select_model(self, task_type: str = None) -> dict:
        if not self._initialized:
            self.initialize()
        if task_type:
            return self._model_router.select_for_task(task_type)
        return self._model_router.select()

    def list_models(self, provider: str = None) -> list:
        return self._model_router.list_models(provider)

    # ------------------------------------------------------------------
    # Local AI
    # ------------------------------------------------------------------

    def local_infer(self, model: str, prompt: str,
                    system_prompt: str = "",
                    temperature: float = 0.7,
                    max_tokens: int = 2048) -> dict:
        if not self._initialized:
            self.initialize()
        return self._local_ai.infer(
            model, prompt, system_prompt, temperature, max_tokens,
        )

    def detect_local_backends(self) -> dict:
        return self._local_ai.detect_backends()

    # ------------------------------------------------------------------
    # Learning
    # ------------------------------------------------------------------

    def observe(self, category: str, observation: str,
                pattern: str = "", context: str = "",
                auto_approve: bool = False) -> dict:
        if not self._initialized:
            self.initialize()
        return self._learning.observe(category, observation, pattern, context, auto_approve)

    def get_pending_learning(self, category: str = None) -> list:
        return self._learning.get_pending(category)

    def approve_learning(self, sample_id: str) -> Optional[dict]:
        return self._learning.approve(sample_id)

    def approve_all_learning(self, category: str = None) -> int:
        return self._learning.approve_all(category)

    def reject_learning(self, sample_id: str) -> bool:
        return self._learning.reject(sample_id)

    def get_learned_patterns(self, category: str = None):
        if category:
            return self._learning.get_learned(category)
        return self._learning.get_all_learned()

    # ------------------------------------------------------------------
    # Developer AI
    # ------------------------------------------------------------------

    def analyze_repository(self, path: str) -> dict:
        if not self._initialized:
            self.initialize()
        return self._developer_ai.analyze_repository(path)

    def generate_documentation(self, path: str) -> dict:
        return self._developer_ai.generate_documentation(path)

    def explain_code(self, path: str, function_name: str = "",
                     line_start: int = 0, line_end: int = 0) -> dict:
        return self._developer_ai.explain_code(path, function_name, line_start, line_end)

    def generate_tests(self, path: str, framework: str = "pytest") -> dict:
        return self._developer_ai.generate_tests(path, framework)

    def suggest_refactoring(self, path: str) -> list:
        return self._developer_ai.suggest_refactoring(path)

    # ------------------------------------------------------------------
    # Workflow AI
    # ------------------------------------------------------------------

    def record_workflow_step(self, name: str, description: str = "",
                              duration_ms: float = 0.0, category: str = "",
                              workflow: str = "") -> None:
        if not self._initialized:
            self.initialize()
        self._workflow_ai.record_step(name, description, duration_ms, category, workflow)

    def get_workflow_suggestions(self) -> list:
        return self._workflow_ai.get_suggestions()

    def analyze_workflow_efficiency(self) -> dict:
        return self._workflow_ai.analyze_efficiency()

    # ------------------------------------------------------------------
    # Automation AI
    # ------------------------------------------------------------------

    def observe_task(self, name: str, description: str = "",
                     duration_ms: float = 0.0) -> dict:
        if not self._initialized:
            self.initialize()
        return self._automation_ai.observe_task(name, description, duration_ms=duration_ms)

    def get_automation_suggestions(self) -> list:
        return self._automation_ai.get_suggestions()

    def approve_automation(self, observation_id: str) -> Optional[dict]:
        return self._automation_ai.approve_automation(observation_id)

    def generate_automation(self, observation_id: str) -> Optional[dict]:
        return self._automation_ai.generate_automation(observation_id)

    # ------------------------------------------------------------------
    # Research
    # ------------------------------------------------------------------

    def research(self, query: str, sources: list = None) -> dict:
        if not self._initialized:
            self.initialize()
        return self._research.research(query, sources=sources)

    def deep_research(self, topic: str, depth: int = 2) -> dict:
        if not self._initialized:
            self.initialize()
        return self._research.deep_research(topic, depth=depth)

    # ------------------------------------------------------------------
    # Project Understanding
    # ------------------------------------------------------------------

    def analyze_project(self, path: str) -> dict:
        if not self._initialized:
            self.initialize()
        return self._project_understanding.analyze(path)

    def understand_file(self, path: str) -> dict:
        return self._project_understanding.understand_file(path)

    # ------------------------------------------------------------------
    # Explainability
    # ------------------------------------------------------------------

    def explain(self, recommendation_id: str = None,
                decision: str = None, confidence: float = None,
                alternatives: list = None, tradeoffs: list = None) -> dict:
        if not self._initialized:
            self.initialize()
        return self._explainability.explain(
            recommendation_id=recommendation_id, decision=decision,
            confidence=confidence, alternatives=alternatives,
            tradeoffs=tradeoffs,
        )

    def explain_recommendation(self, recommendation: dict) -> dict:
        return self._explainability.explain_recommendation(recommendation)

    # ------------------------------------------------------------------
    # Coordinator
    # ------------------------------------------------------------------

    def coordinate(self, goal: str, context: dict = None) -> dict:
        if not self._initialized:
            self.initialize()
        from agents.specialized import Coordinator
        if self._coordinator is None:
            self._coordinator = Coordinator()
        return self._coordinator.plan_execution(goal, context)

    def list_specialized_agents(self) -> list:
        from agents.specialized import list_specialized_agents
        return list_specialized_agents()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Get overall intelligence engine status."""
        status = {
            "version": __version__,
            "initialized": self._initialized,
        }
        if not self._initialized:
            return status

        subsystems = {
            "planning": self._planning,
            "reasoning": self._reasoning,
            "context": self._context,
            "model_router": self._model_router,
            "local_ai": self._local_ai,
            "learning": self._learning,
            "developer_ai": self._developer_ai,
            "workflow_ai": self._workflow_ai,
            "automation_ai": self._automation_ai,
            "research": self._research,
            "project_understanding": self._project_understanding,
            "explainability": self._explainability,
        }
        for name, instance in subsystems.items():
            if instance is not None:
                try:
                    stats = instance.get_stats()
                    status[name] = stats if isinstance(stats, dict) else {"status": "available"}
                except Exception:
                    status[name] = {"status": "available"}

        status["agent_roles"] = 13
        return status


# Global intelligence engine
_intelligence_engine: IntelligenceEngine | None = None


def get_intelligence_engine() -> IntelligenceEngine:
    """Return the global IntelligenceEngine singleton."""
    global _intelligence_engine
    if _intelligence_engine is None:
        _intelligence_engine = IntelligenceEngine()
    return _intelligence_engine
