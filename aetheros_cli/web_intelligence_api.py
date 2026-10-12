"""
Web Intelligence API for AetherOS Intelligence Engine.

FastAPI routes for the intelligence dashboard:
    - Intelligence Dashboard API
    - Agent Monitor API
    - Memory Viewer API
    - Knowledge Graph API
    - Planning View API
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_engine():
    """Lazy-import and return the global IntelligenceEngine."""
    from aetheros_intelligence import get_intelligence_engine
    engine = get_intelligence_engine()
    engine.initialize()
    return engine


def register_routes(app) -> None:
    """Register all intelligence API routes on a FastAPI application."""
    if app is None:
        logger.warning("No app provided for intelligence API routes")
        return

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @app.get("/api/intelligence/status")
    async def intelligence_status():
        engine = _get_engine()
        return engine.status()

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    @app.post("/api/intelligence/plan")
    async def create_plan(goal: str, description: str = "",
                          priority: str = "medium"):
        engine = _get_engine()
        return engine.plan(goal, description, priority=priority)

    @app.get("/api/intelligence/plans")
    async def list_plans(include_completed: bool = False, limit: int = 10):
        engine = _get_engine()
        return {"plans": engine.list_plans(include_completed, limit)}

    @app.get("/api/intelligence/plan/{plan_id}")
    async def get_plan(plan_id: str):
        engine = _get_engine()
        return engine.get_plan(plan_id) or {"error": "Plan not found"}

    @app.post("/api/intelligence/plan/{plan_id}/execute")
    async def execute_plan(plan_id: str):
        engine = _get_engine()
        return engine.execute_next(plan_id)

    @app.get("/api/intelligence/plan/{plan_id}/status")
    async def plan_status(plan_id: str):
        engine = _get_engine()
        return engine.get_plan_status(plan_id)

    # ------------------------------------------------------------------
    # Reasoning
    # ------------------------------------------------------------------

    @app.post("/api/intelligence/reason")
    async def reason(question: str, context: str = None):
        engine = _get_engine()
        return engine.reason(question, context)

    @app.get("/api/intelligence/reflections")
    async def reflections(limit: int = 10):
        engine = _get_engine()
        return {"reflections": engine.get_recent_reflections(limit)}

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    @app.post("/api/intelligence/context")
    async def build_context(session_id: str = "", workspace_path: str = "",
                            goal: str = ""):
        engine = _get_engine()
        return engine.get_context(session_id, workspace_path, goal)

    # ------------------------------------------------------------------
    # Model Router
    # ------------------------------------------------------------------

    @app.get("/api/intelligence/models")
    async def list_models(provider: str = None):
        engine = _get_engine()
        return {"models": engine.list_models(provider)}

    @app.post("/api/intelligence/models/select")
    async def select_model(task_type: str = "chat"):
        engine = _get_engine()
        return engine.select_model(task_type)

    # ------------------------------------------------------------------
    # Local AI
    # ------------------------------------------------------------------

    @app.get("/api/intelligence/local/backends")
    async def local_backends():
        engine = _get_engine()
        return engine.detect_local_backends()

    @app.post("/api/intelligence/local/infer")
    async def local_infer(model: str, prompt: str,
                          system_prompt: str = "",
                          temperature: float = 0.7,
                          max_tokens: int = 2048):
        engine = _get_engine()
        return engine.local_infer(model, prompt, system_prompt, temperature, max_tokens)

    # ------------------------------------------------------------------
    # Learning
    # ------------------------------------------------------------------

    @app.get("/api/intelligence/learning")
    async def get_learning():
        engine = _get_engine()
        return {
            "learned": engine.get_learned_patterns(),
            "pending": engine.get_pending_learning(),
        }

    @app.post("/api/intelligence/learning/observe")
    async def observe(category: str, observation: str,
                      pattern: str = "", auto_approve: bool = False):
        engine = _get_engine()
        return engine.observe(category, observation, pattern, auto_approve=auto_approve)

    @app.post("/api/intelligence/learning/approve/{sample_id}")
    async def approve_learning(sample_id: str):
        engine = _get_engine()
        return engine.approve_learning(sample_id) or {"error": "Sample not found"}

    @app.post("/api/intelligence/learning/reject/{sample_id}")
    async def reject_learning(sample_id: str):
        engine = _get_engine()
        return {"success": engine.reject_learning(sample_id)}

    # ------------------------------------------------------------------
    # Developer AI
    # ------------------------------------------------------------------

    @app.post("/api/intelligence/analyze")
    async def analyze_repository(path: str):
        engine = _get_engine()
        return engine.analyze_repository(path)

    @app.post("/api/intelligence/document")
    async def generate_documentation(path: str):
        engine = _get_engine()
        return engine.generate_documentation(path)

    @app.post("/api/intelligence/tests")
    async def generate_tests(path: str, framework: str = "pytest"):
        engine = _get_engine()
        return engine.generate_tests(path, framework)

    @app.get("/api/intelligence/refactor")
    async def suggest_refactoring(path: str):
        engine = _get_engine()
        return {"suggestions": engine.suggest_refactoring(path)}

    # ------------------------------------------------------------------
    # Workflow AI
    # ------------------------------------------------------------------

    @app.post("/api/intelligence/workflow/record")
    async def record_workflow(name: str, description: str = "",
                               duration_ms: float = 0.0, category: str = ""):
        engine = _get_engine()
        engine.record_workflow_step(name, description, duration_ms, category)
        return {"success": True}

    @app.get("/api/intelligence/workflow/suggestions")
    async def workflow_suggestions():
        engine = _get_engine()
        return {"suggestions": engine.get_workflow_suggestions()}

    @app.get("/api/intelligence/workflow/efficiency")
    async def workflow_efficiency():
        engine = _get_engine()
        return engine.analyze_workflow_efficiency()

    # ------------------------------------------------------------------
    # Automation AI
    # ------------------------------------------------------------------

    @app.post("/api/intelligence/automation/observe")
    async def observe_task(name: str, description: str = "",
                           duration_ms: float = 0.0):
        engine = _get_engine()
        return engine.observe_task(name, description, duration_ms)

    @app.get("/api/intelligence/automation/suggestions")
    async def automation_suggestions():
        engine = _get_engine()
        return {"suggestions": engine.get_automation_suggestions()}

    @app.post("/api/intelligence/automation/approve/{observation_id}")
    async def approve_automation(observation_id: str):
        engine = _get_engine()
        return engine.approve_automation(observation_id) or {"error": "Not found"}

    # ------------------------------------------------------------------
    # Agents / Coordinator
    # ------------------------------------------------------------------

    @app.get("/api/intelligence/agents")
    async def list_agents():
        engine = _get_engine()
        return {"agents": engine.list_specialized_agents()}

    @app.post("/api/intelligence/coordinate")
    async def coordinate(goal: str):
        engine = _get_engine()
        return engine.coordinate(goal)

    # ------------------------------------------------------------------
    # Research
    # ------------------------------------------------------------------

    @app.post("/api/intelligence/research")
    async def research(query: str, sources: List[str] = None, deep: int = 1):
        engine = _get_engine()
        if deep > 1:
            return engine.deep_research(query, deep)
        return engine.research(query, sources)

    # ------------------------------------------------------------------
    # Explainability
    # ------------------------------------------------------------------

    @app.post("/api/intelligence/explain")
    async def explain(decision: str, confidence: float = None):
        engine = _get_engine()
        return engine.explain(decision=decision, confidence=confidence)

    logger.info("Registered intelligence API routes (%d endpoints)", 28)
