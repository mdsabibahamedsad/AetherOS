"""
COMPATIBILITY SHIM — ``agent.transports.hermes_tools_mcp_server``

This module was renamed to ``agent.transports.aetheros_tools_mcp_server``.
Old import paths still work via this re-export.
"""
from agent.transports.aetheros_tools_mcp_server import *  # noqa: F401, F403
from agent.transports.aetheros_tools_mcp_server import main  # noqa: F401
