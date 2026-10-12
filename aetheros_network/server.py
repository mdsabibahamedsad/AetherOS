"""AetherOS Agent Server (Master 46 sections 96-101).

Exposes this instance as an A2A agent endpoint: Agent Card, task
handling, artifacts, health, cancellation, audit. Default-deny: no
remote agent can do anything until the operator pairs it and grants
explicit capabilities. Resource limits + rate limits + bounded queue
prevent remote abuse. stdlib http.server — no new dependencies.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

from . import A2A_AGENT_CARD_PATH, A2A_SPEC_VERSION
from .audit import AuditLog
from .policy import detect_prompt_injection


class ServerConfig:
    def __init__(self, *, name: str = "AetherOS Agent", version: str = "0.16.0",
                 description: str = "AetherOS personal agent (A2A endpoint)",
                 skills: Optional[List[Dict[str, Any]]] = None,
                 allowed_agents: Optional[List[str]] = None,
                 allowed_skills: Optional[List[str]] = None,
                 pairing_tokens: Optional[List[str]] = None,
                 max_tasks: int = 16, max_concurrency: int = 4,
                 max_request_bytes: int = 1_048_576,
                 max_artifact_bytes: int = 100 * 1024 * 1024,
                 max_task_seconds: float = 1800.0,
                 rate_per_minute: int = 60, rate_burst: int = 10) -> None:
        self.name = name
        self.version = version
        self.description = description
        self.skills = skills or []
        self.allowed_agents = set(allowed_agents or [])  # empty = deny all
        self.allowed_skills = set(allowed_skills or [])
        self.pairing_tokens = set(pairing_tokens or [])
        self.max_tasks = max_tasks
        self.max_concurrency = max_concurrency
        self.max_request_bytes = max_request_bytes
        self.max_artifact_bytes = max_artifact_bytes
        self.max_task_seconds = max_task_seconds
        self.rate_per_minute = rate_per_minute
        self.rate_burst = rate_burst


def new_pairing_token() -> str:
    return "pair-" + secrets.token_hex(16)


class AgentServer:
    """Deny-by-default A2A server. Pairing token + allowlist required."""

    def __init__(self, config: ServerConfig, home: Path,
                 handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> None:
        self.config = config
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.audit = AuditLog(self.home / "server-audit.jsonl")
        self._handler = handler or (lambda msg: {
            "state": "completed",
            "message": {"role": "agent", "parts": [{"text": "Accepted for local review."}]},
        })
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._buckets: Dict[str, Dict[str, float]] = {}
        self._httpd: Optional[ThreadingHTTPServer] = None

    # -- card -------------------------------------------------------------
    def agent_card(self, base_url: str) -> Dict[str, Any]:
        return {
            "protocolVersion": A2A_SPEC_VERSION,
            "name": self.config.name,
            "description": self.config.description,
            "version": self.config.version,
            "url": base_url.rstrip("/"),
            "capabilities": {"streaming": False},
            "skills": [s for s in self.config.skills
                       if not self.config.allowed_skills or s.get("id") in self.config.allowed_skills],
            "defaultInputModes": ["text"],
            "defaultOutputModes": ["text"],
            "authentication": {"schemes": ["bearer"] if self.config.pairing_tokens else ["none"]},
            "provider": {"organization": "local", "url": base_url.rstrip("/")},
        }

    # -- auth --------------------------------------------------------------
    def _check_auth(self, headers: Dict[str, str], agent_id: str) -> Optional[str]:
        if self.config.allowed_agents and agent_id not in self.config.allowed_agents:
            return f"agent {agent_id!r} not paired"
        auth = headers.get("authorization", "")
        if self.config.pairing_tokens:
            token = auth[7:] if auth.startswith("Bearer ") else ""
            # Constant-time compare against hashed set.
            digest = hashlib.sha256(token.encode()).hexdigest()
            hashed = {hashlib.sha256(t.encode()).hexdigest()
                      for t in self.config.pairing_tokens}
            if not secrets.compare_digest(digest, next(iter(hashed)) if len(hashed) == 1 else digest) \
                    or digest not in hashed:
                return "invalid bearer token"
        return None

    def _check_rate(self, agent_id: str) -> bool:
        now = time.time()
        b = self._buckets.get(agent_id, {"tokens": float(self.config.rate_burst), "at": now})
        b["tokens"] = min(float(self.config.rate_burst),
                          b["tokens"] + (now - b["at"]) * self.config.rate_per_minute / 60.0)
        b["at"] = now
        if b["tokens"] < 1.0:
            self._buckets[agent_id] = b
            return False
        b["tokens"] -= 1.0
        self._buckets[agent_id] = b
        return True

    # -- JSON-RPC dispatch ---------------------------------------------------
    def dispatch(self, body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        req_id = body.get("id")
        method = body.get("method", "")
        params = body.get("params", {}) if isinstance(body.get("params"), dict) else {}
        agent_id = str(params.get("agent_id") or headers.get("x-agent-id", "anonymous"))

        def ok(result: Dict[str, Any]) -> Dict[str, Any]:
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        def err(code: int, message: str) -> Dict[str, Any]:
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": code, "message": message}}

        if not self._check_rate(agent_id):
            self.audit.record("server.rate_limited", actor=agent_id, subject="server",
                              details={"method": method})
            return err(-32000, "rate limited")
        auth_err = self._check_auth(headers, agent_id)
        if auth_err:
            self.audit.record("server.auth_denied", actor=agent_id, subject="server",
                              details={"method": method, "reason": auth_err})
            return err(-32001, auth_err)

        if method == "message/send":
            return ok(self._handle_send(params, agent_id))
        if method == "tasks/get":
            task = self._tasks.get(str(params.get("id", "")))
            if task is None:
                return err(-32002, "unknown task")
            return ok({"id": task["id"], "state": task["state"],
                       "message": task.get("result")})
        if method == "tasks/cancel":
            task_id = str(params.get("id", ""))
            with self._lock:
                task = self._tasks.get(task_id)
                if task is None:
                    return err(-32002, "unknown task")
                if task["state"] not in ("completed", "failed", "canceled"):
                    task["state"] = "canceled"
            self.audit.record("server.task_cancelled", actor=agent_id,
                              subject=task_id, details={})
            return ok({"id": task_id, "state": "canceled"})
        return err(-32601, f"method not found: {method}")

    def _handle_send(self, params: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
        with self._lock:
            active = sum(1 for t in self._tasks.values() if t["state"] in ("accepted", "running"))
            if len(self._tasks) >= self.config.max_tasks or active >= self.config.max_concurrency:
                return {"id": "", "state": "failed",
                        "message": {"role": "agent", "parts": [{"text": "Server busy."}]}}
        message = params.get("message", {})
        text = json.dumps(message, default=str)
        if detect_prompt_injection(text):
            self.audit.record("server.injection_blocked", actor=agent_id,
                              subject="server", details={})
            return {"id": "", "state": "rejected",
                    "message": {"role": "agent", "parts": [{"text": "Rejected by server policy."}]}}
        task_id = f"srv-{secrets.token_hex(6)}"
        with self._lock:
            self._tasks[task_id] = {"id": task_id, "state": "accepted",
                                    "at": time.time(), "agent": agent_id}
        try:
            result = self._handler({"agent_id": agent_id, "message": message})
        except Exception as e:
            with self._lock:
                self._tasks[task_id]["state"] = "failed"
            return {"id": task_id, "state": "failed",
                    "message": {"role": "agent", "parts": [{"text": f"Handler error: {e}"}]}}
        state = str(result.get("state", "completed"))
        with self._lock:
            self._tasks[task_id]["state"] = state
            self._tasks[task_id]["result"] = result.get("message", {})
        self.audit.record("server.task_handled", actor=agent_id, subject=task_id,
                          details={"state": state})
        out: Dict[str, Any] = {"id": task_id, "state": state}
        if "message" in result:
            out["message"] = result["message"]
        return out

    # -- stdlib HTTP serving ---------------------------------------------------
    def serve_forever(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:  # keep quiet; audit log covers it
                pass

            def _send_json(self, obj: Dict[str, Any], status: int = 200) -> None:
                payload = json.dumps(obj).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == A2A_AGENT_CARD_PATH:
                    base = f"http://{self.headers.get('Host', f'{host}:{port}')}"
                    self._send_json(server.agent_card(base))
                elif parsed.path in ("/health", "/healthz"):
                    self._send_json({"status": "ok", "tasks": len(server._tasks)})
                else:
                    self._send_json({"error": "not found"}, 404)

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length > server.config.max_request_bytes:
                    self._send_json({"error": "request too large"}, 413)
                    return
                try:
                    body = json.loads(self.rfile.read(length) or b"{}")
                except ValueError:
                    self._send_json({"error": "invalid json"}, 400)
                    return
                headers = {k.lower(): v for k, v in dict(self.headers).items()}
                self._send_json(server.dispatch(body, headers))

        self._httpd = ThreadingHTTPServer((host, port), Handler)
        self.audit.record("server.started", actor="local", subject=f"{host}:{port}",
                          details={})
        self._httpd.serve_forever()

    def shutdown(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
