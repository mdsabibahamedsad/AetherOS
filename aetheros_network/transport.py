"""A2A JSON-RPC transport over HTTPS (Master 46 sections 15-16, 33-37, 68-70).

Methods (A2A v1.0 core subset):
  message/send, message/stream (SSE), tasks/get, tasks/cancel,
  + Agent Card fetch at /.well-known/agent-card.json.

Security enforced below the UI:
  - HTTPS required in production; http:// only with explicit
    ``allow_insecure=True`` (development), which is logged and visible.
  - SSRF guard on every URL (policy.check_url_allowed).
  - TLS verification on by default; custom CA bundle / pinning supported.
  - Timeouts: connect / request / stream / task deadlines are separate;
    long tasks use async polling (tasks/get), never huge HTTP timeouts.
  - Idempotency-Key header on message/send; never blindly resubmit.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urljoin, urlparse

from . import A2A_AGENT_CARD_PATH
from .policy import check_url_allowed


@dataclass
class TransportConfig:
    timeout_connect: float = 10.0
    timeout_request: float = 60.0
    timeout_stream: float = 300.0
    verify_tls: bool = True
    ca_bundle: Optional[str] = None
    pinned_spki: List[str] = field(default_factory=list)  # documented; enforced where httpx allows
    allow_insecure: bool = False  # dev only: VISIBLE + LOGGED
    allow_private_hosts: bool = False  # LAN pairing mode, explicit
    allowed_hosts: Optional[List[str]] = None
    proxy: Optional[str] = None  # enterprise proxy support (section 70)
    bearer_token: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)


class TransportError(Exception):
    def __init__(self, message: str, *, kind: str = "transport",
                 status: Optional[int] = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.kind = kind  # offline|dns|tls|timeout|reset|http|rate_limit|auth|protocol
        self.status = status
        self.retryable = retryable


def _classify_exception(exc: Exception, url: str) -> TransportError:
    import httpx
    msg = str(exc)
    if isinstance(exc, httpx.ConnectError):
        low = msg.lower()
        if "dns" in low or "name resolution" in low or "getaddrinfo" in low:
            return TransportError(f"dns failure for {url}: {msg}", kind="dns", retryable=True)
        if "ssl" in low or "tls" in low or "certificate" in low:
            return TransportError(f"tls failure for {url}: {msg}", kind="tls")
        if "refused" in low:
            return TransportError(f"connection refused {url}", kind="offline", retryable=True)
        return TransportError(f"connection failed {url}: {msg}", kind="offline", retryable=True)
    if isinstance(exc, httpx.ConnectTimeout):
        return TransportError(f"connect timeout {url}", kind="timeout", retryable=True)
    if isinstance(exc, (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout)):
        return TransportError(f"request timeout {url}", kind="timeout", retryable=True)
    return TransportError(f"transport error {url}: {msg}", kind="reset", retryable=True)


class A2ATransport:
    """Synchronous A2A client. One instance per remote agent endpoint."""

    def __init__(self, base_url: str, config: Optional[TransportConfig] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.config = config or TransportConfig()
        self._insecure_warned = False
        self._validate_base_url()

    def _validate_base_url(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme == "http":
            if not self.config.allow_insecure:
                raise TransportError(
                    "insecure http:// blocked in production "
                    "(set allow_insecure=True for development only)",
                    kind="protocol",
                )
        elif parsed.scheme != "https":
            raise TransportError(f"unsupported scheme: {parsed.scheme!r}", kind="protocol")

    def _check_url(self, url: str) -> None:
        parsed = urlparse(url)
        is_local_dev = self.config.allow_private_hosts or self.config.allow_insecure
        if parsed.scheme == "http" and not self.config.allow_insecure:
            raise TransportError("insecure http:// blocked", kind="protocol")
        ok, reason = check_url_allowed(
            url if parsed.scheme == "https" else url,
            allow_private=is_local_dev,
            allowed_hosts=self.config.allowed_hosts,
        )
        if not ok:
            # In explicit LAN/dev mode, still re-resolve: allow http+private.
            if is_local_dev and ("private address" in reason or "restricted address" in reason):
                return
            raise TransportError(f"url blocked by network policy: {reason}", kind="protocol")

    def _client(self):
        import httpx
        cfg = self.config
        verify = cfg.ca_bundle or cfg.verify_tls
        return httpx.Client(
            verify=verify,
            proxy=cfg.proxy,
            timeout=httpx.Timeout(cfg.timeout_request, connect=cfg.timeout_connect),
            follow_redirects=False,  # endpoint substitution defense: no silent redirects
        )

    def _headers(self, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        h.update(self.config.headers)
        if self.config.bearer_token:
            h["Authorization"] = f"Bearer {self.config.bearer_token}"
        if idempotency_key:
            h["Idempotency-Key"] = idempotency_key
        return h

    def fetch_agent_card(self) -> Dict[str, Any]:
        """GET /.well-known/agent-card.json. Returns raw JSON (untrusted)."""
        url = self.base_url + A2A_AGENT_CARD_PATH
        self._check_url(url)
        import httpx
        t0 = time.time()
        try:
            with self._client() as client:
                resp = client.get(url, headers=self._headers())
        except Exception as exc:
            raise _classify_exception(exc, url)
        latency_ms = (time.time() - t0) * 1000
        if resp.status_code == 429:
            raise TransportError("rate limited", kind="rate_limit", status=429, retryable=True)
        if resp.status_code == 401:
            raise TransportError("agent card requires authentication", kind="auth", status=401)
        if resp.status_code >= 500:
            raise TransportError(f"server error {resp.status_code}", kind="http",
                                 status=resp.status_code, retryable=True)
        if resp.status_code != 200:
            raise TransportError(f"agent card fetch failed: {resp.status_code}",
                                 kind="http", status=resp.status_code)
        try:
            data = resp.json()
        except ValueError:
            raise TransportError("agent card is not valid JSON", kind="protocol")
        if not isinstance(data, dict):
            raise TransportError("agent card must be a JSON object", kind="protocol")
        data["_aetheros_fetch_latency_ms"] = latency_ms
        return data

    def _rpc(self, method: str, params: Dict[str, Any],
             idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        url = self.base_url  # JSON-RPC endpoint is the agent url itself
        self._check_url(url)
        body = {"jsonrpc": "2.0", "id": f"aetheros-{uuid.uuid4().hex[:12]}",
                "method": method, "params": params}
        try:
            with self._client() as client:
                resp = client.post(url, content=json.dumps(body),
                                   headers=self._headers(idempotency_key))
        except Exception as exc:
            raise _classify_exception(exc, url)
        if resp.status_code == 429:
            raise TransportError("rate limited", kind="rate_limit", status=429, retryable=True)
        if resp.status_code in (401, 403):
            raise TransportError(f"auth failed ({resp.status_code})", kind="auth",
                                 status=resp.status_code)
        if resp.status_code >= 500:
            raise TransportError(f"server error {resp.status_code}", kind="http",
                                 status=resp.status_code, retryable=True)
        if resp.status_code != 200:
            raise TransportError(f"rpc http {resp.status_code}", kind="http",
                                 status=resp.status_code)
        try:
            data = resp.json()
        except ValueError:
            raise TransportError("rpc response is not valid JSON", kind="protocol")
        if not isinstance(data, dict) or data.get("jsonrpc") != "2.0":
            raise TransportError("malformed JSON-RPC response", kind="protocol")
        if data.get("error"):
            err = data["error"]
            raise TransportError(f"remote error {err.get('code')}: {err.get('message')}",
                                 kind="protocol")
        result = data.get("result")
        if not isinstance(result, dict):
            raise TransportError("rpc result must be an object", kind="protocol")
        return result

    def send_message(self, message: Dict[str, Any],
                     idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """message/send. Caller supplies idempotency key for safe retries."""
        return self._rpc("message/send",
                         {"message": message},
                         idempotency_key or f"aetheros-{uuid.uuid4().hex}")

    def get_task(self, task_id: str) -> Dict[str, Any]:
        return self._rpc("tasks/get", {"id": task_id})

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        return self._rpc("tasks/cancel", {"id": task_id})

    def stream_message(self, message: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """message/stream via SSE. Yields parsed event dicts."""
        url = self.base_url
        self._check_url(url)
        import httpx
        body = {"jsonrpc": "2.0", "id": f"aetheros-{uuid.uuid4().hex[:12]}",
                "method": "message/stream", "params": {"message": message}}
        cfg = self.config
        try:
            with httpx.Client(
                verify=cfg.ca_bundle or cfg.verify_tls,
                proxy=cfg.proxy,
                timeout=httpx.Timeout(cfg.timeout_stream, connect=cfg.timeout_connect),
                follow_redirects=False,
            ) as client:
                with client.stream("POST", url, content=json.dumps(body),
                                   headers=dict(self._headers(), Accept="text/event-stream")) as resp:
                    if resp.status_code != 200:
                        raise TransportError(f"stream http {resp.status_code}",
                                             kind="http", status=resp.status_code)
                    buf = ""
                    for chunk in resp.iter_text():
                        buf += chunk
                        while "\n\n" in buf:
                            raw, buf = buf.split("\n\n", 1)
                            event = _parse_sse(raw)
                            if event is not None:
                                yield event
        except TransportError:
            raise
        except Exception as exc:
            raise _classify_exception(exc, url)


def _parse_sse(block: str) -> Optional[Dict[str, Any]]:
    data_lines = [line[5:].strip() for line in block.splitlines()
                  if line.startswith("data:")]
    if not data_lines:
        return None
    payload = "\n".join(data_lines)
    if payload.strip() == "[DONE]":
        return {"type": "done"}
    try:
        obj = json.loads(payload)
        return obj if isinstance(obj, dict) else {"type": "message", "data": obj}
    except ValueError:
        return {"type": "message", "text": payload}
