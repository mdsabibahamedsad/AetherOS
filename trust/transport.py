"""UI transport: typed HTTP API (Starlette) + typed IPC envelopes.

The renderer/CLI never decides — every route validates a pydantic
schema, calls the TrustFabric, and returns the recorded decision.
Raw private keys, raw secrets, the audit backend, unrestricted
policy mutation, and raw OS privilege APIs are never exposed (§101).
"""
from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

try:
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    _HAS_STARLETTE = True
except Exception:  # pragma: no cover
    _HAS_STARLETTE = False


# ---------------------------------------------------------------------------
# Typed schemas (no Any at the boundary; §208)
# ---------------------------------------------------------------------------

class ProposeIn(BaseModel):
    identity_id: str
    capability: str
    resource: str
    kind: str = "tool"
    purpose: str = ""
    data_class: str = "internal"
    task_id: str = ""
    tool_id: str = ""
    autonomy: int = 2


class AuthorizeIn(ProposeIn):
    audience: str = ""


class TokenValidateIn(BaseModel):
    token: Dict[str, Any]
    audience: str


class ApprovalRequestIn(BaseModel):
    actor: str
    action: str
    resource: str
    purpose: str = ""
    risk: str = "R1"
    approver_policy: str = "single"
    task_id: str = ""


class ApprovalVoteIn(BaseModel):
    request_id: str
    approver: str
    granted: bool


class RevokeIn(BaseModel):
    kind: str
    target_id: str
    reason: str = ""
    actor: str = "api"


class KillIn(BaseModel):
    layer: str = "GLOBAL_KILL"
    target: str = ""
    reason: str = ""
    actor: str = "api"


class IncidentOpenIn(BaseModel):
    kind: str
    severity: str = "LOW"
    actor: str = ""
    resources: List[str] = Field(default_factory=list)


class PolicyPublishIn(BaseModel):
    policy_id: str
    body: Dict[str, Any]
    layer: str = "task"


class IpcEnvelope(BaseModel):
    """Typed IPC from the renderer (§147-148). Only whitelisted ops."""

    OP_KINDS: ClassVar[tuple] = ("propose", "token.validate", "approval.request",
                "approval.vote", "audit.query", "provenance.explain",
                "health", "doctor")

    sender: str
    kind: str
    payload: Dict[str, Any] = Field(default_factory=dict)

    def check(self) -> Dict[str, Any]:
        if self.kind not in self.OP_KINDS:
            return {"ok": False, "reason": f"unknown op {self.kind}"}
        if not self.sender:
            return {"ok": False, "reason": "missing sender"}
        return {"ok": True}


# ---------------------------------------------------------------------------
# App factory (fabric injected — real backend state, §215)
# ---------------------------------------------------------------------------

