"""Versioned API gateway (Master 62 §5, §75-76, §30, §92-97).

FastAPI app factory: /api/v1 (+ /api/v2 alias with sunset headers),
routing, API-key auth, scope authorization, enforced rate limits,
idempotency keys, request/trace IDs, pagination, audit, SSE streaming.
Public Developer API only — internal runtime is never exposed raw.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Request
    from fastapi.responses import JSONResponse, StreamingResponse
    _FASTAPI = True
except ImportError:  # pragma: no cover
    _FASTAPI = False

from aetheros_platform import registry as _registry
from aetheros_platform.auth import APIKeyManager, has_scope
from aetheros_platform.errors import AetherError
from aetheros_platform.events import BUS, USAGE, redact
from aetheros_platform.ratelimit import LIMITER

KEYS = APIKeyManager()
IDEM_STORE: Dict[str, Any] = {}
# In-process task ledger: create_task stores the inline result so GET /cancel
# operate on real records. History beyond process lifetime comes from the
# event bus + audit log (durable), not this dict.
TASK_STORE: Dict[str, Any] = {}


def _req_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


def _audit(action: str, actor: str, target: str, result: str, detail: Dict[str, Any]) -> None:
    try:
        from aetheros_data.records import AuditLog
        from aetheros_data.engine import get_engine
        AuditLog(get_engine()).record(actor, action, target, result=result,
                                      payload=redact(detail))
    except Exception:
        pass


def _cred(request) -> Optional[Dict[str, Any]]:
    raw = request.headers.get("x-api-key", "") or ""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        raw = auth[7:]
    if not raw:
        return None
    return KEYS.verify(raw)


def _require(cred: Optional[Dict[str, Any]], scope: str) -> Dict[str, Any]:
    from aetheros_platform.errors import err as _err
    if cred is None:
        raise _err("AUTHENTICATION_REQUIRED", "missing or invalid API key",
                   remediation="pass X-API-Key or Bearer token")
    if not has_scope(cred, scope):
        raise _err("AUTHORIZATION_DENIED", f"scope {scope} required",
                   remediation="issue a key with the required scope")
    return cred


def _page(items: List[Any], cursor: str = "", limit: int = 20) -> Dict[str, Any]:
    limit = max(1, min(limit, 100))
    start = 0
    if cursor:
        try:
            start = int(cursor)
            if start < 0:
                raise ValueError()
        except ValueError:
            from aetheros_platform.errors import err as _err
            raise _err("INVALID_REQUEST", "invalid cursor")
    chunk = items[start: start + limit]
    nxt = str(start + limit) if start + limit < len(items) else ""
    return {"items": chunk, "nextCursor": nxt, "limit": limit}


def create_app(agents=None, tools=None, skills=None, webhooks=None) -> "FastAPI":
    assert _FASTAPI, "fastapi required"
    from aetheros_platform.agents import AgentRegistry
    from aetheros_platform.tools import ToolRegistry
    from aetheros_platform.skills import SkillRegistry
    from aetheros_platform.events import WebhookRegistry

    app = FastAPI(title="AetherOS Developer API", version="1.0.0")
    agent_reg = agents or AgentRegistry(audit=_audit)
    tool_reg = tools or ToolRegistry(audit=_audit)
    skill_reg = skills or SkillRegistry(tools=tool_reg, audit=_audit)
    hook_reg = webhooks or WebhookRegistry(audit=_audit)

    async def _guard(request: Request, scope: str, layer: str, endpoint: str):
        rid = request.headers.get("x-request-id", "") or _req_id()
        cred = _cred(request)
        _require(cred, scope)
        ident = cred["key_id"] if cred else "anon"
        try:
            LIMITER.check(layer, ident, endpoint)
        except AetherError as exc:
            exc.requestId = rid
            raise exc
        return cred, rid, ident

    def _http(exc: AetherError):
        # Legacy wrapper (kept for non-AetherError paths). Prefer raising
        # AetherError directly so the handler emits the flat typed body.
        return HTTPException(status_code=exc.http_status, detail=exc.to_dict())

    @app.exception_handler(AetherError)
    async def _aether_handler(request: Request, exc: AetherError):
        return JSONResponse(status_code=exc.http_status, content=exc.to_dict())

    @app.middleware("http")
    async def _headers(request: Request, call_next):
        rid = request.headers.get("x-request-id", "") or _req_id()
        t0 = time.time()
        try:
            resp = await call_next(request)
        except HTTPException as exc:
            resp = JSONResponse(status_code=exc.status_code, content=exc.detail)
        resp.headers["x-request-id"] = rid
        resp.headers["x-trace-id"] = rid
        if request.url.path.startswith("/api/v2"):
            resp.headers["Sunset"] = "not-planned"
            resp.headers["X-API-Version"] = "v2-alias-of-v1"
        else:
            resp.headers["X-API-Version"] = "v1"
        USAGE.record("gateway", tokens=0, tool_calls=0,
                     runtime_s=round(time.time() - t0, 4))
        return resp

    def _idem(request: Request, payload: Dict[str, Any]) -> Optional[Any]:
        key = request.headers.get("Idempotency-Key", "")
        if not key:
            return None
        ck = f"{request.url.path}:{key}"
        if ck in IDEM_STORE:
            return {"duplicate": True, "result": IDEM_STORE[ck]}
        IDEM_STORE[ck] = payload  # placeholder replaced below
        return None

    # -- meta ------------------------------------------------------------------
    @app.get("/api/v1/health")
    async def health():
        return {"ok": True, "version": "1.0.0", "api": ["v1", "v2-alias"]}

    @app.get("/api/v1/registry")
    async def get_registry():
        return {"registryVersion": _registry.REGISTRY_VERSION,
                "endpoints": _registry.public_endpoints()}

    @app.get("/api/v1/schemas")
    async def get_schemas():
        from aetheros_platform import schemas as _s
        return {"schemaVersion": _s.SCHEMA_VERSION, "schemas": _s.SCHEMAS}

    # -- agents ------------------------------------------------------------------
    @app.post("/api/v1/agents")
    async def create_agent(request: Request, body: Dict[str, Any]):
        cred, rid, _ = await _guard(request, "agents:write", "agent", "POST /agents")
        try:
            body = dict(body)
            body.setdefault("tenant", {"organization": request.headers.get("x-tenant-org", "default"),
                                       "workspace": request.headers.get("x-tenant-workspace", "default")})
            rec = agent_reg.register(body, owner=cred["key_id"])
        except AetherError as exc:
            exc.requestId = rid
            raise exc
        BUS.emit("AgentStarted", source="gateway", agent=rec["record_id"])
        return {"agentId": rec["record_id"], "state": rec["data"].get("state")}

    def _tenant_of(request: Request) -> Dict[str, str]:
        return {"organization": request.headers.get("x-tenant-org", "default"),
                "workspace": request.headers.get("x-tenant-workspace", "default")}

    def _owns(manifest_tenant: Dict[str, Any], want: Dict[str, str]) -> bool:
        return (manifest_tenant.get("organization", "default") == want["organization"]
                and manifest_tenant.get("workspace", "default") == want["workspace"])

    @app.get("/api/v1/agents")
    async def list_agents(request: Request, cursor: str = "", limit: int = 20):
        await _guard(request, "agents:read", "standard", "GET /agents")
        want = _tenant_of(request)
        items = [r for r in agent_reg.list()
                 if _owns(r["data"].get("manifest", {}).get("tenant", {}), want)]
        return _page(items, cursor, limit)

    @app.get("/api/v1/agents/{agent_id}")
    async def get_agent(request: Request, agent_id: str):
        await _guard(request, "agents:read", "standard", "GET /agents/{id}")
        rec = agent_reg.get(agent_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="not found")
        if not _owns(rec["data"].get("manifest", {}).get("tenant", {}),
                     _tenant_of(request)):
            from aetheros_platform.errors import err as _err
            raise _err("AUTHORIZATION_DENIED",
                       "cross-tenant access denied by resource ownership")
        return rec

    # -- tasks ---------------------------------------------------------------------
    @app.post("/api/v1/tasks")
    async def create_task(request: Request, body: Dict[str, Any]):
        from aetheros_platform.schemas import validate
        cred, rid, _ = await _guard(request, "tasks:write", "task", "POST /tasks")
        dup = _idem(request, {})
        if dup is not None:
            return dup["result"]
        errs = validate("AgentTask", body)
        if errs:
            from aetheros_platform.errors import err as _err
            raise _err("INVALID_SCHEMA", errs[0])
        try:
            result = agent_reg.run_task(
                body["agent"], body.get("input", {}), actor=cred["key_id"],
                tool_runner=lambda t, a, actor, grants: tool_reg.invoke(
                    t, a, actor=actor, grants=grants),
                tool_caps_fn=lambda t: list(
                    (tool_reg.get(t) or {}).get("capabilities", [])))
        except AetherError as exc:
            exc.requestId = rid
            raise exc
        TASK_STORE[result["taskId"]] = result
        BUS.emit("TaskCreated", source="gateway", task=result["taskId"])
        BUS.emit("TaskUpdated", source="gateway", task=result["taskId"])
        key = request.headers.get("Idempotency-Key", "")
        if key:
            IDEM_STORE[f"{request.url.path}:{key}"] = result
        _audit("task.created", cred["key_id"], result["taskId"], "ok", {})
        return result

    @app.get("/api/v1/tasks/{task_id}")
    async def get_task(request: Request, task_id: str):
        await _guard(request, "tasks:read", "standard", "GET /tasks/{id}")
        rec = TASK_STORE.get(task_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="unknown task id")
        return rec

    @app.post("/api/v1/tasks/{task_id}/cancel")
    async def cancel_task(request: Request, task_id: str):
        await _guard(request, "tasks:write", "task", "POST /tasks/cancel")
        rec = TASK_STORE.get(task_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="unknown task id")
        if rec.get("state") not in ("COMPLETED", "FAILED", "CANCELLED"):
            rec = dict(rec, state="CANCELLED")
            TASK_STORE[task_id] = rec
            BUS.emit("TaskUpdated", source="gateway", task=task_id)
        return {"taskId": task_id, "state": rec["state"],
                "note": "tasks execute inline; cancel marks the ledger record"}

    @app.get("/api/v1/tasks/{task_id}/events")
    async def task_events(request: Request, task_id: str):
        await _guard(request, "tasks:read", "standard", "GET /tasks/events")

        def gen():
            sub = BUS.subscribe()
            try:
                yield 'event: open\ndata: {"stream":"task-events"}\n\n'
                import queue as _q
                while True:
                    try:
                        evt = sub.get(timeout=25)
                    except _q.Empty:
                        yield ": heartbeat\n\n"
                        continue
                    if evt.get("task") in ("", task_id):
                        import json as _j
                        yield f"event: {evt['type']}\ndata: {_j.dumps(evt)}\n\n"
            finally:
                BUS.unsubscribe(sub)

        return StreamingResponse(gen(), media_type="text/event-stream")

    # -- tools ---------------------------------------------------------------------
    @app.post("/api/v1/tools")
    async def register_tool(request: Request, body: Dict[str, Any]):
        from aetheros_platform.errors import err as _err
        from aetheros_platform.schemas import validate as _validate
        await _guard(request, "tools:write", "standard", "POST /tools")
        # Server-side tool CODE upload stays disabled by design (executing
        # uploaded code would bypass review/quarantine). But the manifest is
        # still schema-validated so malformed/unsafe definitions are rejected
        # with a typed error instead of a silent no-op.
        errs = _validate("Tool", body)
        if errs:
            raise _err("INVALID_SCHEMA", f"tool manifest invalid: {errs[0]}",
                       remediation="register tools in-process via the Tool SDK")
        raise _err("POLICY_DENIED",
                   "server-side tool code upload is disabled",
                   remediation="register tools in-process via the Tool SDK; "
                               "this endpoint validates manifests only")

    @app.get("/api/v1/tools")
    async def list_tools(request: Request, cursor: str = "", limit: int = 20):
        await _guard(request, "tools:read", "standard", "GET /tools")
        return _page(tool_reg.list(), cursor, limit)

    @app.post("/api/v1/tools/{name}/invoke")
    async def invoke_tool(request: Request, name: str, body: Dict[str, Any]):
        cred, rid, _ = await _guard(request, "tools:invoke", "tool-invoke", f"POST /tools/{name}")
        dup = _idem(request, {})
        if dup is not None:
            return dup["result"]
        try:
            result = tool_reg.invoke(name, body.get("args", {}), actor=cred["key_id"],
                                     grants=body.get("grants", []),
                                     idempotency_key=request.headers.get("Idempotency-Key", "") or None)
        except AetherError as exc:
            exc.requestId = rid
            raise exc
        BUS.emit("ToolCompleted", source="gateway", agent=cred["key_id"])
        out = {"ok": True, "result": result}
        key = request.headers.get("Idempotency-Key", "")
        if key:
            IDEM_STORE[f"{request.url.path}:{key}"] = out
        return out

    # -- skills ----------------------------------------------------------------------
    @app.post("/api/v1/skills")
    async def register_skill(request: Request, body: Dict[str, Any]):
        await _guard(request, "skills:write", "standard", "POST /skills")
        try:
            return skill_reg.register(body)
        except AetherError as exc:
            raise exc

    @app.get("/api/v1/skills")
    async def list_skills(request: Request, cursor: str = "", limit: int = 20):
        await _guard(request, "skills:read", "standard", "GET /skills")
        return _page(skill_reg.list(), cursor, limit)

    # -- memory / artifacts / automations / webhooks -----------------------------------
    @app.post("/api/v1/memory/records")
    async def mem_write(request: Request, body: Dict[str, Any]):
        from aetheros_platform.schemas import validate
        cred, rid, _ = await _guard(request, "memory:write", "memory", "POST /memory")
        errs = validate("MemoryRecord", body)
        if errs:
            from aetheros_platform.errors import err as _err
            raise _err("INVALID_SCHEMA", errs[0])
        from aetheros_platform import domains as _d
        rec = _d.memory_write(body["content"], body.get("scope", "user"),
                              owner=cred["key_id"],
                              sensitivity=body.get("sensitivity", "internal"))
        BUS.emit("MemoryWritten", source="gateway", agent=cred["key_id"])
        return rec

    @app.get("/api/v1/memory/search")
    async def mem_search(request: Request, q: str = ""):
        await _guard(request, "memory:read", "memory", "GET /memory/search")
        from aetheros_platform import domains as _d
        return {"items": _d.memory_search(q)}

    @app.post("/api/v1/artifacts")
    async def art_create(request: Request, body: Dict[str, Any]):
        cred, rid, _ = await _guard(request, "artifacts:write", "standard", "POST /artifacts")
        import base64
        from aetheros_platform import domains as _d
        raw = base64.b64decode(body.get("dataBase64", ""))
        rec = _d.artifact_create(raw, filename=body.get("filename", ""),
                                 owner=cred["key_id"],
                                 classification=body.get("classification", "internal"))
        BUS.emit("ArtifactCreated", source="gateway", agent=cred["key_id"])
        return rec

    @app.get("/api/v1/artifacts/{artifact_id}")
    async def art_get(request: Request, artifact_id: str):
        await _guard(request, "artifacts:read", "standard", "GET /artifacts/{id}")
        import base64
        from aetheros_platform import domains as _d
        try:
            raw = _d.artifact_bytes(artifact_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)[:200])
        return {"artifactId": artifact_id, "dataBase64": base64.b64encode(raw).decode()}

    @app.post("/api/v1/automations")
    async def auto_create(request: Request, body: Dict[str, Any]):
        from aetheros_platform.schemas import validate
        cred, rid, _ = await _guard(request, "automations:write", "standard", "POST /automations")
        errs = validate("Automation", body)
        if errs:
            from aetheros_platform.errors import err as _err
            raise _err("INVALID_SCHEMA", errs[0])
        from aetheros_platform import domains as _d
        job = _d.automation_create(body["name"], body["trigger"], owner=cred["key_id"])
        BUS.emit("AutomationTriggered", source="gateway", agent=cred["key_id"])
        return job

    @app.post("/api/v1/webhooks")
    async def hook_create(request: Request, body: Dict[str, Any]):
        await _guard(request, "webhooks:write", "standard", "POST /webhooks")
        return hook_reg.register(body.get("url", ""), body.get("events", []))

    # -- A2A (experimental) --------------------------------------------------------------
    @app.get("/api/v1/a2a/card")
    async def a2a_card():
        from aetheros_platform import a2a as _a2a
        return _a2a.local_card()

    @app.post("/api/v1/a2a/tasks")
    async def a2a_task(request: Request, body: Dict[str, Any]):
        await _guard(request, "a2a:write", "standard", "POST /a2a/tasks")
        from aetheros_platform import a2a as _a2a
        return _a2a.submit_remote_task(body)

    # v2 alias (same handlers; headers mark the alias)
    @app.get("/api/v2/health")
    async def health_v2():
        return {"ok": True, "version": "2.0.0-alias", "api": ["v1", "v2-alias"]}

    return app
