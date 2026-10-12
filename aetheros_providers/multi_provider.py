"""Multi-Provider Orchestrator — route different tasks to different providers.

Supports assigning different providers to different workflow stages:
- Planner → Claude
- Coder → GPT-5
- Vision → Gemini
- Browser → OpenRouter
- Summarizer → Groq

Also supports using multiple providers inside one conversation.
"""

from __future__ import annotations

import enum
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import httpx

from providers import get_provider_profile

logger = logging.getLogger("aetheros_providers.multi")


@dataclass
class WorkflowStage:
    name: str
    provider: str
    model: str
    settings: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 120
    max_retries: int = 2

    @property
    def key(self) -> str:
        return f"{self.provider}/{self.model}"


class MultiProviderOrchestrator:
    """Orchestrates multiple providers across workflow stages.

    Each workflow stage can use a different provider/model.
    Supports parallel execution and result aggregation.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stages: Dict[str, WorkflowStage] = {}
        self._default_stages: Dict[str, WorkflowStage] = {
            "planner": WorkflowStage("Planner", "anthropic", "claude-sonnet-4"),
            "coder": WorkflowStage("Coder", "openai", "gpt-4o"),
            "vision": WorkflowStage("Vision", "google", "gemini-2.0-flash"),
            "browser": WorkflowStage("Browser", "openrouter", "gpt-4o"),
            "summarizer": WorkflowStage("Summarizer", "groq", "llama-3.3-70b"),
            "researcher": WorkflowStage("Researcher", "openai", "gpt-4o"),
            "reviewer": WorkflowStage("Reviewer", "anthropic", "claude-sonnet-4"),
            "compression": WorkflowStage("Compression", "openai", "gpt-4o-mini"),
        }
        self._stages.update(self._default_stages)

    # ------------------------------------------------------------------
    # Stage management
    # ------------------------------------------------------------------

    def define_stage(self, name: str, provider: str, model: str, **settings) -> WorkflowStage:
        with self._lock:
            stage = WorkflowStage(
                name=name,
                provider=provider,
                model=model,
                settings=settings,
            )
            self._stages[name] = stage
            return stage

    def get_stage(self, name: str) -> Optional[WorkflowStage]:
        with self._lock:
            return self._stages.get(name)

    def remove_stage(self, name: str) -> bool:
        with self._lock:
            if name in self._stages and name not in self._default_stages:
                del self._stages[name]
                return True
            return False

    def list_stages(self) -> Dict[str, WorkflowStage]:
        with self._lock:
            return dict(self._stages)

    def reset_to_defaults(self) -> None:
        with self._lock:
            self._stages.clear()
            self._stages.update(self._default_stages)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def call_provider(self, provider: str, model: str, params: Dict[str, Any]) -> Any:
        """Make a call to a specific provider/model combination.

        Args:
            provider: Provider name.
            model: Model name.
            params: Call parameters (messages, temperature, etc.).

        Returns:
            The provider response.
        """
        messages = params.get("messages", [])
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 4096)
        stream = params.get("stream", False)

        try:
            profile = get_provider_profile(provider)
            if profile is None:
                return {"error": f"Provider '{provider}' not found", "success": False}

            base_url = profile.base_url
            api_key = self._resolve_api_key(provider)

            if not api_key:
                return {"error": f"No API key configured for {provider}", "success": False}

            url = f"{base_url.rstrip('/')}/v1/chat/completions"
            body = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
            }

            with httpx.Client(timeout=120) as client:
                response = client.post(
                    url,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                return response.json()

        except ImportError:
            return {"error": "httpx not available", "success": False}
        except Exception as exc:
            logger.error("Provider call failed: %s/%s - %s", provider, model, exc)
            return {"error": str(exc), "success": False}

    def execute_stage(self, stage_name: str, messages: List[Dict[str, Any]], **overrides) -> Any:
        """Execute a specific workflow stage with the given messages."""
        stage = self.get_stage(stage_name)
        if stage is None:
            return {"error": f"Stage '{stage_name}' not defined", "success": False}

        params = {
            "messages": messages,
            "temperature": overrides.get("temperature", stage.settings.get("temperature", 0.7)),
            "max_tokens": overrides.get("max_tokens", stage.settings.get("max_tokens", 4096)),
            "stream": overrides.get("stream", False),
        }

        return self.call_provider(stage.provider, stage.model, params)

    def execute_pipeline(self, stages: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a pipeline of stages sequentially, passing context between them."""
        results = {}
        current_context = dict(context)

        for stage_name in stages:
            messages = current_context.get("messages", [])
            result = self.execute_stage(stage_name, messages)
            results[stage_name] = result
            current_context["last_result"] = result

            if "output" in result:
                current_context.setdefault("all_outputs", {})[stage_name] = result["output"]

        return results

    # ------------------------------------------------------------------
    # Multi-provider conversation
    # ------------------------------------------------------------------

    def multi_provider_chat(
        self,
        stages: List[str],
        user_message: str,
        system_message: str = "",
    ) -> Dict[str, Any]:
        """Chat using multiple providers in sequence.

        Each provider sees the previous provider's response.
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_message})

        results = {}
        for stage_name in stages:
            result = self.execute_stage(stage_name, messages)
            results[stage_name] = result
            if result.get("success", False):
                choice = result.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": f"[This was the response from {stage_name}. Continue the workflow.]",
                })

        return results

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def _resolve_api_key(self, provider: str) -> Optional[str]:
        env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "cohere": "COHERE_API_KEY",
            "together": "TOGETHER_API_KEY",
            "groq": "GROQ_API_KEY",
            "xai": "XAI_API_KEY",
        }
        env_var = env_map.get(provider.lower(), f"{provider.upper()}_API_KEY")
        return os.environ.get(env_var)

    def summary(self) -> str:
        lines = ["Multi-Provider Orchestrator:"]
        for name, stage in self._stages.items():
            lines.append(f"  {name:15s} → {stage.provider:15s} / {stage.model}")
        return "\n".join(lines)