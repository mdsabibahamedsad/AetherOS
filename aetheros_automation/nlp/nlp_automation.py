from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from typing import Any

from aetheros_automation.models.models import (
    AgentRole, GraphExecutionMode, RiskLevel, TaskStatus,
)
from aetheros_automation.orchestrator.types import OrchestrationPlan, OrchestrationTask

logger = logging.getLogger(__name__)


class NLPAutomationEngine:
    def __init__(self):
        self._schedule_patterns: list[dict[str, Any]] = [
            {
                "pattern": r"(every|each)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
                "type": "weekly",
            },
            {
                "pattern": r"(every|each)\s+(day|morning|afternoon|evening|night)",
                "type": "daily",
            },
            {
                "pattern": r"(every|each)\s+(\d+)\s*(hour|minute|second)s?",
                "type": "interval",
            },
            {
                "pattern": r"(once|one.?time)",
                "type": "oneshot",
            },
        ]

    async def process(self, request: str) -> OrchestrationPlan:
        plan = OrchestrationPlan(
            id=uuid.uuid4().hex[:12],
            goal=request,
            description=self._generate_description(request),
            created_at=time.time(),
        )

        plan.subtasks = await self._parse_tasks(request)
        plan.execution_graph = self._build_graph(plan.subtasks)
        plan.estimated_time = sum(t.estimated_duration for t in plan.subtasks)
        plan.estimated_cost = len(plan.subtasks) * 0.01
        plan.risk_level = await self._assess_risk(request)
        plan.required_tools = self._extract_required_tools(request)
        plan.required_agents = self._extract_required_roles(request)

        schedule = self._detect_schedule(request)
        if schedule:
            plan.metadata = {"schedule": schedule}

        return plan

    def _generate_description(self, request: str) -> str:
        return f"Automated task generated from: {request[:100]}"

    async def _parse_tasks(self, request: str) -> list[OrchestrationTask]:
        request_lower = request.lower()
        tasks: list[OrchestrationTask] = []

        connectors = [
            "and then", "then", "after that", "next", "finally",
            "subsequently", "afterwards", "following that", ", and", ",",
        ]
        parts = self._smart_split(request, connectors)

        for i, part in enumerate(parts[:10]):
            part = part.strip()
            if not part:
                continue

            role = self._infer_role(part)
            tools = self._infer_tools(part)
            requires_approval = self._needs_approval(part)

            task = OrchestrationTask(
                id=uuid.uuid4().hex[:12],
                name=part[:80],
                description=part,
                agent_role=role,
                tools=tools,
                requires_approval=requires_approval,
                estimated_duration=self._estimate_duration(part),
                created_at=time.time(),
            )
            tasks.append(task)

        if not tasks:
            tasks.append(OrchestrationTask(
                id=uuid.uuid4().hex[:12],
                name=request[:80],
                description=request,
                agent_role=self._infer_role(request),
                tools=self._infer_tools(request),
                estimated_duration=120.0,
                created_at=time.time(),
            ))

        for i in range(1, len(tasks)):
            tasks[i].dependencies.append(tasks[i - 1].id)

        return tasks

    def _smart_split(self, text: str, connectors: list[str]) -> list[str]:
        pattern = "|".join(re.escape(c) for c in connectors)
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip()]

    def _infer_role(self, text: str) -> AgentRole:
        text_lower = text.lower()
        if any(k in text_lower for k in ["research", "search", "investigate", "find", "gather"]):
            return AgentRole.RESEARCH
        if any(k in text_lower for k in ["code", "develop", "program", "implement", "build"]):
            return AgentRole.DEVELOPER
        if any(k in text_lower for k in ["write", "draft", "compose", "author", "document"]):
            return AgentRole.WRITER
        if any(k in text_lower for k in ["browse", "navigate", "scrape", "web page"]):
            return AgentRole.BROWSER
        if any(k in text_lower for k in ["test", "verify", "validate", "qa"]):
            return AgentRole.QA
        if any(k in text_lower for k in ["deploy", "release", "publish"]):
            return AgentRole.DEPLOYMENT
        if any(k in text_lower for k in ["security", "audit", "threat", "protect"]):
            return AgentRole.SECURITY
        if any(k in text_lower for k in ["creative", "design", "art", "generate image", "visual"]):
            return AgentRole.CREATIVE
        if any(k in text_lower for k in ["data", "analyze", "statistic", "report", "chart"]):
            return AgentRole.DATA
        if any(k in text_lower for k in ["email", "message", "communicate", "notify", "send"]):
            return AgentRole.COMMUNICATION
        if any(k in text_lower for k in ["review", "check", "proofread", "examine"]):
            return AgentRole.REVIEW
        if any(k in text_lower for k in ["file", "save", "open", "read file"]):
            return AgentRole.FILE
        if any(k in text_lower for k in ["plan", "organize", "coordinate", "manage"]):
            return AgentRole.PLANNER
        return AgentRole.COORDINATOR

    def _infer_tools(self, text: str) -> list[str]:
        tools = []
        text_lower = text.lower()
        if any(k in text_lower for k in ["search", "research", "web", "find"]):
            tools.append("web_search")
        if any(k in text_lower for k in ["browse", "navigate", "web page"]):
            tools.append("browser_navigate")
        if any(k in text_lower for k in ["file", "save", "read", "write", "create"]):
            tools.append("file_operations")
        if any(k in text_lower for k in ["terminal", "command", "run", "shell"]):
            tools.append("terminal")
        if any(k in text_lower for k in ["code", "develop", "program"]):
            tools.append("code_execution")
        if any(k in text_lower for k in ["email", "send", "message"]):
            tools.append("send_message")
        if any(k in text_lower for k in ["image", "picture", "visual", "chart"]):
            tools.append("vision")
        if any(k in text_lower for k in ["data", "analyze", "report", "chart"]):
            tools.append("data_analysis")
        return tools

    def _needs_approval(self, text: str) -> bool:
        text_lower = text.lower()
        keywords = ["delete", "remove", "destroy", "payment", "spend", "buy",
                     "install", "permission", "send email", "post", "publish"]
        return any(k in text_lower for k in keywords)

    def _estimate_duration(self, text: str) -> float:
        text_lower = text.lower()
        if any(k in text_lower for k in ["research", "investigate"]):
            return 120.0
        if any(k in text_lower for k in ["code", "develop", "implement", "build"]):
            return 300.0
        if any(k in text_lower for k in ["browse", "scrape"]):
            return 60.0
        if any(k in text_lower for k in ["analyze", "data", "report"]):
            return 180.0
        if any(k in text_lower for k in ["write", "draft", "compose"]):
            return 120.0
        return 60.0

    def _build_graph(self, tasks: list[OrchestrationTask]) -> dict[str, Any]:
        nodes = [{"id": t.id, "name": t.name, "role": t.agent_role.value} for t in tasks]
        edges = [{"from": dep, "to": t.id} for t in tasks for dep in t.dependencies]
        return {"nodes": nodes, "edges": edges}

    async def _assess_risk(self, request: str) -> RiskLevel:
        request_lower = request.lower()
        high_risk = ["delete", "destroy", "payment", "install", "permission"]
        count = sum(1 for k in high_risk if k in request_lower)
        if count >= 2:
            return RiskLevel.HIGH
        if count >= 1:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _extract_required_tools(self, request: str) -> list[str]:
        return self._infer_tools(request)

    def _extract_required_roles(self, request: str) -> list[AgentRole]:
        roles: list[AgentRole] = []
        text_lower = request.lower()
        if any(k in text_lower for k in ["research", "search", "find"]):
            roles.append(AgentRole.RESEARCH)
        if any(k in text_lower for k in ["code", "develop", "program"]):
            roles.append(AgentRole.DEVELOPER)
        if any(k in text_lower for k in ["write", "draft"]):
            roles.append(AgentRole.WRITER)
        if any(k in text_lower for k in ["creative", "design"]):
            roles.append(AgentRole.CREATIVE)
        if any(k in text_lower for k in ["data", "analyze"]):
            roles.append(AgentRole.DATA)
        return roles

    def _detect_schedule(self, request: str) -> dict[str, Any] | None:
        request_lower = request.lower()
        for sp in self._schedule_patterns:
            match = re.search(sp["pattern"], request_lower)
            if match:
                schedule_type = sp["type"]
                interval = None
                if schedule_type == "interval" and match.groups() and len(match.groups()) >= 2:
                    try:
                        interval = f"every {match.group(2)} {match.group(3)}s"
                    except (IndexError, ValueError):
                        interval = "1h"
                return {
                    "type": schedule_type,
                    "interval": interval or "1d",
                    "matched": match.group(0),
                }
        return None

    def add_schedule_pattern(self, pattern: str, schedule_type: str):
        self._schedule_patterns.append({"pattern": pattern, "type": schedule_type})

    def get_schedule_types(self) -> list[str]:
        return list(set(sp["type"] for sp in self._schedule_patterns))
