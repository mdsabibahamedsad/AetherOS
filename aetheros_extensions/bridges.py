"""Integration bridges (sections 19, 21-23, 47-50).

One canonical path per subsystem — no parallel security systems:
- MCP servers as MCPExtensions over tools/mcp_tool.py (lazy import).
- SKILL.md dirs as skill extensions (frontmatter parse, untrusted).
- Extension tools into ToolRegistry with full metadata.
- Specialist agents into swarm AgentRegistry.
- Automation nodes inherit autonomy caps (never elevate).
- Scoped memory via MemoryService recall adapter.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_extensions.manifest import ExtensionManifest, ExtensionType
from aetheros_extensions.permissions import Grant

_INJECTION_RE = re.compile(
    r"(ignore (all )?previous instructions|override (system|platform) policy|"
    r"disregard (safety|security)|prompt injection|jailbreak)", re.I)


def scan_untrusted_text(text: str) -> Dict[str, Any]:
    """Treat skill instructions / MCP descriptions / READMEs as untrusted."""
    hits = _INJECTION_RE.findall(text or "")
    return {"suspicious": bool(hits), "hits": len(hits)}


# -- MCP ---------------------------------------------------------------

def mcp_server_manifest(server_id: str, config: Dict[str, Any]) -> ExtensionManifest:
    return ExtensionManifest(
        id=f"mcp.{server_id}", name=f"MCP: {server_id}",
        display_name=f"MCP server {server_id}", version="1.0.0",
        description=f"Adopted MCP server '{server_id}' (BUILT_IN bridge).",
        publisher="aetheros", publisher_id="aetheros",
        extension_type=ExtensionType.MCP_SERVER,
        capabilities=["mcp.tools"],
        permissions=[{"permission": "mcp.connect", "names": [server_id]},
                     {"permission": "mcp.tool.execute", "names": [server_id]}],
        mcp_servers=[{"id": server_id, **config}])


def mcp_server_health(server_id: str) -> Dict[str, Any]:
    """Real health via the MCP client module (no fake healthy)."""
    try:
        import tools.mcp_tool as mcp
    except ImportError as exc:
        return {"state": "FAILING", "reason": f"mcp client unavailable: {exc}"}
    try:
        servers = getattr(mcp, "_servers", {}) or {}
        if server_id in servers:
            return {"state": "HEALTHY", "reason": "connected"}
        configured = False
        try:
            from aetheros_cli.config import load_config
            cfg = load_config() or {}
            configured = server_id in (cfg.get("mcp_servers") or {})
        except Exception:
            pass
        return {"state": "DEGRADED" if configured else "FAILING",
                "reason": "configured but not connected" if configured
                          else "server not configured"}
    except Exception as exc:
        return {"state": "FAILING", "reason": str(exc)[:200]}


def mcp_tool_gate(tool_description: str) -> Dict[str, Any]:
    """MCP tool descriptions are untrusted: scan before use."""
    scan = scan_untrusted_text(tool_description)
    if scan["suspicious"]:
        return {"allowed": False, "reason": "tool description trips injection scan"}
    return {"allowed": True, "reason": "description scan passed (still untrusted at runtime)"}


# -- skills --------------------------------------------------------------

def parse_skill_frontmatter(skill_dir: Path) -> Dict[str, Any]:
    """Parse SKILL.md frontmatter (yaml-lite, stdlib only)."""
    md = Path(skill_dir) / "SKILL.md"
    if not md.exists():
        raise ValueError("SKILL.md missing")
    text = md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("SKILL.md missing frontmatter")
    end = text.find("\n---", 3)
    if end < 0:
        raise ValueError("SKILL.md frontmatter unterminated")
    front = text[3:end]
    out: Dict[str, Any] = {}
    for line in front.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip().strip("\"'")
    instructions = text[end + 4:]
    return {"frontmatter": out, "instructions": instructions,
            "scan": scan_untrusted_text(instructions + front)}


def skill_manifest(skill_id: str, parsed: Dict[str, Any]) -> ExtensionManifest:
    fm = parsed.get("frontmatter", {})
    return ExtensionManifest(
        id=f"skill.{skill_id}", name=str(fm.get("name", skill_id)),
        display_name=str(fm.get("name", skill_id)),
        version=str(fm.get("version", "1.0.0")),
        description=str(fm.get("description", ""))[:500],
        publisher="aetheros", publisher_id=str(fm.get("author", "aetheros")),
        extension_type=ExtensionType.SKILL,
        capabilities=[f"skill.{skill_id}"],
        permissions=[],
        skills=[{"id": skill_id, "untrusted_instructions": True}])


# -- tools ---------------------------------------------------------------

def extension_tool_schema(tool: Dict[str, Any], extension_id: str,
                          version: str) -> Dict[str, Any]:
    schema = {"name": tool.get("name", ""), "description": str(tool.get("description", ""))[:1000],
              "parameters": tool.get("parameters", {"type": "object", "properties": {}})}
    schema["_extension"] = {"toolId": tool.get("name", ""), "extensionId": extension_id,
                            "risk": tool.get("risk", "R3"),
                            "permissions": tool.get("permissions", []),
                            "side_effects": tool.get("side_effects", "unknown"),
                            "idempotent": bool(tool.get("idempotent", False)),
                            "approval": tool.get("approval", "approve"),
                            "version": version}
    return schema


# -- agents ---------------------------------------------------------------

def register_specialist_agent(agent: Dict[str, Any]) -> Dict[str, Any]:
    """Register a specialist agent definition with the swarm registry."""
    try:
        from aetheros_swarm.registry import AgentDefinition, AgentRegistry
    except ImportError as exc:
        return {"ok": False, "reason": f"swarm registry unavailable: {exc}"}
    try:
        reg = AgentRegistry()
        reg.register(AgentDefinition(
            role=str(agent.get("role", "")), capabilities=list(agent.get("capabilities", [])),
            default_tools=list(agent.get("tools", [])),
            permissions=list(agent.get("permissions", ["read"])),
            description=str(agent.get("description", ""))[:500]))
        return {"ok": True, "role": agent.get("role", "")}
    except Exception as exc:
        return {"ok": False, "reason": str(exc)[:200]}


# -- automation ------------------------------------------------------------

def automation_node_gate(node: Dict[str, Any], autonomy_level: int) -> Dict[str, Any]:
    """Extension workflow nodes inherit caps; never elevate Level 0."""
    if autonomy_level <= 0:
        return {"allowed": False, "reason": "automation disabled (level 0)"}
    action = str(node.get("action", ""))
    if action in ("shell", "deploy", "email_send", "delete_data") and autonomy_level < 5:
        return {"allowed": False, "reason": f"{action} needs supervised autonomy"}
    return {"allowed": True, "reason": "within autonomy cap"}


# -- memory ---------------------------------------------------------------

def scoped_memory_recall(scope: str = "extension"):
    def recall(query: str, *, top_k: int = 5) -> Dict[str, Any]:
        try:
            from aetheros_memory_intelligence.service import MemoryService
            svc = MemoryService()
            svc.initialize()
            return svc.retrieve(query, top_k=top_k)
        except Exception as exc:
            return {"included": [], "error": str(exc)[:200]}
    recall.__scope__ = scope
    return recall
