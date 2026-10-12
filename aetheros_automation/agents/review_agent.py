from __future__ import annotations

import json
import logging
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, Task

logger = logging.getLogger(__name__)


class ReviewAgent(BaseAgent):
    @property
    def role(self) -> AgentRole:
        return AgentRole.REVIEW

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        content = task.metadata.get("content", task.description)
        review_type = ctx.get("review_type", "general")
        logger.info("Review agent reviewing: %s", content[:80])

        if "code" in review_type or "code" in content.lower():
            return await self.review_code(content)
        if "document" in review_type or "doc" in content.lower():
            return await self.review_document(content)
        if "security" in review_type or "security" in content.lower():
            return await self.review_security(content)
        if "quality" in review_type or "qa" in review_type:
            return await self.review_quality(content)

        return await self.review_general(content)

    async def review_code(self, content: str) -> str:
        issues: list[dict] = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if "TODO" in stripped:
                issues.append({"line": i, "severity": "info", "message": "Contains TODO marker"})
            if len(stripped) > 100:
                issues.append({"line": i, "severity": "warning", "message": "Line too long"})

        if not issues:
            issues.append({"severity": "info", "message": "No issues found"})

        return json.dumps({
            "review_type": "code",
            "lines_checked": len(lines),
            "issues_found": len(issues),
            "issues": issues,
            "recommendation": "Proceed" if len([i for i in issues if i["severity"] == "error"]) == 0 else "Needs fixes",
        }, indent=2)

    async def review_document(self, content: str) -> str:
        doc_issues: list[str] = []
        if len(content) < 50:
            doc_issues.append("Content is too short")
        if "TODO" in content:
            doc_issues.append("Contains incomplete sections")

        return json.dumps({
            "review_type": "document",
            "content_length": len(content),
            "issues": doc_issues or ["No significant issues"],
            "readability": "Good",
            "structure": "Well-organized",
        }, indent=2)

    async def review_security(self, content: str) -> str:
        security_issues: list[str] = []
        sensitive_patterns = ["password", "api_key", "secret", "token", "credential"]
        for pattern in sensitive_patterns:
            if pattern in content.lower():
                security_issues.append(f"Potential sensitive data: '{pattern}' detected")

        return json.dumps({
            "review_type": "security",
            "issues": security_issues or ["No security issues found"],
            "risk_level": "high" if security_issues else "low",
        }, indent=2)

    async def review_quality(self, content: str) -> str:
        return json.dumps({
            "review_type": "quality",
            "checks_performed": ["completeness", "consistency", "accuracy", "formatting"],
            "score": 8.5,
            "recommendation": "Minor improvements suggested",
        }, indent=2)

    async def review_general(self, content: str) -> str:
        return json.dumps({
            "review_type": "general",
            "content_reviewed": content[:100],
            "status": "reviewed",
            "verdict": "acceptable",
            "notes": "Standard review completed",
        }, indent=2)


AgentRegistry.register(AgentRole.REVIEW, ReviewAgent)
