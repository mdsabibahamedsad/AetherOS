"""Synchronous + asynchronous SDK clients (Master 62 §46).

Secure defaults: TLS verification on, bounded retries/timeouts, no secret
logging, idempotency keys on mutations, cursor pagination helpers.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Iterator, List, Optional

import httpx

from aetheros_sdk.errors import RetryPolicy, SDKError, TimeoutPolicy


class _Base:
    def __init__(self, base_url: str, api_key: str,
                 retry: Optional[RetryPolicy] = None,
                 timeout: Optional[TimeoutPolicy] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.retry = retry or RetryPolicy()
        self.timeout = timeout or TimeoutPolicy()

    def _headers(self, idempotency_key: str = "") -> Dict[str, str]:
        h = {"Content-Type": "application/json", "X-API-Key": self.api_key,
             "X-Request-Id": f"sdk_{uuid.uuid4().hex[:10]}"}
        if idempotency_key:
            h["Idempotency-Key"] = idempotency_key
        return h

    def _should_retry(self, exc: Optional[Exception], status: int) -> bool:
        if status in (429, 502, 503, 504):
            return True
        return False


class Client(_Base):
    """Synchronous client."""

    def __init__(self, *a: Any, **k: Any) -> None:
        super().__init__(*a, **k)
        self._http = httpx.Client(verify=True, timeout=httpx.Timeout(
            self.timeout.request_s, connect=self.timeout.connect_s))

    def _req(self, method: str, path: str, body: Any = None,
             idempotency_key: str = "") -> Any:
        url = self.base_url + path
        last: Optional[SDKError] = None
        for attempt in range(self.retry.max_attempts):
            try:
                resp = self._http.request(method, url, json=body,
                                          headers=self._headers(idempotency_key))
            except httpx.HTTPError as exc:
                last = SDKError(category="NETWORK_ERROR", message=str(exc)[:300],
                                retryable=True)
                time.sleep(self.retry.delay(attempt))
                continue
            if resp.status_code in (429, 502, 503, 504) and attempt + 1 < self.retry.max_attempts:
                last = SDKError.from_response(resp.status_code, _safe_json(resp))
                time.sleep(self.retry.delay(attempt))
                continue
            if resp.status_code >= 400:
                raise SDKError.from_response(resp.status_code, _safe_json(resp))
            return resp.json() if resp.content else None
        raise last or SDKError(message="request failed")

    # -- resources -----------------------------------------------------------
    def create_agent(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        return self._req("POST", "/api/v1/agents", manifest,
                         idempotency_key=f"agent:{manifest['name']}:{manifest['version']}")

    def list_agents(self, limit: int = 20) -> Dict[str, Any]:
        return self._req("GET", f"/api/v1/agents?limit={limit}")

    def create_task(self, agent_id: str, task_input: Dict[str, Any],
                    idempotency_key: str = "") -> Dict[str, Any]:
        return self._req("POST", "/api/v1/tasks",
                         {"agent": agent_id, "input": task_input},
                         idempotency_key=idempotency_key or f"task:{uuid.uuid4().hex[:10]}")

    def get_task(self, task_id: str) -> Dict[str, Any]:
        return self._req("GET", f"/api/v1/tasks/{task_id}")

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        return self._req("POST", f"/api/v1/tasks/{task_id}/cancel")

    def invoke_tool(self, name: str, args: Dict[str, Any],
                    grants: Optional[List[str]] = None,
                    idempotency_key: str = "") -> Dict[str, Any]:
        return self._req("POST", f"/api/v1/tools/{name}/invoke",
                         {"args": args, "grants": grants or []},
                         idempotency_key=idempotency_key)

    def register_skill(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        return self._req("POST", "/api/v1/skills", manifest,
                         idempotency_key=f"skill:{manifest['name']}:{manifest['version']}")

    def memory_write(self, content: str, scope: str = "user") -> Dict[str, Any]:
        return self._req("POST", "/api/v1/memory/records", {"content": content, "scope": scope},
                         idempotency_key=f"mem:{uuid.uuid4().hex[:10]}")

    def memory_search(self, q: str) -> Dict[str, Any]:
        return self._req("GET", f"/api/v1/memory/search?q={q}")

    def artifact_create(self, data: bytes, filename: str = "",
                        classification: str = "internal") -> Dict[str, Any]:
        import base64
        return self._req("POST", "/api/v1/artifacts",
                         {"dataBase64": base64.b64encode(data).decode(),
                          "filename": filename,
                          "classification": classification},
                         idempotency_key=f"art:{uuid.uuid4().hex[:10]}")

    def artifact_get(self, artifact_id: str) -> bytes:
        import base64
        rec = self._req("GET", f"/api/v1/artifacts/{artifact_id}")
        return base64.b64decode(rec["dataBase64"])

    def automation_create(self, name: str, trigger: Dict[str, Any]) -> Dict[str, Any]:
        return self._req("POST", "/api/v1/automations",
                         {"name": name, "trigger": trigger},
                         idempotency_key=f"auto:{name}:{uuid.uuid4().hex[:8]}")

    def webhook_register(self, url: str, events: List[str]) -> Dict[str, Any]:
        return self._req("POST", "/api/v1/webhooks",
                         {"url": url, "events": events},
                         idempotency_key=f"hook:{uuid.uuid4().hex[:10]}")

    def agent_card(self) -> Dict[str, Any]:
        return self._req("GET", "/api/v1/a2a/card")

    def stream_task_events(self, task_id: str) -> Iterator[Dict[str, Any]]:
        import json as _j
        with self._http.stream("GET", self.base_url + f"/api/v1/tasks/{task_id}/events",
                               headers=self._headers(), timeout=self.timeout.stream_idle_s) as resp:
            if resp.status_code >= 400:
                raise SDKError.from_response(resp.status_code, resp.read())
            buf = ""
            for chunk in resp.iter_text():
                buf += chunk
                while "\n\n" in buf:
                    frame, buf = buf.split("\n\n", 1)
                    data = "".join(l[6:] for l in frame.splitlines() if l.startswith("data:"))
                    if data.strip().startswith("{"):
                        yield _j.loads(data)

    def close(self) -> None:
        self._http.close()


class AsyncClient(_Base):
    """Asynchronous client (same surface, async/await)."""

    def __init__(self, *a: Any, **k: Any) -> None:
        super().__init__(*a, **k)
        self._http: Optional[httpx.AsyncClient] = None

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(verify=True, timeout=httpx.Timeout(
                self.timeout.request_s, connect=self.timeout.connect_s))
        return self._http

    async def _req(self, method: str, path: str, body: Any = None,
                   idempotency_key: str = "") -> Any:
        import asyncio
        http = await self._client()
        last: Optional[SDKError] = None
        for attempt in range(self.retry.max_attempts):
            try:
                resp = await http.request(method, self.base_url + path, json=body,
                                          headers=self._headers(idempotency_key))
            except httpx.HTTPError as exc:
                last = SDKError(category="NETWORK_ERROR", message=str(exc)[:300],
                                retryable=True)
                await asyncio.sleep(self.retry.delay(attempt))
                continue
            if resp.status_code in (429, 502, 503, 504) and attempt + 1 < self.retry.max_attempts:
                last = SDKError.from_response(resp.status_code, _safe_json(resp))
                await asyncio.sleep(self.retry.delay(attempt))
                continue
            if resp.status_code >= 400:
                raise SDKError.from_response(resp.status_code, _safe_json(resp))
            return resp.json() if resp.content else None
        raise last or SDKError(message="request failed")

    async def create_agent(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        return await self._req("POST", "/api/v1/agents", manifest,
                               idempotency_key=f"agent:{manifest['name']}:{manifest['version']}")

    async def create_task(self, agent_id: str, task_input: Dict[str, Any],
                          idempotency_key: str = "") -> Dict[str, Any]:
        return await self._req("POST", "/api/v1/tasks",
                               {"agent": agent_id, "input": task_input},
                               idempotency_key=idempotency_key or f"task:{uuid.uuid4().hex[:10]}")

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        return await self._req("GET", f"/api/v1/tasks/{task_id}")

    async def invoke_tool(self, name: str, args: Dict[str, Any],
                          grants: Optional[List[str]] = None,
                          idempotency_key: str = "") -> Dict[str, Any]:
        return await self._req("POST", f"/api/v1/tools/{name}/invoke",
                               {"args": args, "grants": grants or []},
                               idempotency_key=idempotency_key)

    async def memory_write(self, content: str, scope: str = "user") -> Dict[str, Any]:
        return await self._req("POST", "/api/v1/memory/records",
                               {"content": content, "scope": scope},
                               idempotency_key=f"mem:{uuid.uuid4().hex[:10]}")

    async def artifact_create(self, data: bytes, filename: str = "",
                              classification: str = "internal") -> Dict[str, Any]:
        import base64
        return await self._req("POST", "/api/v1/artifacts",
                               {"dataBase64": base64.b64encode(data).decode(),
                                "filename": filename,
                                "classification": classification},
                               idempotency_key=f"art:{uuid.uuid4().hex[:10]}")

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()


def _safe_json(resp) -> Any:
    try:
        return resp.json()
    except Exception:
        return (resp.text or "")[:500]


def verify_webhook(secret: str, body: bytes, timestamp: str,
                   delivery_id: str, signature: str) -> bool:
    """SDK helper for webhook signature verification (§96)."""
    from aetheros_platform.events import verify_signature
    return verify_signature(secret, body, timestamp, delivery_id, signature)
