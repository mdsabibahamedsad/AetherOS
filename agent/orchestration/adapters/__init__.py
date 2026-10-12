"""Adapters package for AetherOS Orchestration Layer.

Provides adapters to wrap existing agents to the universal AgentInterface.
"""

from agent.orchestration.adapters.core_agent_adapter import (
    CoreAgentAdapter,
    adapt_core_agent,
)
from agent.orchestration.adapters.automation_agent_adapter import (
    AutomationAgentAdapter,
    AutomationRoleAdapter,
    adapt_automation_agent,
    adapt_automation_role_agent,
)
from agent.orchestration.adapters.delegate_adapter import (
    DelegateAgentAdapter,
    adapt_delegate_agent,
)

__all__ = [
    "CoreAgentAdapter",
    "adapt_core_agent",
    "AutomationAgentAdapter",
    "AutomationRoleAdapter",
    "adapt_automation_agent",
    "adapt_automation_role_agent",
    "DelegateAgentAdapter",
    "adapt_delegate_agent",
]