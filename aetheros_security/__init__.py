"""
AetherOS Security OS
====================

Zero Trust Security Framework for AetherOS.

Architecture::

    aetheros_security/
        __init__.py          Package exports and version
        permissions/         Granular permission engine
        sandbox/             Secure sandbox execution
        secrets/             Secrets management (OS secure storage + vault)
        encryption/          Authenticated encryption (AES-GCM)
        ai_security/         AI-specific security
        audit/               Audit logging
        threat/              Threat detection
        rate_limit/          Rate limiting
        authentication/      Authentication (local, passwordless, OAuth, device, biometric)
        session/             Session management (signed, expiring, renewable)
        policy/              Declarative policy loading/validation
        privacy/             Privacy controls (offline, telemetry opt-in, export/delete)
        network/             Network security policy
        supply_chain/        Dependency/SBOM/signature verification
        dlp/                 Data loss prevention
        classification/      Data classification + flow control (R0-R4 context)
        budget/              Resource budgets + recursion limits
        kill_switch/         Named kill switches + safe shutdown
        policy_hierarchy/    Layered policy priority + safe explanations
        tool_authz/          Tool authorization boundary (param validation)
        action_guard/        Privileged-action pipeline (dry-run, bulk, dual control)
        scorecard/           Security posture scorecard

Security Principles:
    - Zero Trust: No entity is trusted by default
    - Least Privilege: Minimum required permissions
    - Defense in Depth: Multiple security layers
    - Audit Everything: All actions are logged
    - Secure by Default: Safest option is default

Usage::

    from aetheros_security import SecurityManager

    sm = SecurityManager()
    sm.initialize()
"""

from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)


