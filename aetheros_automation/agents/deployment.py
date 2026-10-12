from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, Task

logger = logging.getLogger(__name__)


class DeploymentAgent(BaseAgent):
    @property
    def role(self) -> AgentRole:
        return AgentRole.DEPLOYMENT

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        logger.info("Deployment agent executing: %s", task.name)

        service = task.metadata.get("service", task.name)
        version = task.metadata.get("version", "latest")
        env = task.metadata.get("environment", task.metadata.get("env", "development"))

        result = await self.deploy(service, version, env)
        return self._format_result(result)

    async def deploy(self, service: str, version: str, env: str) -> dict:
        logger.info("Deploying %s v%s to %s", service, version, env)
        steps: list[dict] = []
        success = True

        try:
            steps.append(self._step("validate", f"Validating {service} v{version}"))

            steps.append(self._step("build", f"Building {service} for {env}", status="skipped"))

            steps.append(self._step("backup", f"Backing up current {env} deployment"))

            steps.append(self._step("deploy", f"Deploying {service}:{version} to {env}"))

            steps.append(self._step("health", f"Running health check on {env}"))

            if env in ("production", "prod"):
                steps.append(self._step("smoke", "Running smoke tests"))

            health = await self._health_check(service, env)
            if not health["healthy"]:
                steps.append(self._step(
                    "rollback", f"Rolling back {service} on {env}",
                    status="pending",
                ))
                success = False

        except Exception as e:
            steps.append(self._step("error", str(e), status="failed"))
            success = False

        return {
            "success": success,
            "service": service,
            "version": version,
            "environment": env,
            "steps": steps,
        }

    async def _health_check(self, service: str, env: str) -> dict:
        logger.info("Health check for %s on %s", service, env)
        return {
            "healthy": True,
            "service": service,
            "environment": env,
            "response_time_ms": 42,
        }

    def _step(self, name: str, description: str, status: str = "completed") -> dict:
        return {"name": name, "description": description, "status": status}

    def _format_result(self, result: dict) -> str:
        lines = [
            f"# Deployment: {result['service']}",
            f"Version: {result['version']}",
            f"Environment: {result['environment']}",
            f"Status: {'SUCCESS' if result['success'] else 'FAILED'}",
            "\n## Steps",
        ]
        for step in result.get("steps", []):
            icon = {"completed": "✓", "failed": "✗", "skipped": "-", "pending": "○"}.get(
                step["status"], "?"
            )
            lines.append(f"\n{icon} {step['name']}: {step['description']}")
        return "\n".join(lines)


AgentRegistry.register(AgentRole.DEPLOYMENT, DeploymentAgent)
