from __future__ import annotations

import logging
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    ModelRoute, ModelCapability, AgentRole, TaskType,
)

logger = logging.getLogger(__name__)

_ROLE_MODEL_MAP: dict[AgentRole, dict[str, Any]] = {
    AgentRole.RESEARCH: {
        "recommended": "claude-sonnet-4-20250514",
        "fallback": "gpt-4o",
        "provider": "anthropic",
        "fallback_provider": "openai",
        "reason": "Broad knowledge, long context for research",
        "supports_tools": True,
        "context_size": 200000,
    },
    AgentRole.CODING: {
        "recommended": "claude-sonnet-4-20250514",
        "fallback": "gpt-4o",
        "provider": "anthropic",
        "fallback_provider": "openai",
        "reason": "Strong coding and reasoning capabilities",
        "supports_tools": True,
        "context_size": 200000,
    },
    AgentRole.BROWSER: {
        "recommended": "claude-sonnet-4-20250514",
        "fallback": "gpt-4o",
        "provider": "anthropic",
        "fallback_provider": "openai",
        "reason": "Fast responses for web navigation",
        "supports_tools": True,
        "context_size": 100000,
    },
    AgentRole.FILE: {
        "recommended": "claude-sonnet-4-20250514",
        "fallback": "gpt-4o-mini",
        "provider": "anthropic",
        "fallback_provider": "openai",
        "reason": "Sufficient for file operations",
        "supports_tools": True,
        "context_size": 100000,
    },
    AgentRole.DATA: {
        "recommended": "claude-sonnet-4-20250514",
        "fallback": "gpt-4o",
        "provider": "anthropic",
        "fallback_provider": "openai",
        "reason": "Strong analytical capabilities",
        "supports_tools": True,
        "context_size": 200000,
    },
    AgentRole.COMMUNICATION: {
        "recommended": "gpt-4o",
        "fallback": "claude-sonnet-4-20250514",
        "provider": "openai",
        "fallback_provider": "anthropic",
        "reason": "Well-suited for professional communication",
        "supports_tools": True,
        "context_size": 128000,
    },
    AgentRole.PLANNER: {
        "recommended": "claude-sonnet-4-20250514",
        "fallback": "gpt-4o",
        "provider": "anthropic",
        "fallback_provider": "openai",
        "reason": "Strong reasoning for planning",
        "supports_tools": False,
        "context_size": 200000,
    },
    AgentRole.REVIEW: {
        "recommended": "claude-sonnet-4-20250514",
        "fallback": "gpt-4o",
        "provider": "anthropic",
        "fallback_provider": "openai",
        "reason": "Thorough review requires strong analysis",
        "supports_tools": True,
        "context_size": 200000,
    },
    AgentRole.SECURITY: {
        "recommended": "claude-sonnet-4-20250514",
        "fallback": "gpt-4o",
        "provider": "anthropic",
        "fallback_provider": "openai",
        "reason": "Security analysis needs strong reasoning",
        "supports_tools": True,
        "context_size": 200000,
    },
    AgentRole.CREATIVE: {
        "recommended": "gpt-4o",
        "fallback": "claude-sonnet-4-20250514",
        "provider": "openai",
        "fallback_provider": "anthropic",
        "reason": "Creative tasks benefit from balanced output",
        "supports_tools": True,
        "context_size": 128000,
    },
    AgentRole.COORDINATOR: {
        "recommended": "claude-sonnet-4-20250514",
        "fallback": "gpt-4o",
        "provider": "anthropic",
        "fallback_provider": "openai",
        "reason": "Coordination requires broad understanding",
        "supports_tools": True,
        "context_size": 200000,
    },
    AgentRole.COORDINATOR: {
        "recommended": "claude-sonnet-4-20250514",
        "fallback": "gpt-4o",
        "provider": "anthropic",
        "fallback_provider": "openai",
        "reason": "General-purpose strong model",
        "supports_tools": True,
        "context_size": 200000,
    },
}


class ModelRouter:
    def __init__(self):
        self._custom_routes: dict[str, ModelRoute] = {}

    def route_for_role(self, role: AgentRole) -> ModelRoute:
        config = _ROLE_MODEL_MAP.get(role, _ROLE_MODEL_MAP[AgentRole.COORDINATOR])
        return ModelRoute(
            task_type=role.value if hasattr(role, 'value') else str(role),
            recommended_model=config["recommended"],
            recommended_provider=config["provider"],
            fallback_model=config["fallback"],
            fallback_provider=config["fallback_provider"],
            reason=config["reason"],
            supports_tools=config.get("supports_tools", True),
            context_size=config.get("context_size", 100000),
        )

    def route_for_task(self, task_type: str, capabilities: Optional[list[str]] = None) -> ModelRoute:
        if task_type in self._custom_routes:
            return self._custom_routes[task_type]
        return self.route_for_role(AgentRole.COORDINATOR)

    def register_custom_route(self, task_type: str, route: ModelRoute):
        self._custom_routes[task_type] = route

    def supports_capability(
        self, model: str, capability: ModelCapability
    ) -> bool:
        capability_map: dict[str, list[ModelCapability]] = {
            "claude-sonnet-4-20250514": [
                ModelCapability.REASONING, ModelCapability.CODING,
                ModelCapability.TOOL_USE, ModelCapability.LARGE_CONTEXT,
            ],
            "gpt-4o": [
                ModelCapability.REASONING, ModelCapability.CODING,
                ModelCapability.VISION, ModelCapability.TOOL_USE,
            ],
            "gpt-4o-mini": [
                ModelCapability.FAST, ModelCapability.CHEAP,
                ModelCapability.TOOL_USE,
            ],
        }
        caps = capability_map.get(model, [])
        return capability in caps

    def select_best_model(
        self,
        task_type: str,
        required_capabilities: list[ModelCapability],
        prefer_local: bool = False,
        max_cost: float = 0.0,
    ) -> ModelRoute:
        role = AgentRole.COORDINATOR
        for r in AgentRole:
            if r.value == task_type:
                role = r
                break
        route = self.route_for_role(role)
        if prefer_local:
            pass
        return route

    def list_available_routes(self) -> list[dict]:
        routes = []
        for role in AgentRole:
            route = self.route_for_role(role)
            routes.append({
                "role": role.value if hasattr(role, 'value') else str(role),
                "model": route.recommended_model,
                "provider": route.recommended_provider,
                "fallback": route.fallback_model,
                "context_size": route.context_size,
                "supports_tools": route.supports_tools,
                "reason": route.reason,
            })
        return routes
