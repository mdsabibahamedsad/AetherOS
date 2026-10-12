"""Shared fixtures: isolated HOME, API keys, live local gateway server.

Tests run against a REAL HTTP server (uvicorn + httpx over loopback) — the
same ASGI app code as production serve. No mocked transports.
"""

import httpx
import pytest


@pytest.fixture()
def home(tmp_path, monkeypatch):
    import aetheros_data.engine as _em
    old = _em._engine_singleton
    if old is not None:
        try:
            old.close()
        except Exception:
            pass
        _em._engine_singleton = None
    h = tmp_path / "phome"
    h.mkdir()
    monkeypatch.setenv("AETHEROS_HOME", str(h))
    yield h
    cur = _em._engine_singleton
    if cur is not None:
        try:
            cur.close()
        except Exception:
            pass
        _em._engine_singleton = None


@pytest.fixture()
def keypair(home):
    from aetheros_platform.auth import APIKeyManager
    mgr = APIKeyManager()
    created = mgr.create("test-key",
                         ["agents:read", "agents:write", "tasks:read", "tasks:write",
                          "tools:read", "tools:write", "tools:invoke",
                          "skills:read", "skills:write",
                          "memory:read", "memory:write", "artifacts:read",
                          "artifacts:write", "automations:write", "webhooks:write",
                          "a2a:write"],
                         owner="tester")
    return created  # includes display-once api_key


@pytest.fixture()
def app(home, keypair):
    from aetheros_platform.agents import AgentRegistry
    from aetheros_platform.events import WebhookRegistry
    from aetheros_platform.gateway import create_app
    from aetheros_platform.skills import SkillRegistry
    from aetheros_platform.tools import ToolRegistry

    tools = ToolRegistry()
    tools.register(
        {"name": "echo", "version": "1.0.0", "description": "Echo tool.",
         "inputSchema": {"type": "object",
                         "properties": {"text": {"type": "string"}}},
         "outputSchema": {"type": "object"},
         "capabilities": ["artifact.create"], "riskLevel": "LOW",
         "sideEffects": [], "idempotent": True, "timeoutSeconds": 10},
        lambda args: {"echo": args.get("text", "")})
    agents = AgentRegistry()
    skills = SkillRegistry(tools=tools)
    hooks = WebhookRegistry()
    return create_app(agents=agents, tools=tools, skills=skills, webhooks=hooks)


@pytest.fixture()
def live(home, keypair, app):
    """Live gateway on 127.0.0.1:ephemeral. Real HTTP, real streaming."""
    import socket
    import threading
    import time

    import uvicorn

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
                                           log_level="error"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{port}"
    ready = False
    for _ in range(200):
        try:
            if httpx.get(base + "/api/v1/health", timeout=1).status_code == 200:
                ready = True
                break
        except Exception:
            time.sleep(0.05)
    assert ready, "gateway did not start"
    yield base
    server.should_exit = True
    th.join(timeout=15)


def auth_headers(keypair, extra=None):
    h = {"X-API-Key": keypair["api_key"]}
    if extra:
        h.update(extra)
    return h
