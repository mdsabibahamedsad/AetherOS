"""AI provider connectors — OpenAI, Anthropic, Google, OpenRouter, Ollama, etc."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from connect.connectors import BaseConnector, ConnectorResult
from connect.models import (ServiceConnection, ConnectionStatus, HealthCheckResult,
                             ServiceCategory)


class OpenAIConnector(BaseConnector):
    service_id = "openai"
    service_name = "OpenAI"
    category = ServiceCategory.AI_PROVIDERS

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        key = (credentials or {}).get("api_key", "")
        if not key:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="API key required")
        try:
            import httpx
            base = connection.config.get("base_url", "https://api.openai.com/v1")
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"})
                if resp.status_code == 200:
                    data = resp.json()
                    models = len(data.get("data", []))
                    return ConnectorResult(message=f"Connected — {models} models available",
                                           data={"models": models})
                return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                       error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ConnectorResult(success=False, status=ConnectionStatus.ERROR, error=str(e))

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        return HealthCheckResult(service_id=self.service_id,
                                  connection_id=connection.id,
                                  status=connection.status,
                                  checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["models", "completions", "embeddings"],
                "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class AnthropicConnector(BaseConnector):
    service_id = "anthropic"
    service_name = "Anthropic"
    category = ServiceCategory.AI_PROVIDERS

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        key = (credentials or {}).get("api_key", "")
        if not key:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="API key required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.anthropic.com/v1/models",
                                         headers={"x-api-key": key,
                                                  "anthropic-version": "2023-06-01"})
                if resp.status_code == 200:
                    return ConnectorResult(message="Connected to Anthropic")
                return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                       error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ConnectorResult(success=False, status=ConnectionStatus.ERROR, error=str(e))

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        return HealthCheckResult(service_id=self.service_id,
                                  connection_id=connection.id,
                                  status=connection.status,
                                  checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["messages", "models"], "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class OpenRouterConnector(BaseConnector):
    service_id = "openrouter"
    service_name = "OpenRouter"
    category = ServiceCategory.AI_PROVIDERS

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        key = (credentials or {}).get("api_key", "")
        if not key:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="API key required")
        return ConnectorResult(message="Connected to OpenRouter")

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        return HealthCheckResult(service_id=self.service_id,
                                  connection_id=connection.id,
                                  status=connection.status,
                                  checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["chat", "models"], "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class OllamaConnector(BaseConnector):
    service_id = "ollama"
    service_name = "Ollama"
    category = ServiceCategory.AI_PROVIDERS

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        base = connection.config.get("base_url", "http://localhost:11434")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{base}/api/tags", timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return ConnectorResult(message=f"Connected — {len(models)} models: {', '.join(models[:3])}",
                                           data={"models": models})
                return ConnectorResult(success=False, status=ConnectionStatus.ERROR,
                                       error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ConnectorResult(success=False, status=ConnectionStatus.ERROR, error=str(e))

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        return HealthCheckResult(service_id=self.service_id,
                                  connection_id=connection.id,
                                  status=connection.status,
                                  checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["inference", "models"], "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class LMStudioConnector(BaseConnector):
    service_id = "lm_studio"
    service_name = "LM Studio"
    category = ServiceCategory.AI_PROVIDERS

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        base = connection.config.get("base_url", "http://localhost:1234/v1")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{base}/models", timeout=3)
                if resp.status_code == 200:
                    return ConnectorResult(message="Connected to LM Studio")
                return ConnectorResult(success=False, status=ConnectionStatus.ERROR,
                                       error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ConnectorResult(success=False, status=ConnectionStatus.ERROR, error=str(e))

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        return HealthCheckResult(service_id=self.service_id,
                                  connection_id=connection.id,
                                  status=connection.status,
                                  checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["inference"], "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class GenericAICompatConnector(BaseConnector):
    service_id = "openai_compat"
    service_name = "Custom OpenAI Compatible"
    category = ServiceCategory.AI_PROVIDERS

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        cfg = {**connection.config, **(credentials or {})}
        base = cfg.get("base_url", "")
        key = cfg.get("api_key", "")
        if not base:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Base URL required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {key}"} if key else {}
                resp = await client.get(f"{base}/models", headers=headers, timeout=5)
                if resp.status_code == 200:
                    return ConnectorResult(message=f"Connected to {base}")
                return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                       error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ConnectorResult(success=False, status=ConnectionStatus.ERROR, error=str(e))

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        return HealthCheckResult(service_id=self.service_id,
                                  connection_id=connection.id,
                                  status=connection.status,
                                  checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["completions"], "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


CONNECTOR_MAP = {
    "openai": OpenAIConnector,
    "anthropic": AnthropicConnector,
    "openrouter": OpenRouterConnector,
    "ollama": OllamaConnector,
    "lm_studio": LMStudioConnector,
    "openai_compat": GenericAICompatConnector,
}
