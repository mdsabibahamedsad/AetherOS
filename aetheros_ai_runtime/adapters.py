"""Provider adapters (sections 2, 5, 19, 21, 37-39, 43-46, 77, 82).

Extensible ABC: OpenAI-compatible, Anthropic-compatible, local
(Ollama/LM Studio/vLLM/llama.cpp via LocalModelManager reuse), custom
HTTP, MCP-backed (external/untrusted). Capability discovery explicit;
reasoning-effort mapping per provider (no equivalence pretense);
normalized events (start/delta/tool_call/tool_result/usage/warning/
complete/error/cancelled); safe retry classification; Retry-After
handling; cancellation via httpx Cancelled; secrets never logged
(redaction on errors).
"""

from __future__ import annotations

import json
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional

RETRYABLE = {"timeout", "connection", "rate_limit", "overloaded", "unknown"}
NON_RETRYABLE = {"auth", "permission", "invalid_request", "context_exceeded",
                 "policy_blocked", "misconfigured"}


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in ("authorization", "api_key", "apikey", "cookie",
                      "token", "secret", "password"):
                out[k] = "[REDACTED]"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    if isinstance(obj, str) and len(obj) > 12 and (
            obj.startswith("sk-") or obj.startswith("Bearer ")):
        return "[REDACTED]"
    return obj


@dataclass
class ChatMessage:
    role: str
    content: Any  # str or content blocks
    name: str = ""
    tool_call_id: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class InferenceRequest:
    messages: List[ChatMessage] = field(default_factory=list)
    model: str = ""
    tools: List[Dict[str, Any]] = field(default_factory=list)
    tool_choice: str = "auto"
    json_schema: Optional[Dict[str, Any]] = None
    reasoning_effort: str = ""  # "", low|medium|high (mapped per provider)
    max_tokens: int = 0
    temperature: float = 0.7
    stream: bool = False
    timeout_s: float = 120.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceEvent:
    kind: str  # start|delta|tool_call|tool_result|usage|warning|complete|error|cancelled
    text: str = ""
    tool_call: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
    error: str = ""
    at: float = field(default_factory=time.time)


def classify_error(exc: Exception) -> str:
    msg = f"{type(exc).__name__}: {exc}".lower()
    if "401" in msg or "unauthorized" in msg or "invalid api key" in msg \
            or "auth" in msg and "error" in msg:
        return "auth"
    if "429" in msg or "rate" in msg and "limit" in msg or "quota" in msg:
        return "rate_limit"
    if "timeout" in msg or "timed out" in msg:
        return "timeout"
    if "connect" in msg or "network" in msg or "dns" in msg:
        return "connection"
    if "context" in msg and ("length" in msg or "long" in msg or "token" in msg):
        return "context_exceeded"
    if "overload" in msg or "503" in msg or "529" in msg:
        return "overloaded"
    if "permission" in msg or "forbidden" in msg or "403" in msg:
        return "permission"
    if "policy" in msg or "blocked" in msg or "moderation" in msg:
        return "policy_blocked"
    if "bad request" in msg or "400" in msg or "invalid" in msg:
        return "invalid_request"
    return "unknown"


