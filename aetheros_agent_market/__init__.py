"""AetherOS Agent Marketplace + Economy (spec: Agent Marketplace & Economy).

Layering (never blurred):
  MCP        = agent <-> tools/data/context
  A2A        = agent <-> agent            (aetheros_network)
  MARKET     = discovery + offers + contracts + reputation + economy
  AETHEROS   = identity + policy + orchestration + security +
               verification + accounting (this package, enforcing)

Money: integer minor units. Trust != capability. Reputation is
multidimensional, never a single number. No LLM in any approval path.
"""

from __future__ import annotations

__all__ = ["MARKETPLACE_VERSION", "API_VERSION"]

MARKETPLACE_VERSION = "0.1.0"
API_VERSION = "v1"
