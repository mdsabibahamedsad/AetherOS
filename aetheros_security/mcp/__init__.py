"""
MCP Security for AetherOS
=========================

Trust registry and enforcement for MCP servers (master security spec
steps 34-37):

    - Server identity (server id, name, version, source, integrity hash)
    - Trust status lifecycle: APPROVED / PENDING / BLOCKED / QUARANTINED /
      REMOVED
    - Permission manifest per server (filesystem, network, credentials)
    - Tool inventory with schema integrity hashes
    - Tool-poisoning defense: tool descriptions, schemas, and responses are
      treated as UNTRUSTED input. They cannot change permissions and cannot
      authorize other tools.

Only APPROVED servers gain access to privileged AetherOS capabilities.
A server whose tool schema changes unexpectedly is quarantined and must be
re-approved.

Usage::

    from aetheros_security.mcp import (
        McpSecurityManager, McpServerRecord, McpTrustStatus,
    )

    mcp = McpSecurityManager()
    mcp.register_server("files", source="github:example/mcp-files")
    mcp.approve("files")
    assert mcp.is_approved("files")
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class McpTrustStatus(Enum):
    """Trust lifecycle status for an MCP server."""
    APPROVED = "approved"
    PENDING = "pending"
    BLOCKED = "blocked"
    QUARANTINED = "quarantined"
    REMOVED = "removed"


@dataclass
class McpToolRecord:
    """A tool exposed by an MCP server."""
    tool_id: str
    name: str
    schema_hash: str = ""
    version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "schema_hash": self.schema_hash,
            "version": self.version,
        }


@dataclass
class McpServerRecord:
    """A registered MCP server with its trust envelope."""
    server_id: str
    name: str
    source: str = ""                 # repo URL / package / command
    version: str = ""
    integrity_hash: str = ""         # hash of the server manifest/code
    trust_status: McpTrustStatus = McpTrustStatus.PENDING
    permission_manifest: Dict[str, Any] = field(default_factory=dict)
    tools: Dict[str, McpToolRecord] = field(default_factory=dict)
    network_policy: Dict[str, Any] = field(default_factory=dict)
    filesystem_policy: Dict[str, Any] = field(default_factory=dict)
    credential_scope: str = ""       # allowed secret scope ("" = none)
    created_at: float = 0.0
    updated_at: float = 0.0
    approved_at: float = 0.0
    audit_history: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        now = time.time()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.server_id:
            self.server_id = uuid.uuid4().hex

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server_id": self.server_id,
            "name": self.name,
            "source": self.source,
            "version": self.version,
            "integrity_hash": self.integrity_hash,
            "trust_status": self.trust_status.value,
            "permission_manifest": dict(self.permission_manifest),
            "tools": {k: t.to_dict() for k, t in self.tools.items()},
            "credential_scope": self.credential_scope,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "approved_at": self.approved_at,
        }


def compute_schema_hash(schema: Dict[str, Any]) -> str:
    """Stable hash of a tool schema."""
    blob = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class McpSecurityError(Exception):
    """Raised for invalid MCP security operations."""


class McpSecurityManager:
    """Manages MCP server trust, tool inventory, and poisoning defense."""

    def __init__(self) -> None:
        self._servers: Dict[str, McpServerRecord] = {}
        self._default_credential_scope = ""

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def register_server(
        self,
        server_id: str,
        name: str,
        *,
        source: str = "",
        version: str = "",
        integrity_hash: str = "",
        permission_manifest: Optional[Dict[str, Any]] = None,
        network_policy: Optional[Dict[str, Any]] = None,
        filesystem_policy: Optional[Dict[str, Any]] = None,
        credential_scope: str = "",
    ) -> McpServerRecord:
        """Register a new MCP server in PENDING trust status."""
        record = McpServerRecord(
            server_id=server_id,
            name=name,
            source=source,
            version=version,
            integrity_hash=integrity_hash,
            permission_manifest=permission_manifest or {},
            network_policy=network_policy or {},
            filesystem_policy=filesystem_policy or {},
            credential_scope=credential_scope or self._default_credential_scope,
        )
        self._servers[server_id] = record
        self._record_event(record, "registered")
        logger.info("MCP server registered: %s (%s) -> pending", name, server_id)
        return record

    def get_server(self, server_id: str) -> Optional[McpServerRecord]:
        return self._servers.get(server_id)

    def require_server(self, server_id: str) -> McpServerRecord:
        record = self._servers.get(server_id)
        if record is None:
            raise McpSecurityError(f"Unknown MCP server: {server_id}")
        return record

    def set_status(self, server_id: str, status: McpTrustStatus) -> bool:
        record = self._servers.get(server_id)
        if record is None:
            return False
        record.trust_status = status
        record.updated_at = time.time()
        if status == McpTrustStatus.APPROVED:
            record.approved_at = time.time()
        if status in (McpTrustStatus.QUARANTINED, McpTrustStatus.REMOVED,
                      McpTrustStatus.BLOCKED):
            record.credential_scope = ""
        self._record_event(record, f"status:{status.value}")
        logger.info("MCP server %s status -> %s", server_id, status.value)
        return True

    def approve(self, server_id: str) -> bool:
        return self.set_status(server_id, McpTrustStatus.APPROVED)

    def block(self, server_id: str) -> bool:
        return self.set_status(server_id, McpTrustStatus.BLOCKED)

    def quarantine(self, server_id: str) -> bool:
        return self.set_status(server_id, McpTrustStatus.QUARANTINED)

    def remove(self, server_id: str) -> bool:
        return self.set_status(server_id, McpTrustStatus.REMOVED)

    def is_approved(self, server_id: str) -> bool:
        record = self._servers.get(server_id)
        return record is not None and record.trust_status == McpTrustStatus.APPROVED

    def is_usable(self, server_id: str) -> bool:
        """Only APPROVED servers are usable for privileged capabilities."""
        return self.is_approved(server_id)

    # ------------------------------------------------------------------
    # Tool inventory + schema integrity (step 37)
    # ------------------------------------------------------------------

    def register_tool(self, server_id: str, tool_id: str, name: str,
                      schema: Optional[Dict[str, Any]] = None,
                      version: str = "") -> bool:
        """Register a tool's schema for a server.

        The schema is hashed; any later change to the schema is detected by
        :meth:`check_tool_schema` and quarantines the server.

        Returns True on success. Returns False (without side effects) if the
        server is not registered or not approved.
        """
        record = self._servers.get(server_id)
        if record is None or record.trust_status != McpTrustStatus.APPROVED:
            return False
        schema_hash = compute_schema_hash(schema or {})
        record.tools[tool_id] = McpToolRecord(
            tool_id=tool_id, name=name, schema_hash=schema_hash, version=version,
        )
        record.updated_at = time.time()
        self._record_event(record, f"tool_registered:{tool_id}")
        return True

    def check_tool_schema(self, server_id: str, tool_id: str,
                          schema: Dict[str, Any]) -> bool:
        """Verify a tool schema still matches the registered hash.

        On mismatch the server is quarantined and must be re-approved
        (a changed privileged tool is suspicious).

        Returns True when the schema matches.
        """
        record = self._servers.get(server_id)
        if record is None:
            return False
        registered = record.tools.get(tool_id)
        if registered is None:
            # Unknown tool from an approved server: quarantine it.
            self.quarantine(server_id)
            self._record_event(record, f"unknown_tool:{tool_id}", severity="warning")
            return False
        if registered.schema_hash != compute_schema_hash(schema):
            self.quarantine(server_id)
            self._record_event(
                record, f"schema_changed:{tool_id}", severity="warning",
                details={"expected": registered.schema_hash[:12],
                         "actual": compute_schema_hash(schema)[:12]},
            )
            logger.warning("MCP tool schema changed unexpectedly: %s:%s -> quarantined",
                           server_id, tool_id)
            return False
        return True

    # ------------------------------------------------------------------
    # Poisoning defense (step 36)
    # ------------------------------------------------------------------

    def validate_response(self, server_id: str, tool_id: str,
                          content: Any) -> bool:
        """Validate an MCP tool response as UNTRUSTED input.

        Response content can never change permissions, authorize other
        tools, or modify the trust state of this server. This is the
        poison-pill guard: text claiming to grant access is ignored.

        Returns True (safe to treat as data), False if the server has been
        revoked meanwhile.
        """
        record = self._servers.get(server_id)
        if record is None or record.trust_status not in (
            McpTrustStatus.APPROVED, McpTrustStatus.PENDING):
            return False
        # The response is data, not policy. No state changes here.
        return True

    def ensure_privileged_scope(self, server_id: str, scope: str) -> bool:
        """Whether an approved server holds the credential scope ``scope``."""
        record = self._servers.get(server_id)
        if record is None or record.trust_status != McpTrustStatus.APPROVED:
            return False
        if not record.credential_scope:
            return False
        return scope.startswith(record.credential_scope)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_servers(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._servers.values()]

    def servers_by_status(self, status: McpTrustStatus) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._servers.values()
                if s.trust_status == status]

    def get_stats(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for record in self._servers.values():
            key = record.trust_status.value
            counts[key] = counts.get(key, 0) + 1
        return {
            "total_servers": len(self._servers),
            "by_status": counts,
            "approved": counts.get("approved", 0),
            "pending": counts.get("pending", 0),
            "blocked": counts.get("blocked", 0),
            "quarantined": counts.get("quarantined", 0),
        }

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def _record_event(self, record: McpServerRecord, event: str,
                      details: Optional[Dict[str, Any]] = None,
                      severity: str = "info") -> None:
        record.audit_history.append({
            "timestamp": time.time(),
            "event": event,
            "details": details or {},
        })
        if len(record.audit_history) > 500:
            record.audit_history = record.audit_history[-500:]
        try:
            from aetheros_security.audit import (AuditEventType, AuditSeverity,
                                                 get_audit_logger)
            get_audit_logger().log(
                AuditEventType.CUSTOM,
                severity=AuditSeverity(severity),
                source="mcp",
                details={"server_id": record.server_id, "event": event,
                         ** (details or {})},
                message=f"MCP security: {event} {record.name}",
            )
        except Exception:
            pass


# Global MCP security manager
_mcp_security: McpSecurityManager | None = None


def get_mcp_security_manager() -> McpSecurityManager:
    """Return the global McpSecurityManager singleton."""
    global _mcp_security
    if _mcp_security is None:
        _mcp_security = McpSecurityManager()
    return _mcp_security