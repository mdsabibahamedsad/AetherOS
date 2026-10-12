"""Gateway E2E: full developer lifecycle through the real HTTP stack (§82, §105).

Developer -> SDK-less HTTP -> Gateway -> Auth -> Scope -> Intent -> Policy ->
Agent -> Tool -> Artifact/Event/Audit. Uses a live local server (same app
code as production serve). No mocked transports.
"""

import threading
import time

import httpx
import pytest

from tests.aetheros_platform.conftest import auth_headers


def _manifest(n):
    return {"name": n, "version": "1.0.0", "description": "e2e",
            "capabilities": ["artifact.create", "memory.read"]}


def test_full_lifecycle(live, keypair):
    h = auth_headers(keypair)
    with httpx.Client(base_url=live) as c:
        # health / registry / schemas are public
        assert c.get("/api/v1/health").json()["ok"] is True
        assert len(c.get("/api/v1/registry").json()["endpoints"]) >= 20
        assert c.get("/api/v1/schemas").json()["schemaVersion"] == "1.0.0"

        # 3. declared capabilities; 4. policy evaluates at run
        agent = c.post("/api/v1/agents", headers=h, json=_manifest("e2e-agent")).json()
        assert agent["state"] == "READY"

        # 5. real tool invocation; 6. audited; 7. result to caller
        invoked = c.post("/api/v1/tools/echo/invoke", headers=h,
                         json={"args": {"text": "hi"}, "grants": ["artifact.create"]}).json()
        assert invoked["result"] == {"echo": "hi"}

        # task runs intent->policy->tool
        task = c.post("/api/v1/tasks", headers=h,
                      json={"agent": agent["agentId"],
                            "input": {"capability": "artifact.create", "tool": "echo",
                                      "args": {"text": "via-task"}}}).json()
        assert task["state"] == "COMPLETED"
        assert task["output"]["tool_result"] == {"echo": "via-task"}

        # 8. events observable; 9. artifacts retrievable
        import base64
        art = c.post("/api/v1/artifacts", headers=h,
                     json={"dataBase64": base64.b64encode(b"report").decode(),
                           "filename": "r.txt"}).json()
        assert art["hash"].startswith("sha256:")
        got = c.get(f"/api/v1/artifacts/{art['artifactId']}", headers=h).json()
        assert base64.b64decode(got["dataBase64"]) == b"report"

        # memory + automation + webhook + A2A card
        mem = c.post("/api/v1/memory/records", headers=h,
                     json={"content": "e2e memory"}).json()
        assert mem["memory_id"]
        assert c.get("/api/v1/memory/search?q=e2e", headers=h).json()["items"]
        auto = c.post("/api/v1/automations", headers=h,
                      json={"name": "e2e-cron", "trigger": {"type": "manual"}}).json()
        assert auto["id"].startswith("job_")
        card = c.get("/api/v1/a2a/card").json()
        assert card["trust"] == "untrusted"
        a2a = c.post("/api/v1/a2a/tasks", headers=h,
                     json={"message": "hello", "idempotencyKey": "e2e-a2a-1"}).json()
        assert a2a["state"] == "completed"

        # version headers + request ids on every response
        r = c.get("/api/v1/health")
        assert r.headers["x-request-id"] and r.headers["x-trace-id"]
        assert r.headers["x-api-version"] == "v1"
        r2 = c.get("/api/v2/health")
        assert r2.headers["x-api-version"] == "v2-alias-of-v1"
        assert "Sunset" in r2.headers


def test_auth_enforced(live, keypair):
    with httpx.Client(base_url=live) as c:
        r = c.post("/api/v1/agents", json=_manifest("nope"))
        assert r.status_code == 401
        assert r.json()["category"] == "AUTHENTICATION_REQUIRED"
        r = c.post("/api/v1/agents", headers={"X-API-Key": "aek_invalid"},
                   json=_manifest("nope"))
        assert r.status_code == 401


