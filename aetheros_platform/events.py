"""Typed events, SSE feed, webhooks, tenancy, usage, observability (M62 §29-31, §59-62, §96-97)."""

from __future__ import annotations

import hashlib
import hmac
import json
import queue
import threading
import time
import urllib.request
import uuid
from typing import Any, Callable, Dict, List, Optional

EVENT_TYPES = ("AgentStarted", "AgentCompleted", "TaskCreated", "TaskUpdated",
               "ToolInvoked", "ToolCompleted", "ApprovalRequested",
               "ApprovalResolved", "MemoryWritten", "ResearchEvidenceAdded",
               "ArtifactCreated", "AutomationTriggered", "PolicyDenied",
               "SecurityAlert", "ModelInvocation", "MCPRequest", "A2ARequest")


class EventBus:
    """In-process typed bus; the gateway exposes it as real SSE (no polling)."""

    def __init__(self) -> None:
        self._subs: List[queue.Queue] = []
        self._lock = threading.Lock()
        self._seq = 0

    def emit(self, kind: str, source: str = "", task: str = "", agent: str = "",
             payload: Optional[Dict[str, Any]] = None,
             classification: str = "internal",
             correlation_id: str = "", causation_id: str = "") -> Dict[str, Any]:
        assert kind in EVENT_TYPES, kind
        with self._lock:
            self._seq += 1
            event = {"eventId": f"evt_{uuid.uuid4().hex[:12]}",
                     "seq": self._seq, "timestamp": time.time(), "type": kind,
                     "source": source, "task": task, "agent": agent,
                     "correlationId": correlation_id or f"corr_{uuid.uuid4().hex[:8]}",
                     "causationId": causation_id, "schemaVersion": 1,
                     "payload": payload or {}, "securityClassification": classification}
            for q in list(self._subs):
                try:
                    q.put_nowait(event)
                except queue.Full:
                    pass
            return event

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=1000)
        with self._lock:
            self._subs.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subs:
                self._subs.remove(q)


BUS = EventBus()


# -- webhooks ---------------------------------------------------------------

def sign_payload(secret: str, body: bytes, timestamp: str, delivery_id: str) -> str:
    msg = timestamp.encode() + b"." + delivery_id.encode() + b"." + body
    return "sha256=" + hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def verify_signature(secret: str, body: bytes, timestamp: str,
                     delivery_id: str, signature: str) -> bool:
    if abs(time.time() - float(timestamp)) > 300:
        return False  # replay protection: 5-minute window
    return hmac.compare_digest(sign_payload(secret, body, timestamp, delivery_id), signature)


class WebhookRegistry:
    def __init__(self, audit: Optional[Callable] = None) -> None:
        self._hooks: Dict[str, Dict[str, Any]] = {}
        self._deliveries: List[Dict[str, Any]] = []
        self._seen_delivery: set = set()
        self._audit = audit

    def register(self, url: str, events: List[str], secret: Optional[str] = None) -> Dict[str, Any]:
        from aetheros_platform.schemas import validate
        errors = validate("Webhook", {"url": url, "events": events})
        if errors:
            from aetheros_platform.errors import err
            raise err("INVALID_SCHEMA", errors[0])
        hid = f"wh_{uuid.uuid4().hex[:10]}"
        hook = {"id": hid, "url": url, "events": events,
                "secret_ref": "stored",
                "enabled": True, "created_at": time.time()}
        self._hooks[hid] = hook
        # Secret value kept in memory only, never in payloads/logs.
        hook["_secret"] = secret or uuid.uuid4().hex
        public = {k: v for k, v in hook.items() if not k.startswith("_")}
        if self._audit:
            self._audit("webhook.registered", "", hid, "ok", {"url": url})
        return public

    def dispatch(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        body = json.dumps(event).encode()
        for hook in self._hooks.values():
            if not hook["enabled"] or event.get("type") not in hook["events"]:
                continue
            delivery_id = f"dlv_{uuid.uuid4().hex[:10]}"
            ts = str(int(time.time()))
            sig = sign_payload(hook["_secret"], body, ts, delivery_id)
            rec: Dict[str, Any] = {"delivery_id": delivery_id, "hook": hook["id"],
                                   "event": event["eventId"], "attempts": 0,
                                   "status": "pending"}
            backoff = 1.0
            for attempt in range(4):
                rec["attempts"] += 1
                try:
                    req = urllib.request.Request(
                        hook["url"], data=body,
                        headers={"Content-Type": "application/json",
                                 "X-Aetheros-Signature": sig,
                                 "X-Aetheros-Timestamp": ts,
                                 "X-Aetheros-Delivery": delivery_id,
                                 "X-Idempotency-Key": delivery_id},
                        method="POST")
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        if 200 <= resp.status < 300:
                            rec["status"] = "delivered"
                            break
                        rec["status"] = f"http-{resp.status}"
                except Exception as exc:
                    rec["status"] = f"error: {str(exc)[:120]}"
                time.sleep(min(backoff, 2.0))
                backoff *= 2
            else:
                rec["status"] = "dead-letter"
            self._deliveries.append(rec)
            results.append(rec)
        return results

    def deliveries(self) -> List[Dict[str, Any]]:
        return list(self._deliveries)

    def set_enabled(self, hook_id: str, enabled: bool) -> None:
        self._hooks[hook_id]["enabled"] = enabled


# -- tenancy / usage / observability ------------------------------------------

class TenantScope:
    """Org -> Workspace -> Project -> Agent -> Task. Ownership checked on
    every access; knowing a resource ID never grants cross-tenant access."""

    def __init__(self, organization: str = "default", workspace: str = "default",
                 project: str = "default") -> None:
        self.organization, self.workspace, self.project = organization, workspace, project

    def key(self) -> str:
        return f"{self.organization}/{self.workspace}/{self.project}"

    def owns(self, resource: Dict[str, Any]) -> bool:
        t = resource.get("tenant", {})
        return (t.get("organization", "default") == self.organization
                and t.get("workspace", "default") == self.workspace)


class UsageLedger:
    """Usage accounting WITHOUT fabricated costs: tokens/calls/runtime recorded;
    cost stays None unless a rate card is explicitly configured."""

    def __init__(self) -> None:
        self._records: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def record(self, actor: str, workspace: str = "", model: str = "",
               tokens: int = 0, tool_calls: int = 0, runtime_s: float = 0.0,
               storage_bytes: int = 0, network_bytes: int = 0) -> Dict[str, Any]:
        rec = {"actor": actor, "workspace": workspace, "model": model,
               "tokens": tokens, "toolCalls": tool_calls, "runtime": runtime_s,
               "storage": storage_bytes, "network": network_bytes,
               "timestamp": time.time(), "cost": None}
        with self._lock:
            self._records.append(rec)
        return rec

    def summary(self, actor: str = "") -> Dict[str, Any]:
        recs = [r for r in self._records if not actor or r["actor"] == actor]
        return {"records": len(recs), "tokens": sum(r["tokens"] for r in recs),
                "toolCalls": sum(r["toolCalls"] for r in recs),
                "runtime": round(sum(r["runtime"] for r in recs), 3)}


USAGE = UsageLedger()


def redact(obj: Any) -> Any:
    """Strip secret-looking values before logs/traces/telemetry."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            kl = k.lower()
            if any(s in kl for s in ("key", "secret", "token", "password", "credential", "auth")):
                out[k] = "[REDACTED]"
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj
