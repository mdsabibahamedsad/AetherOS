"""Schema + registry + error contract tests (Master 62 §6, §4, §7, §47)."""

import json
import subprocess

import pytest


def test_all_public_schemas_validate():
    from aetheros_platform.schemas import SCHEMAS, validate
    assert len(SCHEMAS) >= 28
    assert validate("Agent", {"name": "x", "version": "1.0.0"}) == []
    assert validate("Agent", {"name": "BAD NAME!", "version": "1.0"}) != []
    assert validate("Tool", {"name": "t", "version": "1.0.0",
                             "inputSchema": {"type": "object"}}) == []
    assert validate("Nope", {}) != []


def test_error_taxonomy_complete():
    from aetheros_platform.errors import AetherError, CATEGORIES, HTTP_STATUS, err
    assert len(CATEGORIES) == 25
    for cat in CATEGORIES:
        e = err(cat, "msg")
        assert e.http_status == HTTP_STATUS[cat]
    e = err("RATE_LIMITED", "slow down")
    assert e.retryable is True
    e2 = err("POLICY_DENIED", "no")
    assert e2.retryable is False


def test_registry_shape():
    from aetheros_platform.registry import ENDPOINTS, V2_ALIAS, public_endpoints
    required = {"endpoint", "version", "stability", "authentication",
                "authorization", "scopes", "rateLimit", "inputSchema",
                "outputSchema", "streaming", "idempotency", "auditPolicy",
                "dataClassification", "deprecationPolicy"}
    for ep in ENDPOINTS:
        assert required <= set(ep), ep
        assert ep["stability"] in ("PUBLIC", "INTERNAL", "EXPERIMENTAL",
                                   "DEPRECATED", "PRIVATE", "UNSTABLE")
    assert len(public_endpoints()) == len(ENDPOINTS)
    assert V2_ALIAS["stability"] == "PUBLIC"


def test_ts_generated_matches_schemas():
    """generated.ts is byte-identical to tsgen output (no hand drift)."""
    from pathlib import Path
    from aetheros_platform import tsgen
    gen_path = Path("sdks/typescript/src/generated.ts")
    assert gen_path.exists()
    assert gen_path.read_text(encoding="utf-8").replace("\r\n", "\n") == tsgen.generate()