def _resolve_version() -> str:
    """Resolve the installed AetherOS version from distribution metadata."""
    try:
        from importlib.metadata import version
        return version("aetheros")
    except Exception:
        pass
    try:
        from pathlib import Path
        _pyproject = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
        if _pyproject.exists():
            for line in _pyproject.read_text("utf-8").splitlines():
                if line.lstrip().startswith("version ="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "0.0.0"


# Security version (single source of truth: installed distribution metadata)
__version__: Final[str] = _resolve_version()

# Zero Trust Constants
ZERO_TRUST_ENABLED: Final[bool] = True
DEFAULT_PERMISSION: Final[str] = "deny"
AUDIT_ALL_ACTIONS: Final[bool] = True

# Permission Categories
PERMISSION_CATEGORIES = {
    "filesystem": ["read", "write", "execute", "delete"],
    "clipboard": ["read", "write"],
    "browser": ["navigate", "interact", "extract"],
    "terminal": ["execute", "background"],
    "network": ["connect", "listen", "dns"],
    "camera": ["capture", "record"],
    "microphone": ["record", "listen"],
    "location": ["access"],
    "notifications": ["show", "manage"],
    "desktop": ["control", "screenshot"],
    "keyboard": ["input", "capture"],
    "mouse": ["control", "capture"],
    "voice": ["synthesize", "recognize"],
    "memory": ["read", "write", "delete"],
    "knowledge": ["read", "write", "search"],
    "cloud": ["upload", "download", "manage"],
    "git": ["read", "write", "push", "pull"],
    "docker": ["build", "run", "manage"],
    "ssh": ["connect", "execute"],
    "api": ["access", "manage"],
}

# Risk Levels
RISK_LEVELS = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

# Permission Durations
PERMISSION_DURATIONS = {
    "once": "Single use",
    "session": "Until session ends",
    "hour": "1 hour",
    "day": "24 hours",
    "week": "7 days",
    "month": "30 days",
    "permanent": "Until revoked",
}


def get_version() -> str:
    """Return the security version."""
    return __version__


def get_permission_categories() -> dict:
    """Return permission categories."""
    return dict(PERMISSION_CATEGORIES)


def get_risk_levels() -> dict:
    """Return risk levels."""
    return dict(RISK_LEVELS)


class SecurityManager:
    """Main security manager for AetherOS.

    Usage::

        sm = SecurityManager()
        sm.initialize()

        # Check permission
        allowed = sm.check_permission("filesystem:read", "my-plugin")

        # Request permission
        granted = sm.request_permission("network:connect", "my-plugin", reason="API access")

        # Load a declarative policy
        sm.load_policy("workspace", "policy.yaml")

        # Run a threat scan
        threats = sm.run_threat_detection()

        # Collect security diagnostics
        diagnostics = sm.run_diagnostics()

        # Attempt recovery of a security subsystem
        report = sm.recover("secrets")

        # Zero-trust authorization
        decision = sm.authorize(
            principal="agent-1", action="filesystem:read",
            resource="workspace/notes.md",
        )

        # Register an agent identity
        sm.register_agent(agent_id="agent-1", owner="alice")

        # Emergency stop
        sm.emergency_stop(reason="suspected compromise")
    """

    def __init__(self) -> None:
        self._initialized = False
        self._zero_trust = ZERO_TRUST_ENABLED
        self._policies: dict = {}
        self._recovery_handlers: dict = {}

    def initialize(self) -> None:
        """Initialize the security system."""
        if self._initialized:
            return

        logger.info("Initializing AetherOS Security OS v%s", __version__)
        # Load built-in policy defaults so zero-trust posture applies even
        # before any user policy is loaded.
        from aetheros_security.policy import get_policy_manager
        get_policy_manager().load_policy("default", {
            "version": 1,
            "workspace": "default",
            "default_permission": "deny",
        })
        self._register_default_recovery_handlers()
        self._initialized = True

    def check_permission(
        self,
        permission: str,
        requester: str,
        **kwargs,
    ) -> bool:
        """Check if a permission is granted.

        Args:
            permission: Permission to check (e.g., "filesystem:read").
            requester: Who is requesting (plugin, agent, etc.).

        Returns:
            True if permission is granted.
        """
        # Per-workspace / per-agent policy takes precedence when provided.
        policy_name = kwargs.pop("policy", kwargs.pop("workspace", None))
        if policy_name:
            from aetheros_security.policy import get_policy_manager
            return get_policy_manager().check_permission(policy_name, permission)

        from aetheros_security.permissions import get_permission_engine
        engine = get_permission_engine()
        return engine.check(permission, requester, **kwargs)

    def request_permission(
        self,
        permission: str,
        requester: str,
        *,
        reason: str = "",
        duration: str = "session",
    ) -> bool:
        """Request a permission.

        Args:
            permission: Permission to request.
            requester: Who is requesting.
            reason: Why the permission is needed.
            duration: How long the permission should last.

        Returns:
            True if permission is granted.
        """
        from aetheros_security.permissions import get_permission_engine
        engine = get_permission_engine()
        return engine.request(permission, requester, reason=reason, duration=duration)

    def load_policy(self, name: str, source) -> dict:
        """Load a declarative security policy.

        Args:
            name: Policy name (workspace/agent identifier).
            source: Path or dict of policy content.

        Returns:
            The validated policy.
        """
        from aetheros_security.policy import get_policy_manager
        policy = get_policy_manager().load_policy(name, source)
        self._policies[name] = policy
        return policy

    def list_policies(self) -> list:
        """List loaded policies."""
        from aetheros_security.policy import get_policy_manager
        return get_policy_manager().get_loaded_policies()

    def get_audit_log(self, limit: int = 100) -> list:
        """Get recent audit log entries."""
        from aetheros_security.audit import get_audit_logger
        logger = get_audit_logger()
        return logger.get_recent(limit)

    def run_threat_detection(self, activity: list | None = None) -> list:
        """Run threat detection over recorded activity.

        Args:
            activity: Optional activity records. When omitted, the detector
                uses whatever it has recorded this process.

        Returns:
            List of threat alerts.
        """
        from aetheros_security.threat import get_threat_detector
        detector = get_threat_detector()
        if activity:
            for record in activity:
                detector.record_activity(**record)
        return detector.analyze_activity()

    def run_diagnostics(self) -> dict:
        """Run security diagnostics across all subsystems.

        Returns:
            Per-subsystem status report. ``True`` means healthy, strings are
            error descriptions, and ``None`` means the subsystem is
            unavailable.
        """
        results: dict = {
            "zero_trust": self._zero_trust,
            "version": __version__,
        }
        try:
            from aetheros_security.encryption import get_encryption_manager
            mgr = get_encryption_manager()
            probe = mgr.encrypt("diagnostics-probe")
            results["encryption"] = mgr.decrypt(probe) == "diagnostics-probe"
        except Exception as exc:
            results["encryption"] = f"failed: {exc}"

        try:
            from aetheros_security.secrets import get_secrets_manager
            results["secrets_backend"] = get_secrets_manager().backend.value
        except Exception as exc:
            results["secrets"] = f"failed: {exc}"

        try:
            from aetheros_security.sandbox import get_sandbox_manager
            results["sandbox_backend"] = get_sandbox_manager().get_backend()
        except Exception as exc:
            results["sandbox"] = f"failed: {exc}"

        try:
            from aetheros_security.permissions import get_permission_engine
            results["permissions"] = get_permission_engine().get_stats()
        except Exception as exc:
            results["permissions"] = f"failed: {exc}"

        try:
            from aetheros_security.audit import get_audit_logger
            results["audit"] = get_audit_logger().get_statistics()
        except Exception as exc:
            results["audit"] = f"failed: {exc}"

        try:
            from aetheros_security.supply_chain import get_supply_chain_manager
            results["supply_chain"] = get_supply_chain_manager().get_stats()
        except Exception as exc:
            results["supply_chain"] = f"failed: {exc}"

        try:
            from aetheros_security.privacy import get_privacy_manager
            results["privacy"] = get_privacy_manager().get_settings()
        except Exception as exc:
            results["privacy"] = f"failed: {exc}"

        return results

    def recover(self, subsystem: str) -> dict:
        """Attempt recovery of a security subsystem.

        Args:
            subsystem: One of the registered subsystems (``secrets``,
                ``encryption``, ``permissions``, ``audit``, ``sandbox``,
                ``authentication``, ``session``, ``policy``).

        Returns:
            A recovery report.
        """
        handler = self._recovery_handlers.get(subsystem)
        if handler is None:
            return {"subsystem": subsystem, "ok": False, "error": "unknown subsystem"}
        return handler()

    def _register_default_recovery_handlers(self) -> None:
        def _recover_secrets() -> dict:
            try:
                from aetheros_security.secrets import get_secrets_manager
                get_secrets_manager()
                return {"subsystem": "secrets", "ok": True, "action": "validated backend"}
            except Exception as exc:
                return {"subsystem": "secrets", "ok": False, "error": str(exc)}

        def _recover_encryption() -> dict:
            try:
                from aetheros_security.encryption import get_encryption_manager
                mgr = get_encryption_manager()
                probe = mgr.encrypt("recovery-probe")
                ok = mgr.decrypt(probe) == "recovery-probe"
                return {"subsystem": "encryption", "ok": ok, "action": "probe roundtrip"}
            except Exception as exc:
                return {"subsystem": "encryption", "ok": False, "error": str(exc)}

        def _recover_permissions() -> dict:
            try:
                from aetheros_security.permissions import get_permission_engine
                get_permission_engine()
                return {"subsystem": "permissions", "ok": True, "action": "validated engine"}
            except Exception as exc:
                return {"subsystem": "permissions", "ok": False, "error": str(exc)}

        def _recover_audit() -> dict:
            try:
                from aetheros_security.audit import get_audit_logger, AuditEventType
                get_audit_logger().log(
                    AuditEventType.SECURITY_ALERT,
                    source="security.recovery",
                    message="audit recovery probe",
                )
                return {"subsystem": "audit", "ok": True, "action": "wrote probe entry"}
            except Exception as exc:
                return {"subsystem": "audit", "ok": False, "error": str(exc)}

        def _recover_authentication() -> dict:
            try:
                from aetheros_security.authentication import get_authentication_manager
                get_authentication_manager()
                return {"subsystem": "authentication", "ok": True, "action": "validated manager"}
            except Exception as exc:
                return {"subsystem": "authentication", "ok": False, "error": str(exc)}

        self._recovery_handlers = {
            "secrets": _recover_secrets,
            "encryption": _recover_encryption,
            "permissions": _recover_permissions,
            "audit": _recover_audit,
            "authentication": _recover_authentication,
            "session": _recover_authentication,
        }

    def get_security_status(self) -> dict:
        """Get overall security status."""
        return {
            "zero_trust": self._zero_trust,
            "initialized": self._initialized,
            "version": __version__,
            "policies": len(self._policies),
        }

    # ------------------------------------------------------------------
    # Zero-trust authorization (steps 7, 12-15)
    # ------------------------------------------------------------------

    def authorize(
        self,
        principal: str,
        action: str,
        resource: str = "",
        *,
        session: str = "",
        risk=None,
    ):
        """Evaluate one action through the central authorization engine.

        Returns an :class:`aetheros_security.authz.AuthorizationDecision`.
        """
        from aetheros_security.authz import (AuthorizationRequest,
                                             get_authorization_engine)
        engine = get_authorization_engine()
        request = AuthorizationRequest(
            principal=principal,
            action=action,
            resource=resource,
            session=session,
            risk=risk,
        )
        return engine.authorize(request)

    def classify_risk(self, action: str, resource: str = ""):
        """Classify an action's risk (low/medium/high/critical)."""
        from aetheros_security.authz import get_authorization_engine
        return get_authorization_engine().get_risk(action, resource)

    def create_approval(self, principal, action, resource="", *,
                        reason="", risk="high"):
        """Create a human-approval binding for one exact action."""
        from aetheros_security.approval import get_approval_manager
        return get_approval_manager().create(
            principal, action, resource, reason=reason, risk=risk,
        )

    def resolve_approval(self, approval_id, *, approved, resolver="user") -> bool:
        from aetheros_security.approval import get_approval_manager
        return get_approval_manager().resolve(approval_id, approved=approved,
                                              resolver=resolver)

    # ------------------------------------------------------------------
    # Identity (steps 3-5)
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str = "", *, owner: str = "",
                       agent_type: str = "general", trust_level: str = "low",
                       workspace: str = "", **kwargs):
        """Register an agent identity."""
        from aetheros_security.identity import (AgentIdentity, TrustLevel,
                                                get_identity_registry)
        identity = AgentIdentity(
            agent_id=agent_id,
            agent_type=agent_type,
            owner=owner,
            trust_level=TrustLevel(trust_level),
            workspace=workspace,
            **kwargs,
        )
        return get_identity_registry().register_agent(identity)

    def get_agent(self, agent_id: str):
        from aetheros_security.identity import get_identity_registry
        return get_identity_registry().get_agent(agent_id)

    def quarantine_agent(self, agent_id: str) -> bool:
        from aetheros_security.identity import get_identity_registry
        return get_identity_registry().quarantine(agent_id)

    def register_user(self, user_id: str, *, scopes=None):
        from aetheros_security.identity import get_identity_registry
        return get_identity_registry().register_user(user_id, scopes=scopes)

    # ------------------------------------------------------------------
    # Tool manifests (steps 9-11)
    # ------------------------------------------------------------------

    def register_tool_manifest(self, manifest) -> None:
        """Register a :class:`aetheros_security.manifest.ToolManifest`."""
        from aetheros_security.manifest import get_manifest_registry
        get_manifest_registry().register(manifest)

    def check_tool_permission(self, tool_id, operation, value=""):
        from aetheros_security.manifest import get_manifest_registry
        return get_manifest_registry().allows(tool_id, operation, value)

    # ------------------------------------------------------------------
    # Filesystem security (steps 23-25)
    # ------------------------------------------------------------------

    def fs_allow(self, pattern, access="read_write"):
        from aetheros_security.filesystem import (FilesystemAccess,
                                                  get_filesystem_security)
        return get_filesystem_security().allow(
            pattern, access=FilesystemAccess(access))

    def fs_deny(self, pattern):
        from aetheros_security.filesystem import get_filesystem_security
        return get_filesystem_security().deny(pattern)

    def fs_can(self, path, operation="read"):
        from aetheros_security.filesystem import get_filesystem_security
        return get_filesystem_security().check(path, operation)

    # ------------------------------------------------------------------
    # MCP security (steps 34-37)
    # ------------------------------------------------------------------

    def register_mcp_server(self, server_id, name, **kwargs):
        from aetheros_security.mcp import get_mcp_security_manager
        return get_mcp_security_manager().register_server(server_id, name, **kwargs)

    def approve_mcp(self, server_id) -> bool:
        from aetheros_security.mcp import get_mcp_security_manager
        return get_mcp_security_manager().approve(server_id)

    def quarantine_mcp(self, server_id) -> bool:
        from aetheros_security.mcp import get_mcp_security_manager
        return get_mcp_security_manager().quarantine(server_id)

    # ------------------------------------------------------------------
    # Redaction (step 19)
    # ------------------------------------------------------------------

    def redact(self, text: str) -> str:
        from aetheros_security.redaction import get_redaction_manager
        return get_redaction_manager().redact(text)

    def redact_dict(self, data: dict) -> dict:
        from aetheros_security.redaction import get_redaction_manager
        return get_redaction_manager().redact_dict(data)

    # ------------------------------------------------------------------
    # Kill switches + safe shutdown (steps 49-50)
    # ------------------------------------------------------------------

    def set_kill_switch(self, name: str, active: bool, *,
                        principal: str, reason: str = "") -> bool:
        """Flip a named kill switch (step 49).

        ``principal`` must be elevated (admin/system/security/root).
        """
        from aetheros_security.kill_switch import get_kill_switch_registry
        return get_kill_switch_registry().set_switch_by_name(
            name, active, principal=principal, reason=reason)

    def kill_switch_status(self) -> list:
        from aetheros_security.kill_switch import get_kill_switch_registry
        return get_kill_switch_registry().status()

    def safe_shutdown(self, *, principal: str = "system",
                      reason: str = "safe shutdown") -> dict:
        """Execute a controlled safe shutdown (step 50)."""
        from aetheros_security.kill_switch import get_safe_shutdown_service
        return get_safe_shutdown_service().run(principal=principal, reason=reason)

    # ------------------------------------------------------------------
    # Data classification + flow control (steps 31-33)
    # ------------------------------------------------------------------

    def classify_data(self, text: str) -> str:
        """Classify content (public..secret)."""
        from aetheros_security.classification import classify_content
        return classify_content(text).value

    def check_data_flow(self, *, classification: str, source: str,
                        destination: str, principal: str = "") -> dict:
        """Gate data movement across boundaries (step 32)."""
        from aetheros_security.classification import (DataClassification,
                                                      get_data_flow_guard)
        level = DataClassification(classification)
        decision = get_data_flow_guard().check_flow(
            classification=level, source=source, destination=destination,
            principal=principal)
        return decision.to_dict()

    # ------------------------------------------------------------------
    # Resource budgets + recursion limits (steps 46-47)
    # ------------------------------------------------------------------

    def create_budget(self, name: str, *, tool_calls=None, cost_usd=None,
                      time_seconds=None, tokens=None, network_requests=None,
                      storage_bytes=None, compute_units=None):
        """Create/register a named resource budget (step 47)."""
        from aetheros_security.budget import BudgetLimits, register_budget, ResourceBudget
        limits = BudgetLimits(time_seconds=time_seconds, token_budget=tokens,
                              cost_usd=cost_usd, tool_calls=tool_calls,
                              network_requests=network_requests,
                              storage_bytes=storage_bytes, compute_units=compute_units)
        return register_budget(name, ResourceBudget(limits=limits, name=name))

    def budget_state(self, name: str) -> dict:
        from aetheros_security.budget import get_budget
        budget = get_budget(name)
        if budget is None:
            return {}
        return {"name": name, **budget.state()}

    def recursion_depth(self) -> int:
        from aetheros_security.budget import get_recursion_guard
        return get_recursion_guard().depth

    # ------------------------------------------------------------------
    # Policy priority hierarchy + safe explanations (steps 52-53)
    # ------------------------------------------------------------------

    def evaluate_policy_hierarchy(self, layered: list, *, default: str = "deny") -> dict:
        """Resolve layered ``(layer, decision)`` pairs (step 52)."""
        from aetheros_security.policy_hierarchy import (PolicyLayer,
                                                        resolve_layer_decisions)
        pairs = []
        for layer, decision in layered:
            if isinstance(layer, str) and layer.isdigit():
                pairs.append((PolicyLayer(int(layer)), decision))
            elif isinstance(layer, str):
                pairs.append((PolicyLayer[layer.upper()], decision))
            else:
                pairs.append((PolicyLayer(layer), decision))
        return resolve_layer_decisions(pairs, default=default)

    def safe_explanation(self, decision: str, reason: str = "") -> str:
        """Produce a safe, non-revealing explanation (step 53)."""
        from aetheros_security.policy_hierarchy import safe_explanation
        return safe_explanation(decision, reason)

    # ------------------------------------------------------------------
    # Tool authorization service (steps 14, 16, 34)
    # ------------------------------------------------------------------

    def tool_authz_check(self, *, principal: str, tool: str, action: str,
                         resource: str = "", parameters: dict | None = None,
                         session: str = "", mission: str = ""):
        """Run a tool-call through the authorization boundary."""
        from aetheros_security.tool_authz import (ToolAuthRequest,
                                                  get_tool_authorization_service)
        service = get_tool_authorization_service()
        decision = service.check(ToolAuthRequest(
            principal=principal, tool=tool, action=action, resource=resource,
            parameters=parameters or {}, session=session, mission=mission))
        return decision.to_dict()

    def register_tool_action(self, tool: str, action: str) -> None:
        from aetheros_security.tool_authz import get_tool_authorization_service
        get_tool_authorization_service().register_tool_action(tool, action)

    # ------------------------------------------------------------------
    # Action guard (steps 35-36, 41-44, 59-61)
    # ------------------------------------------------------------------

    def guarded_action(self, *, principal: str, action: str, resource: str = "",
                       parameters: dict | None = None, session: str = "",
                       mission: str = "", task: str = "", agent: str = "",
                       dry_run: bool = False, item_count: int = 1) -> dict:
        """Run a guarded action through the deterministic pipeline."""
        from aetheros_security.action_guard import (GuardRequest,
                                                    get_action_guard)
        result = get_action_guard().execute(GuardRequest(
            principal=principal, action=action, resource=resource,
            parameters=parameters or {}, session=session, mission=mission,
            task=task, agent=agent, dry_run=dry_run, item_count=item_count))
        return result.to_dict()

    def classify_action_risk(self, action: str, resource: str = "") -> str:
        """Return the R0-R4 risk tier for an action (step 36)."""
        from aetheros_security.action_guard import get_action_guard
        return get_action_guard().classify_risk(action, resource).value

    # ------------------------------------------------------------------
    # Security scorecard (step 86)
    # ------------------------------------------------------------------

    def security_scorecard(self) -> dict:
        """Generate the security posture scorecard (step 86)."""
        from aetheros_security.scorecard import generate_scorecard
        return generate_scorecard()

    # ------------------------------------------------------------------
    # Response: emergency stop, lockdown, incidents, health (52, 53, 67, 68)
    # ------------------------------------------------------------------

    def emergency_stop(self, reason: str = "") -> bool:
        from aetheros_security.response import get_response_manager
        return get_response_manager().emergency_stop(reason)

    def recover_from_stop(self) -> bool:
        from aetheros_security.response import get_response_manager
        return get_response_manager().recover_from_stop()

    def lockdown(self, reason: str = "") -> bool:
        from aetheros_security.response import get_response_manager
        return get_response_manager().lockdown(reason)

    def open_incident(self, title, *, severity="medium", description="",
                      source="", affected_principals=None):
        from aetheros_security.response import get_response_manager
        return get_response_manager().open_incident(
            title, severity=severity, description=description,
            source=source, affected_principals=affected_principals,
        )

    def security_health(self):
        """Run the security health checks and return the score report."""
        from aetheros_security.response import get_response_manager
        manager = get_response_manager()
        manager.register_default_health_checks()
        return manager.run_health_checks()


# Global security manager
_security_manager: SecurityManager | None = None


def get_security_manager() -> SecurityManager:
    """Return the global SecurityManager singleton."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager
