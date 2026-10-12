#!/usr/bin/env python3
"""
AetherOS Capability Kernel — Unified Capability System

This module provides the central capability abstraction layer that sits above
the existing tool registry. It maps user goals to executable capabilities,
handles permission checks, routes to appropriate models/tools, and manages
the execution lifecycle with observation, verification, and recovery.

Key components:
- CapabilityRegistry: Maps capabilities to tools/models/providers
- CommandGateway: Single normalized entry point for all user requests
- TaskModel: Unified task representation with full lifecycle state
- PermissionModel: Risk-based permission system with approval gates
- ExecutionEngine: Execute → Observe → Verify → Recover loop
- CapabilityRouter: Selects optimal tool/model combination for a goal
"""

from typing import Any, Dict

from .capability_registry import CapabilityRegistry, CapabilityEntry, CapabilityCategory
from .command_gateway import CommandGateway, TaskRequest, TaskSource
from .task_model import Task, TaskState, TaskStep, TaskProgress
from .permission_model import PermissionModel, RiskLevel, PermissionDecision
from .execution_engine import ExecutionEngine, ExecutionResult
from .capability_router import CapabilityRouter, RoutingDecision
from .planner import get_parameterizer, get_planner, Parameterizer, Planner, ParameterizationResult, Plan, PlanStep
from .models import (
    CapabilitySpec,
    CapabilityProvider,
    ToolReference,
    ModelReference,
    VerificationStrategy,
    RecoveryStrategy,
)

__all__ = [
    "CapabilityRegistry",
    "CapabilityEntry",
    "CapabilityCategory",
    "CommandGateway",
    "TaskRequest",
    "TaskSource",
    "Task",
    "TaskState",
    "TaskStep",
    "TaskProgress",
    "PermissionModel",
    "RiskLevel",
    "PermissionDecision",
    "ExecutionEngine",
    "ExecutionResult",
    "CapabilityRouter",
    "RoutingDecision",
    "CapabilitySpec",
    "CapabilityProvider",
    "ToolReference",
    "ModelReference",
    "VerificationStrategy",
    "RecoveryStrategy",
    "get_parameterizer",
    "get_planner",
    "Parameterizer",
    "Planner",
    "ParameterizationResult",
    "Plan",
    "PlanStep",
]

# Module-level singleton instances (initialized on first access)
_registry: CapabilityRegistry | None = None
_gateway: CommandGateway | None = None
_permission_model: PermissionModel | None = None
_execution_engine: ExecutionEngine | None = None
_router: CapabilityRouter | None = None


def get_capability_registry() -> CapabilityRegistry:
    """Get the global capability registry singleton."""
    global _registry
    if _registry is None:
        _registry = CapabilityRegistry()
    return _registry


def get_command_gateway() -> CommandGateway:
    """Get the global command gateway singleton."""
    global _gateway
    if _gateway is None:
        _gateway = CommandGateway()
    return _gateway


def get_permission_model() -> PermissionModel:
    """Get the global permission model singleton."""
    global _permission_model
    if _permission_model is None:
        _permission_model = PermissionModel()
    return _permission_model


def get_execution_engine() -> ExecutionEngine:
    """Get the global execution engine singleton."""
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()
    return _execution_engine


def get_capability_router() -> CapabilityRouter:
    """Get the global capability router singleton."""
    global _router
    if _router is None:
        _router = CapabilityRouter()
    return _router


def get_parameterizer(config: Dict[str, Any] | None = None) -> "Parameterizer":
    """Get the global parameterizer singleton."""
    from .planner import get_parameterizer as _get_parameterizer
    return _get_parameterizer(config)


def get_planner(config: Dict[str, Any] | None = None) -> "Planner":
    """Get the global planner singleton."""
    from .planner import get_planner as _get_planner
    return _get_planner(config)


def initialize_capability_kernel(config: dict | None = None) -> None:
    """Initialize all capability kernel components with optional config."""
    global _registry, _gateway, _permission_model, _execution_engine, _router
    
    _registry = CapabilityRegistry(config)
    _permission_model = PermissionModel(config)
    _execution_engine = ExecutionEngine(config)
    _router = CapabilityRouter(config)
    _gateway = CommandGateway(config)
    
    # Register built-in capabilities from existing tool registry
    _registry.discover_and_register_capabilities()
    
    # Register recovery strategies
    _execution_engine.register_default_recovery_strategies()
    
    # Register verification strategies
    _execution_engine.register_default_verification_strategies()