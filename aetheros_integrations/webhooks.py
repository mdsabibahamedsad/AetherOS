"""AetherOS Integrations — Webhook Engine.

Incoming (signed/validated) and outgoing (signed, retried, deduplicated)
webhooks with history, replay, and loop protection. Signed with HMAC-SHA256
using the configured webhook secret. Deduplication keys prevent duplicate
deliveries; hop counting prevents webhook loops.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from aetheros_integrations.config import load_integrations_settings
from aetheros_integrations.models import WebhookDelivery
from aetheros_integrations.security import AuditLog

logger = logging.getLogger(__name__)


def sign_payload(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_signature(secret: str, payload: bytes, signature: str) -> bool:
    if not signature:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


def _dedup_key(event: str, payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(f"{event}:{canonical}".encode()).hexdigest()


class WebhookEngine:
    """Delivers outgoing webhooks and validates incoming ones."""

    def __init__(self, settings=None, audit: Optional[AuditLog] = None, dirpath=None, delivery_store: Optional["WebhookStore"] = None):
        from aetheros_integrations.config import get_aetheros_dir

        self._settings = settings or load_integrations_settings()
        self._dir = dirpath or get_aetheros_dir(self._settings.data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._audit = audit or AuditLog(dirpath=self._dir, settings=self._settings)
        self._secret = self._settings.webhook.secret or "aetheros-dev-webhook-secret"
        self._store = delivery_store or WebhookStore(self._dir)
        self._lock = threading.RLock()
        self._http = httpx.Client(timeout=self._settings.webhook.timeout_s)
        self._incoming_handlers: List[Callable[[Dict[str, Any], WebhookDelivery], Any]] = []

    def close(self) -> None:
        self._http.close()

    @property
    def secret(self) -> str:
        return self._secret

    # -- incoming ---------------------------------------------------------

    def register_handler(self, handler: Callable[[Dict[str, Any], WebhookDelivery], Any]) -> None:
        self._incoming_handlers.append(handler)

    def handle_incoming(
        self,
        body: bytes,
        *,
        signature: str = "",
        event: str = "",
        integration_id: str = "",
        headers: Optional[Dict[str, str]] = None,
    ) -> WebhookDelivery:
        """Validate an incoming webhook signature and dispatch to handlers."""
        valid = verify_signature(self._secret, body, signature) if signature else True
        payload: Dict[str, Any] = {}
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {"_raw": body.decode("utf-8", "replace")}
        hop_count = int((headers or {}).get("X-AetherOS-Hops", "0") or 0)
        delivery = WebhookDelivery(
            direction="incoming",
            integration_id=integration_id,
            event=event or payload.get("event", "webhook.incoming"),
            payload=payload,
            signature_valid=valid,
            status="rejected" if not valid else "delivered",
            hop_count=hop_count,
            dedup_key=_dedup_key(event, payload),
        )
        if not valid:
            delivery.last_error = "signature mismatch"
            self._store.save(delivery)
            self._audit.record("webhook.rejected", target=integration_id, detail={"reason": "bad signature"})
            return delivery
        if hop_count > self._settings.webhook.max_hops:
            delivery.status = "rejected"
            delivery.last_error = "hop limit exceeded"
            self._store.save(delivery)
            return delivery
        if self._store.exists_dedup(delivery.dedup_key, direction="incoming"):
            delivery.status = "rejected"
            delivery.last_error = "duplicate event (dedup)"
            self._store.save(delivery)
            return delivery
        delivery.delivered_at = time.time()
        self._store.save(delivery)
        for handler in list(self._incoming_handlers):
            try:
                handler(payload, delivery)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Incoming webhook handler failed: %s", exc)
        return delivery

    # -- outgoing ---------------------------------------------------------

    def deliver(
        self,
        url: str,
        payload: Dict[str, Any],
        *,
        event: str = "",
        integration_id: str = "",
        secret: str = "",
        extra_headers: Optional[Dict[str, str]] = None,
        max_attempts: Optional[int] = None,
    ) -> WebhookDelivery:
        """Send a signed outgoing webhook with retry/backoff and dedup."""
        dkey = _dedup_key(event, payload)
        delivery = WebhookDelivery(
            direction="outgoing",
            integration_id=integration_id,
            event=event,
            payload=payload,
            max_attempts=max_attempts or self._settings.webhook.default_max_attempts,
            dedup_key=dkey,
        )
        if self._store.exists_dedup(dkey, direction="outgoing"):
            delivery.status = "rejected"
            delivery.last_error = "duplicate delivery (dedup)"
            self._store.save(delivery)
            return delivery
        sec = secret or self._secret
        body = json.dumps(payload, default=str).encode("utf-8")
        signature = sign_payload(sec, body)
        headers = {
            "Content-Type": "application/json",
            "X-AetherOS-Event": event,
            "X-AetherOS-Signature": signature,
            "X-AetherOS-Hops": str(extra_headers.get("X-AetherOS-Hops", "0") if extra_headers else "0"),
            **(extra_headers or {}),
        }
        self._store.save(delivery)
        attempt = 0
        backoff = self._settings.webhook.retry_backoff_s
        while attempt < delivery.max_attempts:
            attempt += 1
            delivery.attempts = attempt
            started = time.perf_counter()
            try:
                resp = self._http.post(url, content=body, headers=headers)
                latency = (time.perf_counter() - started) * 1000
                delivery.latency_ms = round(latency, 2)
                if resp.status_code < 400:
                    delivery.status = "delivered"
                    delivery.delivered_at = time.time()
                    delivery.last_error = ""
                    break
                delivery.last_error = f"http {resp.status_code}"
            except httpx.HTTPError as exc:
                delivery.last_error = str(exc)
            except Exception as exc:  # noqa: BLE001
                delivery.last_error = str(exc)
            self._store.save(delivery)
            if attempt < delivery.max_attempts:
                time.sleep(backoff)
                backoff *= 2
        if delivery.status != "delivered":
            delivery.status = "failed"
        self._store.save(delivery)
        self._audit.record(
            "webhook.delivered" if delivery.status == "delivered" else "webhook.failed",
            target=integration_id,
            detail={"event": event, "url": url, "attempts": delivery.attempts, "error": delivery.last_error},
        )
        return delivery

    def replay(self, delivery_id: str, url: str, secret: str = "", max_attempts: Optional[int] = None) -> WebhookDelivery:
        """Replay a previously recorded delivery (history replay).

        The replayed delivery uses a fresh dedup key so it is never treated
        as a duplicate of the original attempt.
        """
        original = self._store.get(delivery_id)
        if original is None:
            raise KeyError(f"No delivery {delivery_id}")
        replay_payload = dict(original.payload)
        replay_payload["_replay_of"] = delivery_id
        return self.deliver(
            url,
            replay_payload,
            event=original.event,
            integration_id=original.integration_id,
            secret=secret,
            max_attempts=max_attempts,
        )

    def history(self, integration_id: str = "", limit: int = 100) -> List[WebhookDelivery]:
        return self._store.list(integration_id=integration_id, limit=limit)

    def stats(self) -> Dict[str, Any]:
        return self._store.stats()


class WebhookStore:
    """JSON-backed history of webhook deliveries."""

    def __init__(self, dirpath, limit: int = 5000):
        self._path = dirpath / "webhooks.json"
        self._limit = limit
        self._lock = threading.RLock()
        self._deliveries: Dict[str, WebhookDelivery] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for item in data:
                d = WebhookDelivery(**item)
                self._deliveries[d.id] = d
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load webhook history: %s", exc)

    def _save(self) -> None:
        payload = [d.to_dict() for d in self._deliveries.values()]
        if len(payload) > self._limit:
            payload = payload[-self._limit :]
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def save(self, delivery: WebhookDelivery) -> None:
        with self._lock:
            self._deliveries[delivery.id] = delivery
            self._save()

    def get(self, delivery_id: str) -> Optional[WebhookDelivery]:
        with self._lock:
            return self._deliveries.get(delivery_id)

    def exists_dedup(self, dedup_key: str, direction: str) -> bool:
        if not dedup_key:
            return False
        with self._lock:
            for d in self._deliveries.values():
                if d.dedup_key == dedup_key and d.direction == direction and d.status in ("delivered", "pending"):
                    return True
        return False

    def list(self, integration_id: str = "", limit: int = 100) -> List[WebhookDelivery]:
        with self._lock:
            items = list(self._deliveries.values())
        if integration_id:
            items = [d for d in items if d.integration_id == integration_id]
        items.sort(key=lambda d: d.created_at, reverse=True)
        return items[:limit]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            delivered = sum(1 for d in self._deliveries.values() if d.status == "delivered")
            failed = sum(1 for d in self._deliveries.values() if d.status == "failed")
            pending = sum(1 for d in self._deliveries.values() if d.status == "pending")
            attempts = sum(d.attempts for d in self._deliveries.values())
            latencies = [d.latency_ms for d in self._deliveries.values() if d.latency_ms]
            avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        return {"total": len(self._deliveries), "delivered": delivered, "failed": failed, "pending": pending, "attempts": attempts, "avg_latency_ms": avg_latency}
