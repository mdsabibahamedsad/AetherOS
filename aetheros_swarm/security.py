"""Tool authorization + swarm security (sections 27-29, 80-85).

- authorize_tool(): (user, run, task, agent, tool, resource, policy) gate.
  Discovery (registry/MCP listing) never implies authorization.
- Least privilege: agents receive only role tools ∩ task.allowed_tools ∩
  policy grants; privilege escalation (self-granting writes/terminal/email/
  deploy) is denied and audited.
- Injection defense: agent outputs are data; orchestrator directives never
  accepted from agent message content (scan for override phrases).
- Secret isolation: secret-shaped content never enters messages/packages.
- Data isolation: project_id must match unless explicitly authorized.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from aetheros_swarm.models import AgentInstance, SideEffectTier, SwarmTask

# Privileges a low-privilege agent must never self-grant (section 82).
_ESCALATION_DENIED = frozenset({
    "filesystem_write", "filesystem_delete", "terminal", "execute_code",
    "send_email", "publish_code", "deploy", "payment", "install_software",
    "terminal.exec", "email.send",
})

# Side-effecting tools requiring explicit authorization (section 83).
_WRITE_TOOLS = frozenset({
    "patch", "terminal", "memory2_create", "memory2_forget",
    "delegate_task", "swarm_stop", "computer_use", "browser_navigate",
})

_OVERRIDE_PHRASES = re.compile(
    r"(ignore the orchestrator|override (policy|orchestrator)|disregard (prior|previous) instructions|"
    r"execute this command|you are now|new instructions:)", re.I)

_SECRET_SHAPED = re.compile(
    r"(api[_-]?key\s*[:=]\s*\S+|password\s*[:=]\s*\S+|bearer\s+\S+|"
    r"sk-(live|test)-[A-Za-z0-9]{8,}|xox[baprs]-[A-Za-z0-9-]+|"
    r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)", re.I)


def contains_secret(text: str) -> bool:
    return bool(_SECRET_SHAPED.search(text or ""))


def sanitize_for_agent(text: str) -> str:
    """Refuse secret-bearing content outright (callers must not send secrets)."""
    if contains_secret(text):
        raise ValueError("secret-shaped content must never enter agent messages")
    return text


def scan_override_attempt(content: str) -> bool:
    """True when agent output tries to override orchestrator policy (data, not authority)."""
    return bool(_OVERRIDE_PHRASES.search(content or ""))


class ToolAuthorizer:
    def __init__(self, *, policy_grants: Optional[Dict[str, List[str]]] = None) -> None:
        # policy_grants: role -> extra allowed tools beyond role defaults.
        self._grants = policy_grants or {}
        self.denials: List[Dict[str, Any]] = []

    def tools_for(self, agent: AgentInstance, task: SwarmTask,
                  role_tools: List[str]) -> List[str]:
        allowed = set(role_tools) & set(task.allowed_tools or role_tools)
        allowed |= set(self._grants.get(agent.role, []))
        # Least privilege: destructive tier needs explicit task tier.
        if task.side_effect_tier == SideEffectTier.READ:
            allowed -= _WRITE_TOOLS
        return sorted(allowed)

    def authorize(self, *, agent: AgentInstance, task: SwarmTask,
                  tool: str, resource: str = "",
                  requested_permissions: Optional[List[str]] = None) -> Dict[str, Any]:
        # Privilege escalation defense: agent cannot self-grant.
        for perm in requested_permissions or []:
            if perm in _ESCALATION_DENIED and perm not in agent.permissions:
                self.denials.append({"agent": agent.id, "tool": tool,
                                     "perm": perm, "reason": "escalation"})
                return {"allowed": False, "reason": f"privilege escalation denied: {perm}"}
        if tool not in agent.tools:
            self.denials.append({"agent": agent.id, "tool": tool,
                                 "reason": "not in agent toolset"})
            return {"allowed": False, "reason": f"tool {tool} not authorized for agent {agent.id}"}
        if task.side_effect_tier == SideEffectTier.DESTRUCTIVE and tool in _WRITE_TOOLS:
            return {"allowed": True, "reason": "destructive tier: requires approval gate",
                    "needs_approval": True}
        return {"allowed": True, "reason": "ok"}

    def check_data_isolation(self, *, agent_project: str, task_project: str,
                             authorized_cross: bool = False) -> bool:
        if not agent_project or not task_project:
            return True
        if agent_project == task_project:
            return True
        return authorized_cross
