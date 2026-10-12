from __future__ import annotations

import logging
import re
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    NLCommand, AgentRole, Objective, TaskPriority,
)

logger = logging.getLogger(__name__)

_SCHEDULE_PATTERNS = [
    re.compile(r"(?:every|each)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", re.I),
    re.compile(r"(?:every|each)\s+(\d+)\s*(?:hour|minute|day|week|month)", re.I),
    re.compile(r"daily|weekly|monthly", re.I),
    re.compile(r"at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)", re.I),
]

_ROLE_KEYWORDS: list[tuple[list[str], AgentRole]] = [
    (["research", "investigate", "search for", "find", "look up", "gather", "explore"], AgentRole.RESEARCH),
    (["code", "write code", "program", "implement", "build", "develop", "script"], AgentRole.CODING),
    (["browse", "navigate", "visit", "open web", "web page", "website"], AgentRole.BROWSER),
    (["save", "write file", "create file", "export", "download"], AgentRole.FILE),
    (["analyze", "analyse", "process data", "compute", "calculate", "aggregate"], AgentRole.DATA),
    (["email", "send", "message", "notify", "communicate"], AgentRole.COMMUNICATION),
    (["plan", "organize", "coordinate", "arrange"], AgentRole.PLANNER),
    (["review", "verify", "validate", "check", "audit"], AgentRole.REVIEW),
    (["design", "create", "generate content", "write", "draft", "compose", "illustrate"], AgentRole.CREATIVE),
]

_TOOL_KEYWORDS: list[tuple[list[str], str]] = [
    (["search web", "find online", "look up", "research"], "web_search"),
    (["open web", "visit page", "navigate"], "browser_navigate"),
    (["save file", "write to", "create file", "export"], "write_file"),
    (["read file", "open file"], "read_file"),
    (["run code", "execute", "run terminal", "run command"], "run_terminal"),
    (["send email", "email"], "send_email"),
    (["search files", "find files"], "search_files"),
    (["analyze image", "look at image", "vision"], "vision_analyze"),
]

_PERMISSION_KEYWORDS: list[tuple[list[str], str]] = [
    (["write file", "save file", "create file", "modify file"], "filesystem_write"),
    (["delete", "remove file"], "filesystem_delete"),
    (["send email", "email"], "send_email"),
    (["browse", "navigate web"], "browser"),
    (["deploy", "publish"], "deploy"),
]


class NLParser:
    def parse(self, text: str) -> NLCommand:
        command = NLCommand(raw_text=text, goal=text)
        command.intent = self._detect_intent(text)
        command.goal = text
        command.schedule = self._extract_schedule(text)
        command.agents = self._extract_agents(text)
        command.tools = self._extract_tools(text)
        command.permissions = self._extract_permissions(text)
        command.output_format = self._extract_output_format(text)
        command.constraints = self._extract_constraints(text)
        return command

    def _detect_intent(self, text: str) -> str:
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["every", "each", "daily", "weekly", "monthly", "schedule"]):
            return "scheduled_task"
        if any(kw in text_lower for kw in ["research", "investigate", "find out", "look up"]):
            return "research"
        if any(kw in text_lower for kw in ["code", "write", "program", "implement", "build"]):
            return "development"
        if any(kw in text_lower for kw in ["analyze", "analyse", "compare", "evaluate"]):
            return "analysis"
        if any(kw in text_lower for kw in ["email", "send", "message", "notify"]):
            return "communication"
        if any(kw in text_lower for kw in ["create", "generate", "design", "draft"]):
            return "creation"
        return "general"

    def _extract_schedule(self, text: str) -> str:
        for pattern in _SCHEDULE_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return ""

    def _extract_agents(self, text: str) -> list[AgentRole]:
        text_lower = text.lower()
        agents: list[AgentRole] = []
        for keywords, role in _ROLE_KEYWORDS:
            if any(kw in text_lower for kw in keywords):
                if role not in agents:
                    agents.append(role)
        if not agents:
            agents.append(AgentRole.COORDINATOR)
        return agents

    def _extract_tools(self, text: str) -> list[str]:
        text_lower = text.lower()
        tools: list[str] = []
        for keywords, tool in _TOOL_KEYWORDS:
            if any(kw in text_lower for kw in keywords):
                if tool not in tools:
                    tools.append(tool)
        return tools

    def _extract_permissions(self, text: str) -> list[str]:
        text_lower = text.lower()
        permissions: list[str] = []
        for keywords, perm in _PERMISSION_KEYWORDS:
            if any(kw in text_lower for kw in keywords):
                if perm not in permissions:
                    permissions.append(perm)
        return permissions

    def _extract_output_format(self, text: str) -> str:
        text_lower = text.lower()
        if "pdf" in text_lower:
            return "pdf"
        if "csv" in text_lower:
            return "csv"
        if "json" in text_lower:
            return "json"
        if "html" in text_lower:
            return "html"
        if "markdown" in text_lower or "md" in text_lower.split():
            return "markdown"
        return ""

    def _extract_constraints(self, text: str) -> list[str]:
        constraints: list[str] = []
        if "urgent" in text.lower() or "asap" in text.lower():
            constraints.append("urgent")
        if "confidential" in text.lower() or "private" in text.lower():
            constraints.append("confidential")
        return constraints
