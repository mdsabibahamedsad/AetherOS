"""
AetherOS Agent Hypervisor 1.0 — secret broker (§30-§32).

Raw secrets are never placed in the agent's environment (§30). Instead,
capabilities use secrets *through* the broker: the agent holds an opaque
handle, the provider resolves the value server-side, and every use is
scoped (agent/capsule/task/capability/destination/time) and audited (§32).

The broker is a scoping/audit layer, not a second vault: values may be
registered from the existing secrets stores or injected for a task, and
the broker adds binding, rotation hooks, revocation, and audit.
"""

from __future__ import annotations

import hashlib
import logging
import secrets as _secrets
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.core.types import _now, new_id

logger = logging.getLogger(__name__)


@dataclass
class SecretBinding:
    """A scoped credential binding (§32)."""
    binding_id: str = field(default_factory=lambda: new_id("secret"))
    name: str = ""  # logical name, e.g. "github.token"
    agent_id: str = ""
    capsule_id: str = ""
    task_id: str = ""
    capability: str = ""
    destination: str = ""
    fingerprint: str = ""  # sha256 of value; the value itself is not logged
    created_at: float = field(default_factory=_now)
    expires_at: Optional[float] = None
    revoked: bool = False
    rotation_of: Optional[str] = None

    def usable(self) -> bool:
        if self.revoked:
            return False
        if self.expires_at and _now() > self.expires_at:
            return False
        return True

    def to_dict(self, *, redacted: bool = True) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "name": self.name,
            "agent_id": self.agent_id,
            "capsule_id": self.capsule_id,
            "task_id": self.task_id,
            "capability": self.capability,
            "destination": self.destination,
            "fingerprint": self.fingerprint,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "revoked": self.revoked,
            "rotation_of": self.rotation_of,
        }


