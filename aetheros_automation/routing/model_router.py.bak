from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_MODEL_CAPABILITIES: dict[str, dict[str, Any]] = {
    "gpt-4o": {
        "provider": "openai",
        "reasoning": "high",
        "coding": "high",
        "vision": True,
        "audio": True,
        "context": 128000,
        "latency": "medium",
        "cost_per_1k_input": 0.0025,
        "cost_per_1k_output": 0.01,
        "privacy": "cloud",
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "reasoning": "medium",
        "coding": "medium",
        "vision": True,
        "audio": False,
        "context": 128000,
        "latency": "low",
        "cost_per_1k_input": 0.00015,
        "cost_per_1k_output": 0.0006,
        "privacy": "cloud",
    },
    "claude-sonnet-4-20250514": {
        "provider": "anthropic",
        "reasoning": "high",
        "coding": "high",
        "vision": True,
        "audio": False,
        "context": 200000,
        "latency": "medium",
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "privacy": "cloud",
    },
    "claude-haiku-3-5-20241022": {
        "provider": "anthropic",
        "reasoning": "medium",
        "coding": "medium",
        "vision": True,
        "audio": False,
        "context": 200000,
        "latency": "low",
        "cost_per_1k_input": 0.0008,
        "cost_per_1k_output": 0.004,
        "privacy": "cloud",
    },
    "gemini-2.5-pro": {
        "provider": "gemini",
        "reasoning": "high",
        "coding": "high",
        "vision": True,
        "audio": True,
        "context": 1000000,
        "latency": "medium",
        "cost_per_1k_input": 0.00125,
        "cost_per_1k_output": 0.005,
        "privacy": "cloud",
    },
    "deepseek-chat": {
        "provider": "deepseek",
        "reasoning": "high",
        "coding": "high",
        "vision": False,
        "audio": False,
        "context": 128000,
        "latency": "low",
        "cost_per_1k_input": 0.00014,
        "cost_per_1k_output": 0.00028,
        "privacy": "cloud",
    },
    "llama-3.1-8b": {
        "provider": "local",
        "reasoning": "low",
        "coding": "low",
        "vision": False,
        "audio": False,
        "context": 8192,
        "latency": "low",
        "cost_per_1k_input": 0.0,
        "cost_per_1k_output": 0.0,
        "privacy": "local",
    },
    "llama-3.1-70b": {
        "provider": "local",
        "reasoning": "medium",
        "coding": "medium",
        "vision": False,
        "audio": False,
        "context": 8192,
        "latency": "high",
        "cost_per_1k_input": 0.0,
        "cost_per_1k_output": 0.0,
        "privacy": "local",
    },
}

_MODEL_ROLE_PREFERENCES: dict[str, list[str]] = {
    "planner": ["gpt-4o", "claude-sonnet-4-20250514", "gemini-2.5-pro"],
    "developer": ["claude-sonnet-4-20250514", "deepseek-chat", "gpt-4o", "gemini-2.5-pro"],
    "coding": ["claude-sonnet-4-20250514", "deepseek-chat", "gpt-4o"],
    "research": ["gpt-4o", "gemini-2.5-pro", "claude-sonnet-4-20250514"],
    "browser": ["gpt-4o-mini", "claude-haiku-3-5-20241022"],
    "writer": ["gpt-4o", "claude-sonnet-4-20250514", "deepseek-chat"],
    "qa": ["gpt-4o", "claude-sonnet-4-20250514"],
    "creative": ["gemini-2.5-pro", "gpt-4o", "claude-sonnet-4-20250514"],
    "data": ["gpt-4o", "deepseek-chat", "claude-sonnet-4-20250514"],
    "communication": ["gpt-4o-mini", "claude-haiku-3-5-20241022"],
    "review": ["gpt-4o", "claude-sonnet-4-20250514"],
    "file": ["gpt-4o-mini", "claude-haiku-3-5-20241022"],
    "coordinator": ["gpt-4o", "claude-sonnet-4-20250514"],
    "security": ["gpt-4o", "claude-sonnet-4-20250514"],
    "deployment": ["gpt-4o-mini", "claude-haiku-3-5-20241022"],
    "memory": ["gpt-4o-mini", "claude-haiku-3-5-20241022"],
}

