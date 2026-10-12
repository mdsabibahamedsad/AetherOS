"""Live loopback rigs: real in-process MCP server/client and A2A
peer pairs exercising the FULL fabric path
(propose -> authorize -> token -> execute -> verify -> audit).
Transport is loopback function calls — labeled LOOPBACK, never
claimed as internet federation. Proves the enforcement logic end
to end; network behavior stays covered by the mTLS + boundary
tests."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .contracts import ToolContractValidator, ToolManifest
from .fabric import TrustFabric
from .models import CapabilityToken


class LoopbackMCPServer:
    """An MCP-style tool server: manifest-declared tools, independent
    token validation per call, signed execution receipts."""

    def __init__(self, fabric: TrustFabric, server_id: str = "mcp-rig"):
        self.fabric = fabric
        self.server_id = server_id
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.validator = ToolContractValidator()

    def register_tool(self, manifest: ToolManifest,
                      handler: Callable[[Dict[str, Any]], Any]) -> None:
        verdict = self.validator.validate(manifest)
        if not verdict["valid"]:
            raise ValueError(f"tool rejected: {verdict['errors']}")
        self.tools[manifest.identity] = {"manifest": manifest,
                                         "handler": handler}

    def call(self, tool_id: str, token: CapabilityToken,
             args: Dict[str, Any]) -> Dict[str, Any]:
        if tool_id not in self.tools:
            return {"ok": False, "reason": "unknown tool"}
        # independent validation: audience must be this server
        try:
            self.fabric.capabilities.validate(token, self.server_id)
        except Exception as exc:
            return {"ok": False, "reason": f"token rejected: {exc}"}
        entry = self.tools[tool_id]
        if token.action != tool_id and token.action not in entry[
                "manifest"].capabilities:
            return {"ok": False, "reason": "token action != tool"}
        try:
            result = entry["handler"](args)
        except Exception as exc:
            return {"ok": False, "reason": f"handler: {exc}"[:200]}
        receipt = self.fabric.provenance.issue_receipt(
            token.token_id, token.subject, token.action, "rig-policy",
            "v1", "hash-rig", "hash-auth", args, result, "handler-ok")
        self.fabric.plane.audit.emit(
            "ACTION_EXECUTED", {"tool": tool_id}, {"ok": True})
        return {"ok": True, "result": result,
                "receipt": receipt.receipt_id}


class LoopbackMCPClient:
    def __init__(self, fabric: TrustFabric, identity_id: str):
        self.fabric = fabric
        self.identity_id = identity_id

    def invoke(self, server: LoopbackMCPServer, tool_id: str,
               resource: str, args: Dict[str, Any],
               task_id: str = "rig") -> Dict[str, Any]:
        try:
            tok = self.fabric.authorize(
                self.identity_id, tool_id, resource, kind="mcp",
                purpose="rig e2e", tool_id=server.server_id,
                task_id=task_id)
        except Exception as exc:
            return {"ok": False, "stage": "authorize",
                    "reason": str(exc)[:200]}
        return server.call(tool_id, tok, args)


class LoopbackA2APeer:
    """An A2A-style peer: explicit delegation required, results carry
    identity + provenance + execution mode."""

    def __init__(self, fabric: TrustFabric, peer_id: str):
        self.fabric = fabric
        self.peer_id = peer_id

    def request(self, capability: str, scope: str,
                delegation_id: str = "") -> Dict[str, Any]:
        if not self.fabric.check_remote(self.peer_id, capability, scope,
                                        delegation_id):
            return {"ok": False,
                    "reason": "REMOTE_DENIED (explicit delegation required)"}
        return {"ok": True, "peer": self.peer_id,
                "capability": capability,
                "evidence": {"identity": self.peer_id,
                             "delegation": delegation_id,
                             "mode": "LOOPBACK"}}

    def delegate_to(self, issuer_scopes, issuer_id: str, scopes: List[str],
                    task_id: str = "") -> Any:
        return self.fabric.plane.delegation.delegate(
            issuer_scopes, issuer_id, self.peer_id, scopes,
            task_id=task_id)
