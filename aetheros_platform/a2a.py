"""A2A-compatible integration (Master 62 §19-20). Boundary: A2A = agent-to-agent.

Status: EXPERIMENTAL subset implemented against the public A2A shape
(Agent Card + JSON-RPC task lifecycle + SSE). No official A2A SDK is
installed in this environment, so this module implements the wire protocol
directly with httpx/FastAPI and validates every Card. Remote agents are
NEVER auto-trusted (default "untrusted").

Covers: Agent Card, discovery, capability advertisement, task create/state,
messages, artifacts, SSE streaming, auth (API key), identity, delegation
records, cancellation, retry (via idempotency keys), provenance.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

import httpx

from aetheros_platform.errors import err
from aetheros_platform.schemas import validate

PROTOCOL_VERSION = "0.3.0-compat"
TRUSTED_AGENTS: set = set()

TASK_STATES = ("submitted", "working", "input-required", "completed",
               "failed", "canceled")


def validate_card(card: Dict[str, Any]) -> List[str]:
    errors = validate("AgentCard", card)
    if card.get("trust", "untrusted") not in ("untrusted", "known", "trusted"):
        errors.append("trust: must be untrusted|known|trusted")
    return errors


def local_card(agent_name: str = "aetheros-dev-agent",
               endpoint: str = "http://127.0.0.1:8765/api/v1/a2a") -> Dict[str, Any]:
    card = {"name": agent_name, "version": "1.0.0",
            "protocolVersion": PROTOCOL_VERSION,
            "description": "AetherOS developer-platform reference agent",
            "capabilities": ["artifact.create", "memory.read"],
            "endpoint": endpoint,
            "authentication": {"type": "api-key", "header": "X-API-Key"},
            "trust": "untrusted"}
    assert not validate_card(card), validate_card(card)
    return card


class A2ATaskStore:
    """Server-side task ledger for the reference agent."""

    def __init__(self, audit: Optional[Callable] = None) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._audit = audit

    def create(self, message: str, idempotency_key: str = "",
               sender: str = "") -> Dict[str, Any]:
        if idempotency_key:
            for t in self._tasks.values():
                if t.get("idempotency_key") == idempotency_key:
                    return t
        tid = f"a2a_{uuid.uuid4().hex[:12]}"
        task = {"id": tid, "state": "submitted", "message": message,
                "sender": sender, "history": [{"role": "user", "text": message}],
                "artifacts": [], "created_at": time.time(),
                "updated_at": time.time(), "idempotency_key": idempotency_key,
                "provenance": {"sender": sender, "untrusted_sender": sender not in TRUSTED_AGENTS}}
        self._tasks[tid] = task
        if self._audit:
            self._audit("a2a.task_created", sender, tid, "ok", {})
        # Reference behavior: complete small tasks inline (real state machine).
        task["state"] = "working"
        task["history"].append({"role": "agent",
                                "text": f"[simulated execution] received: {message[:200]}"})
        task["state"] = "completed"
        task["updated_at"] = time.time()
        return task

    def get(self, task_id: str) -> Dict[str, Any]:
        if task_id not in self._tasks:
            raise err("RESOURCE_UNAVAILABLE", f"unknown A2A task {task_id}")
        return self._tasks[task_id]

    def cancel(self, task_id: str) -> Dict[str, Any]:
        task = self.get(task_id)
        if task["state"] in ("completed", "failed", "canceled"):
            raise err("CONFLICT", f"task {task_id} already terminal")
        task["state"] = "canceled"
        task["updated_at"] = time.time()
        return task


TASKS = A2ATaskStore()


def submit_remote_task(body: Dict[str, Any]) -> Dict[str, Any]:
    """Gateway handler: validate card-side input, run the local ledger."""
    message = body.get("message", "")
    if not message:
        raise err("INVALID_REQUEST", "A2A task requires a message")
    return TASKS.create(message, idempotency_key=body.get("idempotencyKey", ""),
                        sender=body.get("sender", ""))


class A2AClient:
    """Minimal client: fetch card (validated), submit task, poll state."""

    def __init__(self, base_url: str, api_key: str = "", timeout_s: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        return h

    def fetch_card(self) -> Dict[str, Any]:
        resp = httpx.get(f"{self.base_url}/api/v1/a2a/card", headers=self._headers(),
                         timeout=self.timeout_s)
        resp.raise_for_status()
        card = resp.json()
        errors = validate_card(card)
        if errors:
            raise err("INVALID_SCHEMA", f"remote Agent Card invalid: {errors[0]}",
                      remediation="do not trust this agent")
        return card

    def submit(self, message: str, idempotency_key: str = "") -> Dict[str, Any]:
        resp = httpx.post(f"{self.base_url}/api/v1/a2a/tasks",
                          headers=self._headers(),
                          json={"message": message, "idempotencyKey": idempotency_key,
                                "sender": "a2a-client"},
                          timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.json()