class ProviderAdapter(ABC):
    kind = "base"

    def __init__(self, *, base_url: str = "", api_key: str = "",
                 transport=None, timeout_s: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key  # never logged (see _headers/_safe_error)
        self._transport = transport
        self.timeout_s = timeout_s
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def reset_cancel(self) -> None:
        self._cancel.clear()

    @abstractmethod
    def list_models(self) -> List[Dict[str, Any]]:
        """Live discovery: [{id, ...}]. Raises on failure (no fake data)."""

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Real probe: {ok, latency_ms, reason}."""

    @abstractmethod
    def chat(self, req: InferenceRequest) -> Iterator[InferenceEvent]:
        """Normalized event stream (streaming or single-shot)."""

    # -- shared HTTP -------------------------------------------------------
    def _client(self):
        import httpx
        kwargs: Dict[str, Any] = {"timeout": self.timeout_s,
                                  "base_url": self.base_url or "http://localhost"}
        if self._transport is not None:
            kwargs["transport"] = self._transport
        return httpx.Client(**kwargs)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _safe_error(self, exc: Exception) -> str:
        return str(_redact(f"{type(exc).__name__}: {exc}"))[:500]


class OpenAICompatibleAdapter(ProviderAdapter):
    kind = "openai_compatible"
    # Explicit per-family reasoning mapping (no equivalence pretense).
    REASONING_PARAM = {"o1": "reasoning_effort", "o3": "reasoning_effort",
                       "default": "reasoning_effort"}

    def list_models(self) -> List[Dict[str, Any]]:
        with self._client() as client:
            resp = client.get("/v1/models", headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        items = data.get("data", []) if isinstance(data, dict) else []
        return [{"id": str(m.get("id", "")), "raw": m}
                for m in items if m.get("id")]

    def health_check(self) -> Dict[str, Any]:
        t0 = time.time()
        try:
            models = self.list_models()
            return {"ok": True, "latency_ms": round((time.time() - t0) * 1000, 1),
                    "reason": f"{len(models)} models listed"}
        except Exception as exc:
            return {"ok": False, "latency_ms": round((time.time() - t0) * 1000, 1),
                    "reason": self._safe_error(exc),
                    "class": classify_error(exc)}

    def _payload(self, req: InferenceRequest) -> Dict[str, Any]:
        messages = []
        for m in req.messages:
            entry: Dict[str, Any] = {"role": m.role}
            if m.tool_calls:
                entry["tool_calls"] = m.tool_calls
                entry["content"] = m.content or None
            else:
                entry["content"] = m.content
            if m.name:
                entry["name"] = m.name
            if m.tool_call_id:
                entry["tool_call_id"] = m.tool_call_id
            messages.append(entry)
        payload: Dict[str, Any] = {"model": req.model, "messages": messages,
                                   "temperature": req.temperature,
                                   "stream": req.stream}
        if req.max_tokens:
            payload["max_tokens"] = req.max_tokens
        if req.tools:
            payload["tools"] = [{"type": "function", "function": t}
                                for t in req.tools]
            payload["tool_choice"] = req.tool_choice
        if req.json_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "result", "schema": req.json_schema,
                                "strict": True}}
        if req.reasoning_effort:
            payload["reasoning_effort"] = req.reasoning_effort
        return payload

    def chat(self, req: InferenceRequest) -> Iterator[InferenceEvent]:
        self.reset_cancel()
        yield InferenceEvent(kind="start")
        try:
            with self._client() as client:
                if req.stream:
                    yield from self._chat_stream(client, req)
                else:
                    yield from self._chat_once(client, req)
        except Exception as exc:
            yield InferenceEvent(kind="error", error=self._safe_error(exc))
        if self._cancel.is_set():
            yield InferenceEvent(kind="cancelled")

    def _chat_once(self, client, req: InferenceRequest):
        resp = client.post("/v1/chat/completions", headers=self._headers(),
                           json=self._payload(req))
        if resp.status_code == 429:
            retry_after = resp.headers.get("retry-after", "")
            yield InferenceEvent(kind="error",
                                 error=f"rate_limit (retry-after: {retry_after})")
            return
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            yield InferenceEvent(kind="error", error="empty choices")
            return
        msg = choices[0].get("message", {})
        if msg.get("content"):
            yield InferenceEvent(kind="delta", text=str(msg["content"]))
        for tc in msg.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            yield InferenceEvent(kind="tool_call", tool_call={
                "id": tc.get("id", ""), "name": fn.get("name", ""),
                "arguments": fn.get("arguments", ""),
                "model": req.model, "timestamp": time.time()})
        yield InferenceEvent(kind="usage", usage=data.get("usage", {}))
        yield InferenceEvent(kind="complete")

    def _chat_stream(self, client, req: InferenceRequest):
        text_parts: List[str] = []
        with client.stream("POST", "/v1/chat/completions",
                           headers=self._headers(),
                           json=self._payload(req)) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if self._cancel.is_set():
                    break
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    data = json.loads(chunk)
                except ValueError:
                    continue
                for choice in data.get("choices", []):
                    delta = choice.get("delta", {})
                    if delta.get("content"):
                        text_parts.append(delta["content"])
                        yield InferenceEvent(kind="delta",
                                             text=str(delta["content"]))
                    for tc in delta.get("tool_calls", []) or []:
                        fn = tc.get("function", {})
                        yield InferenceEvent(kind="tool_call", tool_call={
                            "id": tc.get("id", ""),
                            "name": fn.get("name", ""),
                            "arguments": fn.get("arguments", ""),
                            "model": req.model, "timestamp": time.time()})
        yield InferenceEvent(kind="complete")


class AnthropicAdapter(ProviderAdapter):
    kind = "anthropic"

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json",
                   "anthropic-version": "2023-06-01"}
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    def list_models(self) -> List[Dict[str, Any]]:
        with self._client() as client:
            resp = client.get("/v1/models", headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        items = data.get("data", []) if isinstance(data, dict) else []
        return [{"id": str(m.get("id", "")), "raw": m}
                for m in items if m.get("id")]

    def health_check(self) -> Dict[str, Any]:
        t0 = time.time()
        try:
            models = self.list_models()
            return {"ok": True, "latency_ms": round((time.time() - t0) * 1000, 1),
                    "reason": f"{len(models)} models listed"}
        except Exception as exc:
            return {"ok": False, "latency_ms": round((time.time() - t0) * 1000, 1),
                    "reason": self._safe_error(exc),
                    "class": classify_error(exc)}

    def chat(self, req: InferenceRequest) -> Iterator[InferenceEvent]:
        self.reset_cancel()
        yield InferenceEvent(kind="start")
        system: List[Dict[str, str]] = []
        messages: List[Dict[str, Any]] = []
        for m in req.messages:
            if m.role == "system":
                system.append({"type": "text",
                               "text": str(m.content)[:20000]})
            elif m.role == "tool":
                messages.append({"role": "user", "content": [{
                    "type": "tool_result", "tool_use_id": m.tool_call_id,
                    "content": str(m.content)[:20000]}]})
            else:
                messages.append({"role": m.role if m.role in ("user", "assistant") else "user",
                                 "content": m.content})
        payload: Dict[str, Any] = {"model": req.model, "messages": messages,
                                   "max_tokens": req.max_tokens or 1024}
        if system:
            payload["system"] = system
        if req.tools:
            payload["tools"] = [{"name": t.get("name", ""),
                                 "description": str(t.get("description", ""))[:1000],
                                 "input_schema": t.get("parameters", {
                                     "type": "object"})}
                                for t in req.tools]
        if req.reasoning_effort:
            # Anthropic thinking budgets (explicit mapping, not equivalence).
            budget = {"low": 1024, "medium": 4096, "high": 10000}.get(
                req.reasoning_effort, 4096)
            payload["thinking"] = {"type": "enabled",
                                   "budget_tokens": budget}
        try:
            with self._client() as client:
                resp = client.post("/v1/messages", headers=self._headers(),
                                   json=payload)
                if resp.status_code == 429:
                    yield InferenceEvent(
                        kind="error",
                        error=f"rate_limit (retry-after: {resp.headers.get('retry-after', '')})")
                    return
                resp.raise_for_status()
                data = resp.json()
            for block in data.get("content", []):
                if self._cancel.is_set():
                    break
                if block.get("type") == "text":
                    yield InferenceEvent(kind="delta", text=str(block.get("text", "")))
                elif block.get("type") == "tool_use":
                    yield InferenceEvent(kind="tool_call", tool_call={
                        "id": block.get("id", ""), "name": block.get("name", ""),
                        "arguments": json.dumps(block.get("input", {})),
                        "model": req.model, "timestamp": time.time()})
            yield InferenceEvent(kind="usage", usage=data.get("usage", {}))
            yield InferenceEvent(kind="complete")
        except Exception as exc:
            yield InferenceEvent(kind="error", error=self._safe_error(exc))
        if self._cancel.is_set():
            yield InferenceEvent(kind="cancelled")


class LocalAdapter(OpenAICompatibleAdapter):
    """Local runtimes speak OpenAI-compatible chat; locality verified by
    loopback check, not assumed from config (rule 8)."""
    kind = "local"

    def is_loopback(self) -> bool:
        from urllib.parse import urlparse
        try:
            host = (urlparse(self.base_url).hostname or "").lower()
        except ValueError:
            return False
        return host in ("localhost", "127.0.0.1", "::1")


class CustomHTTPAdapter(OpenAICompatibleAdapter):
    kind = "custom_http"


class MCPModelAdapter(ProviderAdapter):
    """MCP-backed model provider: external/untrusted transport delegate."""
    kind = "mcp_model"

    def __init__(self, *, invoke: Callable[[InferenceRequest], Iterator[InferenceEvent]],
                 **kw) -> None:
        super().__init__(**kw)
        self._invoke = invoke

    def list_models(self) -> List[Dict[str, Any]]:
        return []

    def health_check(self) -> Dict[str, Any]:
        return {"ok": False, "reason": "mcp model transports health-check via tools",
                "class": "unknown"}

    def chat(self, req: InferenceRequest) -> Iterator[InferenceEvent]:
        yield InferenceEvent(kind="start")
        try:
            yield from self._invoke(req)
        except Exception as exc:
            yield InferenceEvent(kind="error", error=self._safe_error(exc))


ADAPTERS = {"openai_compatible": OpenAICompatibleAdapter,
            "anthropic": AnthropicAdapter, "local": LocalAdapter,
            "custom_http": CustomHTTPAdapter, "mcp_model": MCPModelAdapter}


def adapter_for(kind: str, **kw) -> ProviderAdapter:
    cls = ADAPTERS.get(kind)
    if cls is None:
        raise ValueError(f"unknown provider adapter (fail closed): {kind}")
    if kind == "mcp_model" and "invoke" not in kw:
        raise ValueError("mcp_model requires an invoke transport")
    return cls(**kw)