def test_scope_enforced(live, home):
    from aetheros_platform.auth import APIKeyManager
    mgr = APIKeyManager()
    narrow = mgr.create("narrow", ["agents:read"], owner="t")
    with httpx.Client(base_url=live) as c:
        r = c.post("/api/v1/agents", headers={"X-API-Key": narrow["api_key"]},
                   json=_manifest("denied"))
        assert r.status_code == 403
        assert r.json()["category"] == "AUTHORIZATION_DENIED"


def test_revoked_and_expired_rejected(live, home):
    import sqlite3
    import time as _t
    from aetheros_data.engine import get_engine
    from aetheros_platform.auth import APIKeyManager
    mgr = APIKeyManager()
    k = mgr.create("doomed", ["agents:read"], owner="t")
    assert mgr.revoke(k["key_id"]) is True
    with httpx.Client(base_url=live) as c:
        assert c.get("/api/v1/agents",
                     headers={"X-API-Key": k["api_key"]}).status_code == 401
    k2 = mgr.create("old", ["agents:read"], owner="t")
    eng = get_engine()
    conn = sqlite3.connect(str(eng.db_path))
    conn.execute("UPDATE api_keys SET expires_at=? WHERE key_id=?",
                 (_t.time() - 10, k2["key_id"]))
    conn.commit()
    conn.close()
    with httpx.Client(base_url=live) as c:
        assert c.get("/api/v1/agents",
                     headers={"X-API-Key": k2["api_key"]}).status_code == 401


def test_plaintext_keys_never_listed(live, keypair):
    with httpx.Client(base_url=live) as c:
        from aetheros_platform.auth import APIKeyManager
        for row in APIKeyManager().list():
            assert "api_key" not in row
            assert "key_hash" not in row


def test_rate_limit_enforced(live, keypair):
    h = auth_headers(keypair)
    seen_429 = False
    with httpx.Client(base_url=live) as c:
        for _ in range(80):
            r = c.get("/api/v1/agents?limit=1", headers=h)
            if r.status_code == 429:
                body = r.json()
                assert body["category"] == "RATE_LIMITED"
                assert body["metadata"]["retry_after"] >= 0
                seen_429 = True
                break
    assert seen_429, "burst of 80 must trip the 60-burst bucket"


def test_idempotent_task_create(live, keypair):
    h = dict(auth_headers(keypair), **{"Idempotency-Key": "idem-e2e-1"})
    with httpx.Client(base_url=live) as c:
        agent = c.post("/api/v1/agents", headers=auth_headers(keypair),
                       json=_manifest("idem-agent")).json()
        t1 = c.post("/api/v1/tasks", headers=h,
                    json={"agent": agent["agentId"],
                          "input": {"capability": "artifact.create"}}).json()
        t2 = c.post("/api/v1/tasks", headers=h,
                    json={"agent": agent["agentId"],
                          "input": {"capability": "artifact.create"}}).json()
        assert t1["taskId"] == t2["taskId"]


def test_pagination_and_bad_cursor(live, keypair):
    h = auth_headers(keypair)
    with httpx.Client(base_url=live) as c:
        p1 = c.get("/api/v1/agents?limit=1", headers=h).json()
        assert p1["limit"] == 1 and "nextCursor" in p1
        bad = c.get("/api/v1/agents?cursor=nope", headers=h)
        assert bad.status_code == 400


def test_sse_receives_real_events(live, keypair):
    """Real streaming (not polling): open SSE, trigger task, receive frames."""
    h = auth_headers(keypair)
    got = []

    def listen():
        with httpx.Client(base_url=live, timeout=15) as c:
            with c.stream("GET", "/api/v1/tasks/t-sse/events", headers=h) as r:
                assert r.status_code == 200
                for line in r.iter_lines():
                    if line.startswith("data:"):
                        got.append(line)
                        if len(got) >= 2:
                            return

    th = threading.Thread(target=listen, daemon=True)
    th.start()
    time.sleep(0.5)
    with httpx.Client(base_url=live) as c:
        agent = c.post("/api/v1/agents", headers=h, json=_manifest("sse-agent")).json()
        c.post("/api/v1/tasks", headers=h,
               json={"agent": agent["agentId"],
                     "input": {"capability": "artifact.create"}})
    th.join(timeout=20)
    assert len(got) >= 2, got
