"""SDK<->API contract tests: Python sync + async clients against live gateway."""

import asyncio

import httpx
import pytest

from tests.aetheros_platform.conftest import auth_headers


def _manifest(n):
    return {"name": n, "version": "1.0.0", "description": "sdk contract",
            "capabilities": ["artifact.create"]}


def test_python_sync_sdk(live, keypair):
    from aetheros_sdk import Client
    c = Client(live, keypair["api_key"])
    agent = c.create_agent(_manifest("py-sync"))
    assert agent["state"] == "READY"
    result = c.create_task(agent["agentId"], {"capability": "artifact.create"})
    assert result["state"] == "COMPLETED"
    out = c.invoke_tool("echo", {"text": "sdk-hi"}, grants=["artifact.create"])
    assert out["result"] == {"echo": "sdk-hi"}
    mem = c.memory_write("sdk memory")
    assert mem["memory_id"]
    assert c.memory_search("sdk")["items"]
    agents = c.list_agents()
    assert agents["items"]
    c.close()


def test_python_async_sdk(live, keypair):
    from aetheros_sdk import AsyncClient

    async def go():
        c = AsyncClient(live, keypair["api_key"])
        agent = await c.create_agent(_manifest("py-async"))
        assert agent["state"] == "READY"
        result = await c.create_task(agent["agentId"],
                                     {"capability": "artifact.create"})
        assert result["state"] == "COMPLETED"
        await c.aclose()
        return result

    assert asyncio.run(go())["state"] == "COMPLETED"


def test_sdk_surfaces_typed_errors(live, keypair):
    from aetheros_sdk import Client
    from aetheros_sdk.errors import SDKError
    c = Client(live, "aek_wrong")
    with pytest.raises(SDKError) as exc:
        c.list_agents()
    assert exc.value.status == 401
    assert exc.value.category == "AUTHENTICATION_REQUIRED"
    c.close()


def test_sdk_idempotent_create(live, keypair):
    from aetheros_sdk import Client
    c = Client(live, keypair["api_key"])
    a1 = c.create_agent(_manifest("py-idem"))
    a2 = c.create_agent(_manifest("py-idem"))
    assert a1["agentId"] == a2["agentId"]
    c.close()


def test_task_ledger_get_and_cancel(live, keypair):
    """GET /tasks/{id} returns the real stored result; cancel marks it."""
    import httpx
    from tests.aetheros_platform.conftest import auth_headers
    h = auth_headers(keypair)
    with httpx.Client(base_url=live) as c:
        agent = c.post("/api/v1/agents", headers=h,
                       json=_manifest("ledger-agent")).json()
        task = c.post("/api/v1/tasks", headers=h,
                      json={"agent": agent["agentId"],
                            "input": {"capability": "artifact.create"}}).json()
        got = c.get(f"/api/v1/tasks/{task['taskId']}", headers=h)
        assert got.status_code == 200
        assert got.json()["taskId"] == task["taskId"]
        assert got.json()["state"] == "COMPLETED"
        assert c.get("/api/v1/tasks/task_nope", headers=h).status_code == 404
        assert c.post("/api/v1/tasks/task_nope/cancel",
                      headers=h).status_code == 404


def test_tool_upload_disabled_but_validated(live, keypair):
    """Malformed manifests -> 422; well-formed code upload -> honest 403."""
    import httpx
    from tests.aetheros_platform.conftest import auth_headers
    h = auth_headers(keypair)
    with httpx.Client(base_url=live) as c:
        bad = c.post("/api/v1/tools", headers=h,
                     json={"name": "t", "version": "x",
                           "inputSchema": "not-an-object"})
        assert bad.status_code == 422
        good = c.post("/api/v1/tools", headers=h,
                      json={"name": "mytool", "version": "1.0.0",
                            "inputSchema": {"type": "object"}})
        assert good.status_code == 403
        assert good.json()["category"] == "POLICY_DENIED"


def test_python_sdk_resources(live, keypair):
    from aetheros_sdk import Client
    c = Client(live, keypair["api_key"])
    agent = c.create_agent(_manifest("py-res"))
    task = c.create_task(agent["agentId"], {"capability": "artifact.create"})
    assert c.get_task(task["taskId"])["taskId"] == task["taskId"]
    art = c.artifact_create(b"resource-bytes", filename="r.bin")
    assert art["hash"].startswith("sha256:")
    assert c.artifact_get(art["artifactId"]) == b"resource-bytes"
    auto = c.automation_create("sdk-cron", {"type": "manual"})
    assert auto["id"].startswith("job_")
    hook = c.webhook_register("https://example.com/hook", ["TaskCreated"])
    assert hook["id"].startswith("wh_")
    assert c.agent_card()["trust"] == "untrusted"
    c.close()


def test_python_async_sdk_resources(live, keypair):
    from aetheros_sdk import AsyncClient

    async def go():
        c = AsyncClient(live, keypair["api_key"])
        agent = await c.create_agent(_manifest("py-async-res"))
        task = await c.create_task(agent["agentId"],
                                   {"capability": "artifact.create"})
        assert (await c.get_task(task["taskId"]))["state"] == "COMPLETED"
        out = await c.invoke_tool("echo", {"text": "async-hi"},
                                  grants=["artifact.create"])
        assert out["result"] == {"echo": "async-hi"}
        mem = await c.memory_write("async memory")
        assert mem["memory_id"]
        art = await c.artifact_create(b"async-bytes")
        assert art["hash"].startswith("sha256:")
        await c.aclose()

    asyncio.run(go())


def test_webhook_sign_verify_helpers():
    import time
    import uuid
    from aetheros_sdk import verify_webhook
    from aetheros_platform.events import sign_payload
    secret = "s3cr3t"
    body = b'{"type":"TaskCreated"}'
    ts = str(int(time.time()))
    dlv = "dlv_" + uuid.uuid4().hex[:8]
    sig = sign_payload(secret, body, ts, dlv)
    assert verify_webhook(secret, body, ts, dlv, sig) is True
    assert verify_webhook(secret, b"tampered", ts, dlv, sig) is False
    assert verify_webhook(secret, body, str(int(ts) - 1000), dlv, sig) is False
