"""
Tool Manager — bridges kernel capability system with existing tool registry.

Connects AetherOS tool registry to the kernel's capability authorization system.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

from kernel.core.types import (
    CapabilityDescriptor,
    CapabilityRiskLevel,
    DataClassification,
    ResourceBudget,
    ICapabilityProvider,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class ToolCapabilityMapping:
    """Maps a tool to a capability."""
    tool_name: str
    capability_id: str
    capability_descriptor: CapabilityDescriptor
    tool_schema: Dict[str, Any] = field(default_factory=dict)


class ToolCapabilityProvider(ICapabilityProvider):
    """Provider that wraps an AetherOS tool as a capability."""
    
    def __init__(self, tool_name: str, tool_handler: Callable, schema: Dict[str, Any]):
        self.tool_name = tool_name
        self.tool_handler = tool_handler
        self.schema = schema
        self._descriptor = self._create_descriptor()

    def _create_descriptor(self) -> CapabilityDescriptor:
        """Create capability descriptor from tool schema."""
        return CapabilityDescriptor(
            capability_id=f"tool.{self.tool_name}",
            version="1.0.0",
            provider="aetheros.tools",
            description=self.schema.get("description", f"Tool: {self.tool_name}"),
            inputs=self.schema.get("parameters", {}),
            outputs={"type": "object"},
            side_effects=[CapabilityRiskLevel.READ_ONLY],  # Would be inferred
            required_authority=[f"tool.{self.tool_name}"],
            required_resources=ResourceBudget(),
            required_credentials=[],
            network_access="network" in self.tool_name or "web" in self.tool_name or "browser" in self.tool_name,
            filesystem_access="fs" in self.tool_name or "file" in self.tool_name,
            device_access="device" in self.tool_name or "computer" in self.tool_name,
            data_classification=DataClassification.INTERNAL,
            reversibility=False,
            idempotency=False,
            latency_class="normal",
            cost_class="free",
            sandbox_support=True,
            verification_strategy="observe",
            tags=["tool", self.tool_name],
        )

    def get_descriptor(self) -> CapabilityDescriptor:
        return self._descriptor

    def invoke(self, invocation: Any) -> Any:
        """Invoke the wrapped tool."""
        args = invocation.inputs
        # Add task_id if available
        if hasattr(invocation, 'intent_id'):
            args = {**args, "task_id": invocation.intent_id}
        return self.tool_handler(args)

    def verify(self, invocation: Any, result: Any) -> bool:
        """Verify tool result."""
        return result is not None


class ToolManager:
    """
    Bridges kernel capability system with existing AetherOS tool registry.
    
    Registers tools as capabilities and enforces authorization.
    """

    def __init__(self, config, event_bus: EventBus, capability_manager):
        self.config = config
        self.event_bus = event_bus
        self.capability_manager = capability_manager
        self._lock = threading.RLock()
        
        self._tool_mappings: Dict[str, ToolCapabilityMapping] = {}
        self._tool_handlers: Dict[str, Callable] = {}
        self._tool_schemas: Dict[str, Dict[str, Any]] = {}

    def register_tool(
        self,
        tool_name: str,
        handler: Callable,
        schema: Dict[str, Any],
        capability_descriptor: CapabilityDescriptor = None,
    ) -> None:
        """Register a tool as a capability."""
        with self._lock:
            self._tool_handlers[tool_name] = handler
            self._tool_schemas[tool_name] = schema

            # Create capability descriptor if not provided
            if capability_descriptor is None:
                capability_descriptor = CapabilityDescriptor(
                    capability_id=f"tool.{tool_name}",
                    version="1.0.0",
                    provider="aetheros.tools",
                    description=schema.get("description", f"Tool: {tool_name}"),
                    inputs=schema.get("parameters", {}),
                    outputs={"type": "object"},
                    side_effects=self._infer_risk_level(tool_name, schema),
                    required_authority=[f"tool.{tool_name}"],
                    required_resources=ResourceBudget(),
                    required_credentials=self._infer_credentials(tool_name),
                    network_access=self._requires_network(tool_name),
                    filesystem_access=self._requires_filesystem(tool_name),
                    device_access=self._requires_device(tool_name),
                    data_classification=DataClassification.INTERNAL,
                    reversibility=self._is_reversible(tool_name),
                    idempotency=self._is_idempotent(tool_name),
                    latency_class="normal",
                    cost_class="free",
                    sandbox_support=True,
                    verification_strategy="observe",
                    tags=["tool", tool_name],
                )

            # Create provider
            provider = ToolCapabilityProvider(tool_name, handler, schema)
            
            # Register with capability manager
            self.capability_manager.register(capability_descriptor, provider)

            # Store mapping
            self._tool_mappings[tool_name] = ToolCapabilityMapping(
                tool_name=tool_name,
                capability_id=capability_descriptor.capability_id,
                capability_descriptor=capability_descriptor,
                tool_schema=schema,
            )

        if self.event_bus:
            self.event_bus.emit("tool.registered", {
                "tool_name": tool_name,
                "capability_id": capability_descriptor.capability_id,
            })

        logger.debug("ToolManager: registered tool %s as capability %s",
                     tool_name, capability_descriptor.capability_id)

    def _infer_risk_level(self, tool_name: str, schema: Dict) -> List[CapabilityRiskLevel]:
        """Infer risk level from tool name and schema."""
        risks = [CapabilityRiskLevel.READ_ONLY]
        
        # File mutating tools
        if any(x in tool_name for x in ["write", "delete", "remove", "patch", "edit"]):
            risks.append(CapabilityRiskLevel.IRREVERSIBLE)
        
        # Network tools
        if any(x in tool_name for x in ["web", "network", "http", "fetch", "browser"]):
            risks.append(CapabilityRiskLevel.EXTERNAL_SIDE_EFFECT)
        
        # Process execution
        if any(x in tool_name for x in ["exec", "terminal", "shell", "process", "run"]):
            risks.append(CapabilityRiskLevel.EXTERNAL_SIDE_EFFECT)
            risks.append(CapabilityRiskLevel.SECURITY_CRITICAL)
        
        # Computer control
        if any(x in tool_name for x in ["computer", "click", "type", "keyboard", "mouse"]):
            risks.append(CapabilityRiskLevel.PHYSICAL)
            risks.append(CapabilityRiskLevel.EXTERNAL_SIDE_EFFECT)
        
        # Device control
        if "device" in tool_name or "robot" in tool_name:
            risks.append(CapabilityRiskLevel.PHYSICAL)
        
        # Financial
        if any(x in tool_name for x in ["pay", "transfer", "buy", "sell", "trade"]):
            risks.append(CapabilityRiskLevel.FINANCIAL)
        
        return list(set(risks))

    def _infer_credentials(self, tool_name: str) -> List[str]:
        """Infer required credentials from tool name."""
        creds = []
        if "github" in tool_name:
            creds.append("GITHUB_TOKEN")
        if "gitlab" in tool_name:
            creds.append("GITLAB_TOKEN")
        if "aws" in tool_name:
            creds.append("AWS_CREDENTIALS")
        if "gcp" in tool_name or "google" in tool_name:
            creds.append("GCP_CREDENTIALS")
        if "azure" in tool_name:
            creds.append("AZURE_CREDENTIALS")
        if "docker" in tool_name:
            creds.append("DOCKER_CREDENTIALS")
        if "kubernetes" in tool_name or "k8s" in tool_name:
            creds.append("KUBECONFIG")
        if "slack" in tool_name:
            creds.append("SLACK_TOKEN")
        if "discord" in tool_name:
            creds.append("DISCORD_TOKEN")
        if "telegram" in tool_name:
            creds.append("TELEGRAM_TOKEN")
        return creds

    def _requires_network(self, tool_name: str) -> bool:
        """Check if tool requires network access."""
        return any(x in tool_name for x in [
            "web", "network", "http", "fetch", "browser", "search",
            "github", "gitlab", "api", "rest", "graphql", "grpc"
        ])

    def _requires_filesystem(self, tool_name: str) -> bool:
        """Check if tool requires filesystem access."""
        return any(x in tool_name for x in [
            "fs", "file", "read", "write", "delete", "patch", "edit",
            "glob", "ls", "find", "cat", "head", "tail"
        ])

    def _requires_device(self, tool_name: str) -> bool:
        """Check if tool requires device access."""
        return any(x in tool_name for x in [
            "device", "computer", "robot", "sensor", "actuator",
            "click", "type", "keyboard", "mouse", "screen"
        ])

    def _is_reversible(self, tool_name: str) -> bool:
        """Check if tool operation is reversible."""
        irreversible = ["delete", "remove", "rm", "drop", "destroy", "terminate"]
        return not any(x in tool_name for x in irreversible)

    def _is_idempotent(self, tool_name: str) -> bool:
        """Check if tool operation is idempotent."""
        idempotent = ["read", "get", "list", "ls", "find", "search", "cat", "head", "tail", "stat"]
        return any(x in tool_name for x in idempotent)

    def discover_tools(self) -> int:
        """Discover and register tools from the existing tool registry."""
        try:
            from tools.registry import registry
            from model_tools import get_tool_definitions

            # Get all tool definitions (None = all toolsets; [] would select none)
            tool_defs = get_tool_definitions(None, None, True)
            
            count = 0
            for tool_def in tool_defs:
                # Definitions are OpenAI function format:
                # {"type": "function", "function": {"name": ..., ...}}
                # but accept flat {"name": ...} as well.
                fn = tool_def.get("function", tool_def)
                tool_name = fn.get("name") or tool_def.get("name")
                if tool_name and tool_name not in self._tool_mappings:
                    # Get handler from registry
                    entry = registry.get_entry(tool_name)
                    if entry is not None and getattr(entry, "handler", None):
                        self.register_tool(tool_name, entry.handler, fn)
                        count += 1
            
            logger.info("ToolManager: discovered %d tools", count)
            return count
            
        except Exception as exc:
            logger.error("Tool discovery failed: %s", exc)
            return 0

    def get_tool_handler(self, tool_name: str) -> Optional[Callable]:
        """Get tool handler."""
        with self._lock:
            return self._tool_handlers.get(tool_name)

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool schema."""
        with self._lock:
            return self._tool_schemas.get(tool_name)

    def get_capability_id(self, tool_name: str) -> Optional[str]:
        """Get capability ID for a tool."""
        mapping = self._tool_mappings.get(tool_name)
        return mapping.capability_id if mapping else None

    def list_tools(self) -> List[str]:
        """List all registered tools."""
        with self._lock:
            return list(self._tool_handlers.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get tool manager statistics."""
        with self._lock:
            total = len(self._tool_mappings)
            by_risk: Dict[str, int] = {}
            
            for mapping in self._tool_mappings.values():
                for risk in mapping.capability_descriptor.side_effects:
                    by_risk[risk.value] = by_risk.get(risk.value, 0) + 1

        return {
            "total_tools": total,
            "by_risk_level": by_risk,
        }

    def shutdown(self) -> None:
        """Shutdown the tool manager."""
        logger.info("ToolManager: shutting down")
        with self._lock:
            self._tool_mappings.clear()
            self._tool_handlers.clear()
            self._tool_schemas.clear()