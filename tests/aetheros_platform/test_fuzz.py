"""Fuzzing: schemas, manifests, API inputs, tool args, packages, events,
Agent Cards, MCP responses, A2A messages (Master 62 §70). No crash may escape
as an unhandled exception or a secret-leaking 500; worst case is a typed
4xx/validation error."""

import itertools
import json
import random
import string

import pytest

WEIRD = ["", " ", "\x00", "../..", "{{", "[]", "null", "None",
         "A" * 5000, "\u202e", "${jndi:ldap://x}", "<script>",
         "'; DROP TABLE x;--", "%s%s%s", "\n\r\t", "🔥",
         "-1", "99999999999999999999", "true", "True", "NaN", "Infinity"]


def _rand(rng, pool):
    return rng.choice(pool)


def test_fuzz_schema_validation_never_crashes():
    from aetheros_platform.schemas import SCHEMAS, validate
    rng = random.Random(62)
    checked = 0
    for name in ("Agent", "Tool", "Skill", "AgentCard", "MCPServer",
                 "Automation", "MemoryRecord", "APIKey", "Webhook", "Package"):
        for _ in range(60):
            payload = {rng.choice(["name", "version", "x", ""]) + str(rng.randint(0, 3)):
                       _rand(rng, WEIRD) for _ in range(rng.randint(0, 5))}
            errors = validate(name, payload)
            assert isinstance(errors, list)
            checked += 1
    assert checked == 600


def test_fuzz_gateway_inputs(live, keypair):
    import httpx
    rng = random.Random(63)
    h = {"X-API-Key": keypair["api_key"]}
    bad_paths = ["/api/v1/agents", "/api/v1/tasks", "/api/v1/skills",
                 "/api/v1/memory/records", "/api/v1/automations",
                 "/api/v1/webhooks", "/api/v1/a2a/tasks"]
    with httpx.Client(base_url=live) as c:
        for i in range(120):
            path = rng.choice(bad_paths)
            body = {"name": _rand(rng, WEIRD), "version": _rand(rng, WEIRD),
                    "extra": _rand(rng, WEIRD)}
            r = c.post(path, headers=h, json=body)
            assert r.status_code in (400, 401, 403, 404, 409, 410, 422, 429), (
                path, r.status_code, r.text[:200])
            if r.status_code not in (429,):
                assert "traceback" not in r.text.lower()
                assert "aek_" not in r.text  # no secret echo


def test_fuzz_tool_args_contained():
    from aetheros_platform.errors import AetherError
    from aetheros_platform.tools import ToolRegistry
    tools = ToolRegistry()
    tools.register({"name": "fuzz", "version": "1.0.0",
                    "inputSchema": {"type": "object",
                                    "properties": {"text": {"type": "string"}}},
                    "outputSchema": {"type": "object"},
                    "capabilities": ["artifact.create"], "riskLevel": "LOW",
                    "sideEffects": [], "idempotent": True, "timeoutSeconds": 5},
                   lambda a: {"ok": True})
    rng = random.Random(64)
    for _ in range(100):
        args = {"text": _rand(rng, WEIRD)}
        try:
            tools.invoke("fuzz", args, actor="fuzz", grants=["artifact.create"])
        except AetherError:
            pass
        except Exception as exc:
            pytest.fail(f"untyped exception escaped: {type(exc).__name__}: {exc}")


def test_fuzz_agent_cards_and_a2a():
    from aetheros_platform.a2a import TASKS, validate_card
    rng = random.Random(65)
    for _ in range(100):
        card = {"name": _rand(rng, WEIRD), "version": _rand(rng, WEIRD),
                "protocolVersion": _rand(rng, WEIRD),
                "capabilities": [_rand(rng, WEIRD)]}
        assert isinstance(validate_card(card), list)
    for _ in range(50):
        msg = _rand(rng, WEIRD)
        if not msg:
            continue
        task = TASKS.create(msg, sender="fuzz")
        assert task["state"] == "completed"
