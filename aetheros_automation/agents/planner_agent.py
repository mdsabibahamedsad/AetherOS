from __future__ import annotations

import logging
import time
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, Task, TaskStatus

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    @property
    def role(self) -> AgentRole:
        return AgentRole.PLANNER

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        goal = task.description
        logger.info("Planner analyzing goal: %s", goal[:80])

        steps = self._decompose_goal(goal, ctx)
        effort = await self.estimate_effort(task)

        plan = {
            "goal": goal,
            "steps": steps,
            "estimated_duration": effort["duration"],
            "complexity": effort["complexity"],
            "risks": effort["risks"],
        }

        task.metadata["plan"] = plan
        task.status = TaskStatus.PENDING

        formatted = self._format_plan(plan)
        logger.info("Plan produced with %d steps, complexity=%s", len(steps), effort["complexity"])
        return formatted

    def _decompose_goal(self, goal: str, context: dict) -> list[dict]:
        lines = goal.strip().split("\n")
        steps: list[dict] = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            steps.append({
                "step": i + 1,
                "description": line,
                "agent": self._infer_agent(line),
                "dependencies": [],
                "estimated_duration": 60.0,
            })

        if not steps:
            steps.append({
                "step": 1,
                "description": goal,
                "agent": "developer",
                "dependencies": [],
                "estimated_duration": 120.0,
            })

        return steps

    def _infer_agent(self, description: str) -> str:
        lower = description.lower()
        if any(w in lower for w in ("research", "search", "find", "investigate")):
            return "research"
        if any(w in lower for w in ("code", "implement", "develop", "write function", "fix")):
            return "developer"
        if any(w in lower for w in ("browse", "navigate", "scrape", "crawl")):
            return "browser"
        if any(w in lower for w in ("write", "document", "draft", "compose")):
            return "writer"
        if any(w in lower for w in ("test", "validate", "verify", "qa")):
            return "qa"
        if any(w in lower for w in ("deploy", "release", "publish")):
            return "deployment"
        if any(w in lower for w in ("audit", "security", "vulnerability")):
            return "security"
        if any(w in lower for w in ("remember", "memorize", "store")):
            return "memory"
        return "developer"

    async def estimate_effort(self, task: Task) -> dict:
        desc = task.description.lower()
        word_count = len(desc.split())

        if any(w in desc for w in ("complex", "large", "multi-step", "full")):
            complexity = "high"
            duration = word_count * 10.0
            risks = ["Scope creep", "Dependency chain complexity", "Multiple integration points"]
        elif any(w in desc for w in ("simple", "small", "quick", "minor", "trivial")):
            complexity = "low"
            duration = max(30.0, word_count * 2.0)
            risks = []
        else:
            complexity = "medium"
            duration = max(60.0, word_count * 5.0)
            risks = ["Incomplete specification", "Hidden dependencies"]

        return {
            "duration": min(duration, 3600.0),
            "complexity": complexity,
            "risks": risks,
        }

    def _format_plan(self, plan: dict) -> str:
        lines = [f"# Plan\nGoal: {plan['goal']}\n"]
        lines.append(f"Estimated duration: {plan['estimated_duration']:.0f}s")
        lines.append(f"Complexity: {plan['complexity']}")
        if plan["risks"]:
            lines.append("Risks:")
            for r in plan["risks"]:
                lines.append(f"  - {r}")
        lines.append("\n## Steps")
        for step in plan["steps"]:
            lines.append(f"\n{step['step']}. {step['description']}")
            lines.append(f"   Agent: {step['agent']}")
            lines.append(f"   Estimated: {step['estimated_duration']:.0f}s")
        return "\n".join(lines)


AgentRegistry.register(AgentRole.PLANNER, PlannerAgent)
