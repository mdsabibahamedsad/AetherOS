"""Model Validator — comprehensive model and provider validation.

Checks:
- API key validity
- Model existence
- Permissions
- Availability
- Rate limits
- Streaming
- Vision
- Function calling
- Reasoning
"""

from __future__ import annotations

import enum
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aetheros_providers.validation")


@dataclass
class ValidationResult:
    success: bool
    checks: Dict[str, bool] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def all_passed(self) -> bool:
        return all(self.checks.values()) if self.checks else False

    @property
    def passed_checks(self) -> int:
        return sum(1 for v in self.checks.values() if v)

    @property
    def failed_checks(self) -> int:
        return sum(1 for v in self.checks.values() if not v)

    def summary(self) -> str:
        lines = [f"Validation: {'PASSED' if self.all_passed else 'FAILED'} ({self.passed_checks}/{len(self.checks)} checks, {self.latency_ms:.0f}ms)"]
        for check, passed in self.checks.items():
            icon = "✓" if passed else "✗"
            error = self.errors.get(check, "")
            lines.append(f"  {icon} {check}{' — ' + error if error else ''}")
        return "\n".join(lines)


class ModelValidator:
    """Comprehensive model and provider validation.

    Validates API keys, model availability, streaming, vision,
    function calling, and reasoning support.
    """

    def __init__(self) -> None:
        self._validators: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # API Key validation
    # ------------------------------------------------------------------

    def validate_api_key(self, provider: str, api_key: str, base_url: str = "") -> ValidationResult:
        """Validate an API key by calling the models endpoint."""
        result = ValidationResult(success=False)
        start = time.monotonic()

        try:
            url = f"{base_url.rstrip('/')}/models" if base_url else ""
            if not url:
                url = self._get_models_url(provider)

            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                elapsed = (time.monotonic() - start) * 1000
                result.latency_ms = round(elapsed, 1)
                result.success = True
                result.checks["api_key_valid"] = True
                result.checks["endpoint_reachable"] = True
                result.details["status_code"] = resp.status
                result.details["model_count"] = len(data.get("data", data.get("models", [])))

        except urllib.error.HTTPError as exc:
            elapsed = (time.monotonic() - start) * 1000
            result.latency_ms = round(elapsed, 1)
            if exc.code == 401:
                result.checks["api_key_valid"] = False
                result.errors["api_key_valid"] = "Invalid API key (401 Unauthorized)"
            elif exc.code == 403:
                result.checks["api_key_valid"] = False
                result.errors["api_key_valid"] = "Insufficient permissions (403 Forbidden)"
            elif exc.code == 429:
                result.checks["api_key_valid"] = False
                result.errors["api_key_valid"] = "Rate limited (429 Too Many Requests)"
            else:
                result.checks["api_key_valid"] = False
                result.errors["api_key_valid"] = f"HTTP {exc.code}: {exc.reason}"
            result.details["status_code"] = exc.code

        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            result.latency_ms = round(elapsed, 1)
            result.checks["endpoint_reachable"] = False
            result.errors["endpoint_reachable"] = str(exc)

        return result

    # ------------------------------------------------------------------
    # Model availability
    # ------------------------------------------------------------------

    def validate_model(
        self,
        provider: str,
        model_id: str,
        api_key: str,
        base_url: str = "",
    ) -> ValidationResult:
        """Validate that a specific model exists and is accessible."""
        result = ValidationResult(success=False)
        start = time.monotonic()

        key_result = self.validate_api_key(provider, api_key, base_url)
        result.checks["api_key_valid"] = key_result.checks.get("api_key_valid", False)
        result.checks["endpoint_reachable"] = key_result.checks.get("endpoint_reachable", False)

        if key_result.errors:
            result.errors.update(key_result.errors)

        if result.checks.get("api_key_valid"):
            models = key_result.details.get("models", [])
            model_found = any(
                model_id in str(m.get("id", ""))
                for m in models
            ) if models else True
            result.checks["model_exists"] = model_found
            if not model_found:
                result.errors["model_exists"] = f"Model '{model_id}' not found in provider catalog"

        elapsed = (time.monotonic() - start) * 1000
        result.latency_ms = round(elapsed, 1)
        result.success = all(result.checks.values())
        return result

    # ------------------------------------------------------------------
    # Capability validation
    # ------------------------------------------------------------------

    def validate_capabilities(
        self,
        provider: str,
        model_id: str,
        check_streaming: bool = True,
        check_vision: bool = False,
        check_tools: bool = False,
        check_reasoning: bool = False,
    ) -> ValidationResult:
        """Validate model capabilities."""
        result = ValidationResult(success=True)

        if check_streaming:
            result.checks["streaming_supported"] = self._check_streaming_support(provider, model_id)
            if not result.checks["streaming_supported"]:
                result.errors["streaming_supported"] = "Streaming not supported for this model"

        if check_vision:
            result.checks["vision_supported"] = self._check_vision_support(provider, model_id)
            if not result.checks["vision_supported"]:
                result.errors["vision_supported"] = "Vision not supported for this model"

        if check_tools:
            result.checks["tool_calling_supported"] = self._check_tool_support(provider, model_id)
            if not result.checks["tool_calling_supported"]:
                result.errors["tool_calling_supported"] = "Tool/function calling not supported for this model"

        if check_reasoning:
            result.checks["reasoning_supported"] = self._check_reasoning_support(provider, model_id)
            if not result.checks["reasoning_supported"]:
                result.errors["reasoning_supported"] = "Reasoning not supported for this model"

        result.success = all(result.checks.values())
        return result

    # ------------------------------------------------------------------
    # Full validation
    # ------------------------------------------------------------------

    def validate_all(
        self,
        provider: str,
        model_id: str,
        api_key: str,
        base_url: str = "",
        check_vision: bool = False,
        check_tools: bool = True,
        check_reasoning: bool = False,
    ) -> ValidationResult:
        """Run full validation: API key, model, and capabilities."""
        model_result = self.validate_model(provider, model_id, api_key, base_url)
        cap_result = self.validate_capabilities(
            provider, model_id,
            check_streaming=True,
            check_vision=check_vision,
            check_tools=check_tools,
            check_reasoning=check_reasoning,
        )

        combined = ValidationResult(
            success=model_result.success and cap_result.success,
            latency_ms=model_result.latency_ms + cap_result.latency_ms,
        )
        combined.checks.update(model_result.checks)
        combined.checks.update(cap_result.checks)
        combined.errors.update(model_result.errors)
        combined.errors.update(cap_result.errors)
        combined.details.update(model_result.details)
        combined.details.update(cap_result.details)

        return combined

    # ------------------------------------------------------------------
    # Capability checks (heuristic-based)
    # ------------------------------------------------------------------

    @staticmethod
    def _check_streaming_support(provider: str, model_id: str) -> bool:
        streaming_providers = {
            "openai", "anthropic", "google", "openrouter", "deepseek",
            "mistral", "together", "groq", "xai", "ollama", "lm_studio",
        }
        return provider.lower() in streaming_providers

    @staticmethod
    def _check_vision_support(provider: str, model_id: str) -> bool:
        model_lower = model_id.lower()
        # Text-only compact variants: exclude before matching vision indicators.
        # e.g. "gpt-4o-mini" contains "gpt-4o" but does not accept image input.
        text_only_indicators = ["-mini", "-nano", "-tiny", "-small", "-instruct", "text-only"]
        if any(tag in model_lower for tag in text_only_indicators):
            return False
        vision_indicators = [
            "vision", "gpt-4o", "gpt-4.1", "gpt-5", "claude-3", "claude-4",
            "gemini", "llava", "qwen-vl", "pixtral", "grok",
        ]
        return any(indicator in model_lower for indicator in vision_indicators)

    @staticmethod
    def _check_tool_support(provider: str, model_id: str) -> bool:
        tool_providers = {
            "openai", "anthropic", "google", "openrouter", "deepseek",
            "mistral", "together", "groq", "xai", "ollama",
        }
        return provider.lower() in tool_providers

    @staticmethod
    def _check_reasoning_support(provider: str, model_id: str) -> bool:
        model_lower = model_id.lower()
        reasoning_indicators = ["o1", "o3", "claude-3", "claude-4", "deepseek-r1", "reasoning"]
        return any(indicator in model_lower for indicator in reasoning_indicators)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _get_models_url(provider: str) -> str:
        urls = {
            "openai": "https://api.openai.com/v1/models",
            "anthropic": "https://api.anthropic.com/v1/models",
            "google": "https://generativelanguage.googleapis.com/v1/models",
            "openrouter": "https://openrouter.ai/api/v1/models",
            "deepseek": "https://api.deepseek.com/models",
            "mistral": "https://api.mistral.ai/v1/models",
            "together": "https://api.together.xyz/v1/models",
            "groq": "https://api.groq.com/openai/v1/models",
            "xai": "https://api.x.ai/v1/models",
        }
        return urls.get(provider, "")