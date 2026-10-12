"""
Security API routes for the AetherOS Web Dashboard.

Provides FastAPI endpoints that expose the aetheros_security subsystem
to the React frontend. Callers must first call ``register_routes(app)``
from ``web_server.py`` to attach these routes.

Endpoints:
    GET    /api/security/status             — Security system status
    GET    /api/security/permissions         — List permission grants
    GET    /api/security/permissions/categories — Available categories
    GET    /api/security/permissions/stats   — Permission statistics
    POST   /api/security/permissions/grant   — Grant a permission
    POST   /api/security/permissions/revoke  — Revoke a permission
    GET    /api/security/secrets             — List secrets
    POST   /api/security/secrets             — Store a secret
    GET    /api/security/secrets/{name}/reveal — Retrieve a secret
    DELETE /api/security/secrets/{name}      — Delete a secret
    GET    /api/security/audit               — View audit entries
    GET    /api/security/audit/stats         — Audit statistics
    GET    /api/security/audit/export        — Export audit log
    GET    /api/security/threats             — Threat alerts
    GET    /api/security/threats/summary     — Threat summary
    GET    /api/security/sandbox             — List sandboxes
    POST   /api/security/sandbox             — Create sandbox
    DELETE /api/security/sandbox/{name}      — Destroy sandbox
    POST   /api/security/sandbox/{name}/exec — Execute in sandbox
    GET    /api/security/sandbox/stats       — Sandbox statistics
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger(__name__)


def register_routes(app) -> None:
    """Attach all security API routes to the FastAPI *app*.

    Usage in ``web_server.py``::

        from aetheros_cli.web_security_api import register_routes
        register_routes(app)
    """

    # ── Helpers ──────────────────────────────────────────────────────────

    def _get_perm_engine():
        from aetheros_security.permissions import get_permission_engine
        return get_permission_engine()

    def _get_secrets_mgr():
        from aetheros_security.secrets import get_secrets_manager, SecretCategory
        return get_secrets_manager(), SecretCategory

    def _get_audit():
        from aetheros_security.audit import get_audit_logger
        return get_audit_logger()

    def _get_threat():
        from aetheros_security.threat import get_threat_detector
        return get_threat_detector()

    def _get_sandbox():
        from aetheros_security.sandbox import get_sandbox_manager
        return get_sandbox_manager()

    # ── Status ───────────────────────────────────────────────────────────

    @app.get("/api/security/status")
    async def security_status():
        from aetheros_security import get_security_manager, __version__

        sm = get_security_manager()
        engine = _get_perm_engine()
        audit = _get_audit()
        threat = _get_threat()

        return {
            "zero_trust": True,
            "initialized": True,
            "version": __version__,
            "permission_count": engine.get_stats().get("total_grants", 0),
            "threat_alerts": len(threat.get_recent_alerts(limit=5)),
            "audit_entry_count": audit.get_statistics().get("total_entries", 0),
        }

    # ── Permissions ──────────────────────────────────────────────────────

    @app.get("/api/security/permissions")
    async def list_permissions():
        engine = _get_perm_engine()
        grants = engine.get_grants()
        return {
            "grants": [
                {
                    "permission": g.permission,
                    "grantee": g.grantee,
                    "granted_at": g.granted_at,
                    "expires_at": g.expires_at,
                    "duration": g.duration,
                    "reason": g.reason,
                }
                for g in grants
            ],
        }

    @app.get("/api/security/permissions/categories")
    async def permission_categories():
        from aetheros_security import PERMISSION_CATEGORIES

        return {
            "categories": [
                {"category": cat, "actions": actions}
                for cat, actions in PERMISSION_CATEGORIES.items()
            ],
        }

    @app.get("/api/security/permissions/stats")
    async def permission_stats():
        engine = _get_perm_engine()
        return engine.get_stats()

    @app.post("/api/security/permissions/grant")
    async def grant_permission(body: dict[str, Any]):
        engine = _get_perm_engine()
        ok = engine.grant(
            body.get("permission", ""),
            body.get("requester", ""),
            duration=body.get("duration", "session"),
            reason=body.get("reason", ""),
        )
        return {"ok": ok}

    @app.post("/api/security/permissions/revoke")
    async def revoke_permission(body: dict[str, Any]):
        engine = _get_perm_engine()
        ok = engine.revoke(body.get("permission", ""), body.get("requester", ""))
        return {"ok": ok}

    # ── Secrets ──────────────────────────────────────────────────────────

    @app.get("/api/security/secrets")
    async def list_secrets():
        mgr, _ = _get_secrets_mgr()
        secrets_list = mgr.list_secrets()
        return {"secrets": secrets_list}

    @app.post("/api/security/secrets")
    async def store_secret(body: dict[str, Any]):
        mgr, SecretCategory = _get_secrets_mgr()
        cat_map = {
            "api_key": SecretCategory.API_KEY,
            "oauth_token": SecretCategory.OAUTH_TOKEN,
            "ssh_key": SecretCategory.SSH_KEY,
            "jwt_token": SecretCategory.JWT_TOKEN,
            "cookie": SecretCategory.COOKIE,
            "certificate": SecretCategory.CERTIFICATE,
            "password": SecretCategory.PASSWORD,
            "generic": SecretCategory.GENERIC,
        }
        ok = mgr.store(
            body.get("name", ""),
            body.get("value", ""),
            category=cat_map.get(body.get("category", "generic"), SecretCategory.GENERIC),
            description=body.get("description", ""),
        )
        return {"ok": ok}

    @app.get("/api/security/secrets/{name}/reveal")
    async def reveal_secret(name: str):
        mgr, _ = _get_secrets_mgr()
        value = mgr.retrieve(name)
        if value is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Secret not found or expired")
        return {"value": value}

    @app.delete("/api/security/secrets/{name}")
    async def delete_secret(name: str):
        mgr, _ = _get_secrets_mgr()
        ok = mgr.delete(name)
        return {"ok": ok}

    # ── Audit Log ────────────────────────────────────────────────────────

    @app.get("/api/security/audit")
    async def audit_log(limit: int = 100, severity: str = None, event_type: str = None, user: str = None):
        audit = _get_audit()
        entries = audit.get_recent(limit=limit)
        if severity:
            entries = [e for e in entries if e.get("severity") == severity]
        if event_type:
            entries = [e for e in entries if e.get("event_type") == event_type]
        if user:
            entries = [e for e in entries if e.get("user") == user]
        return {"entries": entries}

    @app.get("/api/security/audit/stats")
    async def audit_stats():
        audit = _get_audit()
        return audit.get_statistics()

    @app.get("/api/security/audit/export")
    async def audit_export():
        audit = _get_audit()
        # mkstemp: platform-correct temp path (no hardcoded /tmp, which breaks
        # on Windows) and 0600 permissions so the exported audit never sits
        # world-readable on disk.
        fd, export_path = tempfile.mkstemp(prefix="aetheros_audit_", suffix=".json")
        os.close(fd)
        ok = audit.export(export_path)
        return {"url": export_path, "ok": ok}

    # ── Threat Detection ─────────────────────────────────────────────────

    @app.get("/api/security/threats")
    async def threat_alerts(limit: int = 50):
        threat = _get_threat()
        threat.analyze_activity()  # Refresh analysis
        return {"alerts": threat.get_recent_alerts(limit=limit)}

    @app.get("/api/security/threats/summary")
    async def threat_summary():
        threat = _get_threat()
        return threat.get_threat_summary()

    # ── Sandbox ──────────────────────────────────────────────────────────

    @app.get("/api/security/sandbox")
    async def list_sandboxes():
        mgr = _get_sandbox()
        return {"sandboxes": mgr.list_sandboxes()}

    @app.post("/api/security/sandbox")
    async def create_sandbox(body: dict[str, Any]):
        from aetheros_security.sandbox import SandboxConfig, SandboxBackend, SandboxMode

        backend_map = {
            "firejail": SandboxBackend.FIREJAIL,
            "docker": SandboxBackend.DOCKER,
            "podman": SandboxBackend.PODMAN,
            "restricted_python": SandboxBackend.RESTRICTED_PYTHON,
            "none": SandboxBackend.NONE,
        }
        mode_map = {
            "full": SandboxMode.FULL,
            "standard": SandboxMode.STANDARD,
            "relaxed": SandboxMode.RELAXED,
            "none": SandboxMode.NONE,
        }
        mgr = _get_sandbox()
        config = SandboxConfig(
            name=body.get("name", ""),
            backend=backend_map.get(body.get("backend", "restricted_python"), SandboxBackend.RESTRICTED_PYTHON),
            mode=mode_map.get(body.get("mode", "standard"), SandboxMode.STANDARD),
            network_access=body.get("network", False),
        )
        mgr.create_sandbox(config)
        return {"ok": True}

    @app.delete("/api/security/sandbox/{name}")
    async def destroy_sandbox(name: str):
        mgr = _get_sandbox()
        ok = mgr.destroy_sandbox(name)
        return {"ok": ok}

    @app.post("/api/security/sandbox/{name}/exec")
    async def exec_sandbox(name: str, body: dict[str, Any]):
        mgr = _get_sandbox()
        sb = mgr.get_sandbox(name)
        if not sb:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Sandbox not found")
        sb.enter()
        try:
            result = sb.execute(body.get("command", ""), timeout=body.get("timeout"))
            return {
                "output": result.output,
                "error": result.error,
                "exit_code": result.exit_code,
                "success": result.success,
            }
        finally:
            sb.exit()

    @app.get("/api/security/sandbox/stats")
    async def sandbox_stats():
        mgr = _get_sandbox()
        return mgr.get_stats()

    logger.info("Registered %d security API routes", 18)
