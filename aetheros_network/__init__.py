"""AetherOS Agent Network (Master 46) — trusted A2A federation layer.

A2A is the horizontal agent-to-agent layer. MCP remains the tool/context
integration layer. This package never replaces MCP and never exposes local
MCP tools to remote agents except through explicit policy + approval.

Protocol target: A2A v1.0 core subset — Agent Card
(``/.well-known/agent-card.json``), JSON-RPC ``message/send``,
``tasks/get``, ``tasks/cancel``, SSE streaming where the server supports
it. Anything outside that subset is documented as not implemented rather
than faked (Master 46 section 0, rules 4 and 12).
"""

from __future__ import annotations

A2A_PROTOCOL_NAME = "A2A"
A2A_SPEC_VERSION = "1.0"
A2A_SUPPORTED_VERSIONS = ("1.0", "0.3")
A2A_AGENT_CARD_PATH = "/.well-known/agent-card.json"

__all__ = [
    "A2A_PROTOCOL_NAME",
    "A2A_SPEC_VERSION",
    "A2A_SUPPORTED_VERSIONS",
    "A2A_AGENT_CARD_PATH",
]
