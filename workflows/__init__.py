"""Workflow Studio — visual DAG-based workflow engine for Aetheros."""

from __future__ import annotations

from typing import Optional

from workflows.models import (WorkflowConfig, WorkflowNode, Connection,
                               WorkflowStatus, ExecutionStatus,
                               NodeCategory, TriggerType, AINodeType,
                               LogicType, ActionType, AgentNodeType,
                               MCPNodeType)
from workflows.store import WorkflowStore
from workflows.engine import WorkflowEngine
from workflows.nodes.base import NodeRegistry, BaseNode, NodeResult
from workflows.scheduler import WorkflowScheduler
from workflows.executor import WorkflowExecutor, ExecutorDaemon
from workflows.logging import WorkflowLogStore
from workflows.marketplace import WorkflowMarketplace
from workflows.templates import get_template, list_templates, create_from_template

import logging  # noqa: E402  (imported after workflows.logging so stdlib wins)

logger = logging.getLogger(__name__)

_store_instance: Optional[WorkflowStore] = None
_engine_instance: Optional[WorkflowEngine] = None


def get_store() -> WorkflowStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = WorkflowStore()
    return _store_instance


def get_engine() -> WorkflowEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = WorkflowEngine(get_store())
    return _engine_instance


def init_workflow_system() -> None:
    """Initialize the workflow system — DB, node discovery, scheduler sync."""
    logger.info("Initializing workflow system...")
    store = get_store()
    NodeRegistry.discover()
    logger.info("Discovered %d node types", len(NodeRegistry.get_all()))
    try:
        scheduler = WorkflowScheduler(store)
        added, removed = scheduler.sync_schedules()
        logger.info("Workflow schedules synced: +%d added, -%d removed", added, removed)
    except Exception as e:
        logger.warning("Schedule sync failed (non-fatal): %s", e)
    from workflows.logging import WorkflowLogStore
    log_store = WorkflowLogStore()
    log_store.info("system", "Workflow system initialized",
                   category="system")
    logger.info("Workflow system initialized")


def discover_nodes() -> dict:
    NodeRegistry.discover()
    return NodeRegistry.get_all()


__all__ = [
    "WorkflowConfig", "WorkflowNode", "Connection",
    "WorkflowStatus", "ExecutionStatus",
    "NodeCategory", "TriggerType", "AINodeType", "LogicType",
    "ActionType", "AgentNodeType", "MCPNodeType",
    "WorkflowStore", "WorkflowEngine",
    "NodeRegistry", "BaseNode", "NodeResult",
    "WorkflowScheduler", "WorkflowExecutor", "ExecutorDaemon",
    "WorkflowLogStore", "WorkflowMarketplace",
    "get_template", "list_templates", "create_from_template",
    "get_store", "get_engine", "init_workflow_system", "discover_nodes",
]