class SecretBroker:
    """Capability-mediated secret use (§31)."""

    def __init__(self, audit: Optional[Callable[..., None]] = None) -> None:
        self._lock = threading.RLock()
        self._values: Dict[str, str] = {}  # binding_id -> value (never serialized)
        self._bindings: Dict[str, SecretBinding] = {}
        self._audit = audit or (lambda *a, **k: None)
        self._use_log: List[Dict[str, Any]] = []

    @staticmethod
    def fingerprint(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    def request_secret(
        self,
        name: str,
        value: str,
        *,
        agent_id: str,
        capsule_id: str,
        task_id: str = "",
        capability: str = "",
        destination: str = "",
        ttl_seconds: float = 3600.0,
    ) -> SecretBinding:
        """Register a secret value under a scoped binding (broker-side only)."""
        binding = SecretBinding(
            name=name, agent_id=agent_id, capsule_id=capsule_id,
            task_id=task_id, capability=capability, destination=destination,
            fingerprint=self.fingerprint(value),
            # ttl<=0 (or None) => no expiry; negative => already expired.
            expires_at=(_now() + ttl_seconds) if ttl_seconds else None,
        )
        with self._lock:
            self._bindings[binding.binding_id] = binding
            self._values[binding.binding_id] = value
        self._audit("secret.request", agent_id, capsule_id,
                    {"name": name, "binding_id": binding.binding_id,
                     "capability": capability, "destination": destination})
        return binding

    def authorize_secret(self, binding_id: str, *, capability: str,
                         destination: str = "") -> bool:
        """Check a use-request against the binding scope (no value returned)."""
        with self._lock:
            binding = self._bindings.get(binding_id)
        if binding is None or not binding.usable():
            return False
        if binding.capability and binding.capability != capability:
            # Capability-scoped bindings only serve their capability...
            # ...unless the binding was issued wildcard-empty.
            return False
        if binding.destination and destination and binding.destination != destination:
            return False
        return True

    def use_secret(self, binding_id: str, *,
                   agent_id: str, capability: str, destination: str = "",
                   redacted_preview: bool = True) -> Dict[str, Any]:
        """Capability-mediated use: the caller gets a result envelope, and
        the plaintext is exposed ONLY to the capability provider callback.

        Returns {"ok", "fingerprint", "preview"} — never the value. To have
        the provider consume the value, use `with_resolved`.
        """
        with self._lock:
            binding = self._bindings.get(binding_id)
        if binding is None:
            return {"ok": False, "reason": "unknown binding"}
        if binding.agent_id != agent_id:
            return {"ok": False, "reason": "agent scope mismatch"}
        if not binding.usable():
            return {"ok": False, "reason": "binding revoked or expired"}
        if not self.authorize_secret(binding_id, capability=capability,
                                     destination=destination):
            return {"ok": False, "reason": "capability/destination scope mismatch"}
        record = {"binding_id": binding_id, "agent_id": agent_id,
                  "capability": capability, "destination": destination,
                  "at": _now()}
        with self._lock:
            self._use_log.append(record)
        self._audit("secret.use", agent_id, binding.capsule_id, record)
        preview = f"‹{binding.fingerprint}›" if redacted_preview else "‹redacted›"
        return {"ok": True, "fingerprint": binding.fingerprint, "preview": preview}

    def with_resolved(self, binding_id: str, *,
                      agent_id: str, capability: str, destination: str = "",
                      consumer: Callable[[str], Any]) -> Any:
        """Resolve the plaintext *inside* the broker and hand it only to the
        provider callback. The agent process never sees the value."""
        check = self.use_secret(binding_id, agent_id=agent_id,
                                capability=capability, destination=destination)
        if not check["ok"]:
            raise PermissionError(f"secret use denied: {check['reason']}")
        with self._lock:
            value = self._values.get(binding_id)
        if value is None:
            raise PermissionError("secret value unavailable (rotated or revoked)")
        return consumer(value)

    def rotate_secret(self, binding_id: str, new_value: str,
                      *, agent_id: str) -> SecretBinding:
        with self._lock:
            old = self._bindings.get(binding_id)
            if old is None:
                raise KeyError(f"unknown binding: {binding_id}")
            if old.agent_id != agent_id:
                raise PermissionError("agent scope mismatch")
            new_binding = SecretBinding(
                name=old.name, agent_id=old.agent_id, capsule_id=old.capsule_id,
                task_id=old.task_id, capability=old.capability,
                destination=old.destination,
                fingerprint=self.fingerprint(new_value),
                expires_at=old.expires_at, rotation_of=old.binding_id)
            old.revoked = True
            self._values.pop(binding_id, None)
            self._bindings[new_binding.binding_id] = new_binding
            self._values[new_binding.binding_id] = new_value
        self._audit("secret.rotate", agent_id, old.capsule_id,
                    {"name": old.name, "old": binding_id,
                     "new": new_binding.binding_id})
        return new_binding

    def revoke_secret(self, binding_id: str, *, reason: str = "revoked") -> bool:
        with self._lock:
            binding = self._bindings.get(binding_id)
            if binding is None:
                return False
            binding.revoked = True
            self._values.pop(binding_id, None)
        self._audit("secret.revoke", binding.agent_id, binding.capsule_id,
                    {"binding_id": binding_id, "reason": reason})
        return True

    def audit_secret_use(self, binding_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [r for r in self._use_log if r["binding_id"] == binding_id]

    def bindings_for_capsule(self, capsule_id: str) -> List[SecretBinding]:
        with self._lock:
            return [b for b in self._bindings.values() if b.capsule_id == capsule_id]

    def gc_expired(self) -> int:
        now = _now()
        removed = 0
        with self._lock:
            for bid, binding in list(self._bindings.items()):
                if binding.expires_at and now > binding.expires_at:
                    binding.revoked = True
                    if self._values.pop(bid, None) is not None:
                        removed += 1
        return removed

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._bindings)
            active = sum(1 for b in self._bindings.values() if b.usable())
            return {"total_bindings": total, "active_bindings": active,
                    "uses": len(self._use_log)}
