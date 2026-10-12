"""Tests for aetheros_cli.web_security_api routes (dashboard security API)."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aetheros_cli.web_security_api import register_routes


def _make_client():
    app = FastAPI()
    register_routes(app)
    return TestClient(app)


def test_audit_export_uses_platform_tempdir_not_hardcoded_tmp():
    """The audit export must not hardcode /tmp (broken on Windows) and the
    exported file must actually exist after the route runs."""
    client = _make_client()
    resp = client.get("/api/security/audit/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    export_path = data["url"]
    assert "/tmp/" not in export_path.replace("\\", "/")
    assert Path(export_path).is_file()
