"""Agent SDK runtime (Master 62 §8-10): manifests, lifecycle, capabilities.

Lifecycle REGISTERED -> CREATED -> READY -> RUNNING -> WAITING/PAUSED ->
COMPLETED/FAILED/CANCELLED (+ QUARANTINED/TERMINATED). Transitions enforced;
illegal transitions raise. Persistence + audit via Master 61 `aetheros_data`.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from aetheros_platform.errors import err
from aetheros_platform.policy import PolicyBridge
from aetheros_platform.schemas import AGENT_STATES, validate

TRANSITIONS: Dict[str, tuple] = {
    "REGISTERED": ("CREATED", "QUARANTINED"),
    "CREATED": ("READY", "QUARANTINED", "TERMINATED"),
    "READY": ("RUNNING", "PAUSED", "TERMINATED", "QUARANTINED"),
    "RUNNING": ("WAITING", "PAUSED", "COMPLETED", "FAILED", "CANCELLED", "QUARANTINED"),
    "WAITING": ("RUNNING", "PAUSED", "CANCELLED", "FAILED"),
    "PAUSED": ("RUNNING", "CANCELLED", "TERMINATED"),
    "COMPLETED": ("TERMINATED", "READY"),
    "FAILED": ("READY", "TERMINATED"),
    "CANCELLED": ("TERMINATED",),
    "QUARANTINED": ("TERMINATED", "READY"),
    "TERMINATED": (),
}


class AgentRegistry:
    def __init__(self, engine=None, audit: Optional[Callable] = None) -> None:
        from aetheros_data.engine import get_engine
        self.e = engine or get_engine()
        from aetheros_data.records import AgentRepository
        self.repo = AgentRepository(self.e)
        self.policy = PolicyBridge(audit=audit)
        self._audit = audit

    # -- manifest ---------------------------------------------------------
    def validate_manifest(self, manifest: Dict[str, Any]) -> List[str]:
        errors = validate("Agent", manifest)
        for cap in manifest.get("capabilities", []):
            if not isinstance(cap, str) or "." not in cap:
                errors.append(f"capabilities: malformed capability {cap!r}")
        return errors

    def register(self, manifest: Dict[str, Any], owner: str = "") -> Dict[str, Any]:
        errors = self.validate_manifest(manifest)
        if errors:
            raise err("INVALID_SCHEMA", f"agent manifest invalid: {errors[0]}",
                      remediation="fix the manifest and re-register")
        agent_id = f"agent_{uuid.uuid4().hex[:12]}"
        record = self.repo.register(agent_id, {"manifest": manifest, "state": "REGISTERED",
                                               "owner": owner, "created_at": time.time()},
                                    idempotency_key=f"agent-manifest:{manifest['name']}:{manifest['version']}")
        if record["data"].get("state", "REGISTERED") != "REGISTERED":
            # Idempotent replay: same name+version already registered — return it.
            return self.get(record["record_id"])  # type: ignore[return-value]
        self._transition(record["record_id"], "CREATED", expected="REGISTERED")
        self._transition(record["record_id"], "READY", expected="CREATED")
        if self._audit:
            self._audit("agent.registered", owner, agent_id, "ok", {"name": manifest["name"]})
        return self.get(record["record_id"])  # type: ignore[return-value]

    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self.repo.get(agent_id)

    def list(self) -> List[Dict[str, Any]]:
        rows = self.e._conn().execute(
            "SELECT * FROM records WHERE domain='agent'").fetchall()
        out = []
        for r in rows:
            import json
            d = dict(r)
            d["data"] = json.loads(d["data"])
            out.append(d)
        return out

    def _transition(self, agent_id: str, to: str, expected: Optional[str] = None) -> Dict[str, Any]:
        rec = self.repo.get(agent_id)
        if rec is None:
            raise err("AGENT_UNAVAILABLE", f"unknown agent {agent_id}")
        cur = rec["data"].get("state", "REGISTERED")
        if expected is not None and cur != expected:
            raise err("CONFLICT", f"expected {expected}, agent is {cur}")
        if to not in TRANSITIONS.get(cur, ()):
            raise err("CONFLICT", f"illegal agent transition {cur} -> {to}",
                      remediation="follow the documented lifecycle")
        data = dict(rec["data"])
        data["state"] = to
        data["updated_at"] = time.time()
        out = self.repo.transition(agent_id, rec["version"], data)
        return out["record"]

    # -- execution ----------------------------------------------------------
    def run_task(self, agent_id: str, task_input: Dict[str, Any],
                 actor: str = "", tool_runner=None,
                 tool_caps_fn: Optional[Callable[[str], List[str]]] = None
                 ) -> Dict[str, Any]:
        """Intent -> policy -> capability -> tool -> result, all audited."""
        rec = self.repo.get(agent_id)
        if rec is None:
            raise err("AGENT_UNAVAILABLE", f"unknown agent {agent_id}")
        manifest = rec["data"]["manifest"]
        if rec["data"].get("state") == "QUARANTINED":
            raise err("SECURITY_VIOLATION", "agent is quarantined")
        self._transition(agent_id, "RUNNING", expected="READY")
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        try:
            grants = list(manifest.get("capabilities", []))
            needed = task_input.get("capability", "artifact.create")
            decision = self.policy.require_allowed(
                {"capability": needed, "actor": actor}, grants)
            result_output: Dict[str, Any] = {"capability": needed,
                                             "decision": decision["decision_id"]}
            if tool_runner is not None and task_input.get("tool"):
                tool_name = task_input["tool"]
                # Least-privilege delegation: the tool executes with only the
                # authority it declares AND the agent holds. An agent can never
                # delegate a capability it was not granted, and a tool never
                # inherits the agent's unrelated capabilities.
                tool_grants = grants
                if tool_caps_fn is not None:
                    tcaps = tool_caps_fn(tool_name)
                    missing = [c for c in tcaps if c not in grants]
                    if missing:
                        raise err("CAPABILITY_NOT_GRANTED",
                                  f"agent lacks capabilities the tool "
                                  f"'{tool_name}' requires: {missing[:5]}",
                                  capability=missing[0],
                                  remediation="grant the capability to the "
                                              "agent manifest or pick another "
                                              "tool")
                    tool_grants = [g for g in grants if g in set(tcaps)]
                tool_result = tool_runner(tool_name, task_input.get("args", {}),
                                          actor=actor, grants=tool_grants)
                result_output["tool_result"] = tool_result
            self._transition(agent_id, "COMPLETED", expected="RUNNING")
            self._transition(agent_id, "READY", expected="COMPLETED")
            if self._audit:
                self._audit("agent.task_completed", actor, task_id, "ok", {})
            return {"taskId": task_id, "state": "COMPLETED", "output": result_output,
                    "artifacts": [], "usage": {}}
        except Exception as exc:
            try:
                cur = (self.repo.get(agent_id) or {}).get("data", {}).get("state")
                if cur == "RUNNING":
                    self._transition(agent_id, "FAILED", expected="RUNNING")
            except Exception:
                pass
            if isinstance(exc, err.__class__) or hasattr(exc, "category"):
                raise
            raise err("INTERNAL_ERROR", f"agent run failed: {exc}") from exc

    def quarantine(self, agent_id: str, reason: str = "") -> None:
        rec = self.repo.get(agent_id)
        if rec is None:
            raise err("AGENT_UNAVAILABLE", f"unknown agent {agent_id}")
        cur = rec["data"].get("state", "REGISTERED")
        if "QUARANTINED" in TRANSITIONS.get(cur, ()):
            self._transition(agent_id, "QUARANTINED", expected=cur)
        if self._audit:
            self._audit("agent.quarantined", "", agent_id, "ok", {"reason": reason})