_FALLBACK_CHAINS: dict[str, list[dict[str, str]]] = {
    "openai": [
        {"model": "gpt-4o-mini", "provider": "openai"},
        {"model": "claude-haiku-3-5-20241022", "provider": "anthropic"},
        {"model": "gemini-2.5-pro", "provider": "gemini"},
    ],
    "anthropic": [
        {"model": "claude-haiku-3-5-20241022", "provider": "anthropic"},
        {"model": "gpt-4o-mini", "provider": "openai"},
        {"model": "deepseek-chat", "provider": "deepseek"},
    ],
    "gemini": [
        {"model": "gpt-4o-mini", "provider": "openai"},
        {"model": "claude-haiku-3-5-20241022", "provider": "anthropic"},
    ],
    "deepseek": [
        {"model": "gpt-4o-mini", "provider": "openai"},
        {"model": "claude-haiku-3-5-20241022", "provider": "anthropic"},
    ],
}


class ModelRouter:
    def __init__(self):
        self._availability_cache: dict[str, bool] = {}
        self._model_capabilities = dict(_MODEL_CAPABILITIES)
        self._role_preferences = dict(_MODEL_ROLE_PREFERENCES)
        self._fallback_chains = dict(_FALLBACK_CHAINS)

    async def select_model(
        self,
        task_type: str = "general",
        tools: list[str] | None = None,
        requires_vision: bool = False,
        requires_audio: bool = False,
        requires_local: bool = False,
        max_cost: float | None = None,
        prefer_low_latency: bool = False,
    ) -> dict[str, str]:
        preferred_models = self._role_preferences.get(task_type, self._role_preferences.get("general", ["gpt-4o-mini"]))

        for model_name in preferred_models:
            caps = self._model_capabilities.get(model_name)
            if not caps:
                continue

            if requires_vision and not caps.get("vision"):
                continue
            if requires_audio and not caps.get("audio"):
                continue
            if requires_local and caps.get("privacy") != "local":
                continue
            if prefer_low_latency and caps.get("latency") == "high":
                continue
            if max_cost is not None:
                input_cost = caps.get("cost_per_1k_input", 0)
                output_cost = caps.get("cost_per_1k_output", 0)
                if (input_cost + output_cost) > max_cost:
                    continue

            return {
                "model": model_name,
                "provider": caps["provider"],
                "reasoning": caps.get("reasoning", "medium"),
                "context_window": caps.get("context", 8192),
                "cost_per_1k_input": caps.get("cost_per_1k_input", 0),
                "cost_per_1k_output": caps.get("cost_per_1k_output", 0),
            }

        return {"model": "gpt-4o-mini", "provider": "openai", "reasoning": "medium", "context_window": 128000}

    async def get_fallback(self, model: str, provider: str) -> dict[str, str] | None:
        chain = self._fallback_chains.get(provider, [])
        for fallback in chain:
            if fallback["model"] != model:
                return fallback
        return None

    def get_model_info(self, model_name: str) -> dict[str, Any] | None:
        return self._model_capabilities.get(model_name)

    def list_available_models(self) -> list[dict[str, Any]]:
        return [
            {"model": k, **v}
            for k, v in self._model_capabilities.items()
        ]

    def list_models_by_provider(self, provider: str) -> list[dict[str, Any]]:
        return [
            {"model": k, **v}
            for k, v in self._model_capabilities.items()
            if v.get("provider") == provider
        ]

    def add_model(self, name: str, capabilities: dict[str, Any]):
        self._model_capabilities[name] = capabilities

    def remove_model(self, name: str):
        self._model_capabilities.pop(name, None)