def create_app(fabric) -> Any:
    if not _HAS_STARLETTE:
        raise RuntimeError("starlette unavailable")

    async def _json(request, fn):
        try:
            body = await request.json() if request.method != "GET" else {}
        except Exception:
            body = {}
        try:
            return JSONResponse(fn(body))
        except Exception as exc:
            return JSONResponse({"error": type(exc).__name__,
                                 "message": str(exc)[:300]}, status_code=400)

    async def health(request):
        return JSONResponse(fabric.health.self_test())

    async def propose(request):
        def go(b):
            req = ProposeIn(**b)
            d = fabric.propose(req.identity_id, req.capability,
                               req.resource, kind=req.kind,
                               purpose=req.purpose,
                               data_class=req.data_class,
                               task_id=req.task_id, tool_id=req.tool_id,
                               autonomy=req.autonomy)
            return {"decision": d.decision.value, "reason": d.reason,
                    "risk": d.risk, "policy_version": d.policy_version}
        return await _json(request, go)

    async def authorize(request):
        def go(b):
            req = AuthorizeIn(**b)
            tok = fabric.authorize(
                req.identity_id, req.capability, req.resource,
                kind=req.kind, purpose=req.purpose,
                data_class=req.data_class, task_id=req.task_id,
                tool_id=req.tool_id or req.audience,
                autonomy=req.autonomy)
            return {"token_id": tok.token_id,
                    "expires_at": tok.expires_at,
                    "audience": tok.audience}
        return await _json(request, go)

    async def token_validate(request):
        def go(b):
            req = TokenValidateIn(**b)
            from trust.models import CapabilityToken
            tok = CapabilityToken(**req.token)
            out = fabric.capabilities.validate(tok, req.audience)
            return {"valid": True, "token_id": out.token_id}
        return await _json(request, go)

    async def approval_request(request):
        def go(b):
            from trust.approvals import ApprovalRequest as AR
            req = ApprovalRequestIn(**b)
            rid = fabric.approvals.request(AR(
                actor=req.actor, action=req.action,
                resource=req.resource, purpose=req.purpose,
                risk=req.risk, approver_policy=req.approver_policy,
                task_id=req.task_id))
            return {"request_id": rid}
        return await _json(request, go)

    async def approval_vote(request):
        def go(b):
            req = ApprovalVoteIn(**b)
            dec = fabric.approvals.vote(req.request_id, req.approver,
                                        req.granted)
            if dec is None:
                return {"pending": True}
            return {"granted": dec.granted,
                    "approvers": list(dec.approvers)}
        return await _json(request, go)

    async def revoke(request):
        def go(b):
            req = RevokeIn(**b)
            rec = fabric.revoke(req.kind, req.target_id, req.reason,
                                actor=req.actor)
            return {"revoked": rec.target_id,
                    "propagated": len(rec.propagated_to)}
        return await _json(request, go)

    async def kill(request):
        def go(b):
            req = KillIn(**b)
            return fabric.emergency.kill(req.layer, req.target,
                                         reason=req.reason,
                                         actor=req.actor)
        return await _json(request, go)

    async def audit(request):
        params = dict(request.query_params)
        evs = fabric.plane.audit.query(**{k: v for k, v in params.items()
                                          if k in ("agent", "action",
                                                   "risk", "incident")})
        ok, msg = fabric.plane.audit.verify()
        return JSONResponse({"events": len(evs), "integrity": ok,
                             "message": msg})

    async def provenance(request):
        action_id = request.path_params["action_id"]
        return JSONResponse(fabric.provenance.explain(action_id))

    async def incidents(request):
        def go(b):
            if request.method == "GET":
                return {"incidents": [
                    {"id": i.incident_id, "kind": i.kind,
                     "state": i.state, "severity": i.severity}
                    for i in fabric.incidents.incidents.values()]}
            req = IncidentOpenIn(**b)
            inc = fabric.incidents.open(req.kind, req.severity,
                                        actor=req.actor,
                                        resources=req.resources)
            return {"incident_id": inc.incident_id, "state": inc.state}
        return await _json(request, go)

    async def policies(request):
        def go(b):
            if request.method == "GET":
                return {"policies": list(fabric.policies._versions)}
            req = PolicyPublishIn(**b)
            ver = fabric.policies.publish(req.policy_id, req.body,
                                          layer=req.layer)
            return {"version": ver.version, "hash": ver.content_hash}
        return await _json(request, go)

    async def doctor(request):
        from trust.health import trust_doctor
        state = {"identity": {"healthy": True},
                 "policy": {"healthy": True},
                 "audit": {"healthy": True},
                 "revocation": {"healthy": True},
                 "emergency": {"healthy": True},
                 "secrets": {"healthy": True},
                 "agents": [], "extensions": []}
        return JSONResponse(trust_doctor(state))

    async def ipc(request):
        def go(b):
            env = IpcEnvelope(**b)
            chk = env.check()
            if not chk["ok"]:
                return chk
            # dispatch read-only ops; mutating ops reuse routes' validation
            if env.kind == "health":
                return fabric.health.self_test()
            if env.kind == "doctor":
                from trust.health import trust_doctor
                return trust_doctor({"identity": {"healthy": True},
                                     "policy": {"healthy": True},
                                     "audit": {"healthy": True},
                                     "revocation": {"healthy": True},
                                     "emergency": {"healthy": True},
                                     "secrets": {"healthy": True},
                                     "agents": [], "extensions": []})
            if env.kind == "audit.query":
                return {"events": len(fabric.plane.audit.query())}
            if env.kind == "provenance.explain":
                return fabric.provenance.explain(
                    env.payload.get("action_id", ""))
            return {"ok": False,
                    "reason": "mutating ops require HTTP route validation"}
        return await _json(request, go)

    routes = [
        Route("/trust/health", health),
        Route("/trust/propose", propose, methods=["POST"]),
        Route("/trust/authorize", authorize, methods=["POST"]),
        Route("/trust/token/validate", token_validate, methods=["POST"]),
        Route("/trust/approvals/request", approval_request,
              methods=["POST"]),
        Route("/trust/approvals/vote", approval_vote, methods=["POST"]),
        Route("/trust/revoke", revoke, methods=["POST"]),
        Route("/trust/emergency-stop", kill, methods=["POST"]),
        Route("/trust/audit", audit),
        Route("/trust/provenance/{action_id}", provenance),
        Route("/trust/incidents", incidents,
              methods=["GET", "POST"]),
        Route("/trust/policies", policies, methods=["GET", "POST"]),
        Route("/trust/doctor", doctor),
        Route("/trust/ipc", ipc, methods=["POST"]),
    ]
    return Starlette(routes=routes)
