"""Web API — JSON endpoints for web-based node editor and workflow management."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from workflows.store import WorkflowStore
from workflows.engine import WorkflowEngine
from workflows.models import (WorkflowConfig, WorkflowNode, Connection,
                               WorkflowStatus, ExecutionStatus, NodeCategory)
from workflows.nodes.base import NodeRegistry

logger = logging.getLogger(__name__)


class WorkflowAPI:
    """JSON API for web-based workflow editor and management."""

    def __init__(self, store: Optional[WorkflowStore] = None):
        self.store = store or WorkflowStore()
        self.engine = WorkflowEngine(store)

    # ---- Workflow CRUD ----

    def list_workflows(self, status: str = None) -> list[dict]:
        workflows = self.store.list_workflows()
        if status:
            workflows = [w for w in workflows
                         if hasattr(w.status, 'value') and w.status.value == status]
        return [self._wf_to_dict(w) for w in workflows]

    def get_workflow(self, workflow_id: str) -> Optional[dict]:
        wf = self.store.get_workflow(workflow_id)
        return self._wf_to_dict(wf) if wf else None

    def create_workflow(self, data: dict) -> dict:
        wf = WorkflowConfig(
            name=data.get("name", "Untitled Workflow"),
            description=data.get("description", ""),
            schedule=data.get("schedule", ""),
            tags=data.get("tags", []),
            nodes=[WorkflowNode(**n) if isinstance(n, dict)
                   else n for n in data.get("nodes", [])],
            connections=[Connection(**c) if isinstance(c, dict)
                         else c for c in data.get("connections", [])],
        )
        if data.get("status"):
            try:
                wf.status = WorkflowStatus(data["status"])
            except ValueError:
                pass
        saved = self.store.save_workflow(wf)
        return self._wf_to_dict(saved)

    def update_workflow(self, workflow_id: str, data: dict) -> Optional[dict]:
        wf = self.store.get_workflow(workflow_id)
        if not wf:
            return None
        if "name" in data:
            wf.name = data["name"]
        if "description" in data:
            wf.description = data["description"]
        if "schedule" in data:
            wf.schedule = data["schedule"]
        if "tags" in data:
            wf.tags = list(data["tags"])
        if "status" in data:
            try:
                wf.status = WorkflowStatus(data["status"])
            except ValueError:
                pass
        if "nodes" in data:
            wf.nodes = [WorkflowNode(**n) if isinstance(n, dict)
                        else n for n in data["nodes"]]
        if "connections" in data:
            wf.connections = [Connection(**c) if isinstance(c, dict)
                              else c for c in data["connections"]]
        self.store.update_workflow(wf)
        return self._wf_to_dict(wf)

    def delete_workflow(self, workflow_id: str) -> bool:
        return self.store.delete_workflow(workflow_id)

    def duplicate_workflow(self, workflow_id: str, new_name: str = None) -> Optional[dict]:
        import copy
        wf = self.store.get_workflow(workflow_id)
        if not wf:
            return None
        new_wf = copy.deepcopy(wf)
        new_wf.id = None
        new_wf.name = new_name or f"{wf.name} (Copy)"
        saved = self.store.save_workflow(new_wf)
        return self._wf_to_dict(saved)

    # ---- Execution ----

    def run_workflow(self, workflow_id: str, context: dict = None) -> dict:
        try:
            record = self.engine.run(workflow_id, context)
            return self._rec_to_dict(record)
        except Exception as e:
            return {"error": str(e)}

    def list_executions(self, workflow_id: str = None, limit: int = 50) -> list[dict]:
        records = self.store.list_executions(workflow_id=workflow_id, limit=limit)
        return [self._rec_to_dict(r) for r in records]

    def get_execution(self, execution_id: str) -> Optional[dict]:
        rec = self.store.get_execution(execution_id)
        return self._rec_to_dict(rec) if rec else None

    # ---- Node Registry ----

    def get_node_types(self, category: str = None) -> list[dict]:
        NodeRegistry.discover()
        if category:
            nodes = NodeRegistry.get_by_category(category)
        else:
            nodes = list(NodeRegistry.get_all().values())
        return [{
            "type": n.type,
            "category": n.category,
            "label": n.label,
            "description": n.description,
            "default_config": getattr(n, "default_config", {}),
            "inputs": getattr(n, "inputs", []),
            "outputs": getattr(n, "outputs", []),
        } for n in nodes]

    def get_node_categories(self) -> list[dict]:
        NodeRegistry.discover()
        categories = {}
        for node in NodeRegistry.get_all().values():
            cat = node.category
            if cat not in categories:
                categories[cat] = {"id": cat, "label": cat.title(), "count": 0}
            categories[cat]["count"] += 1
        return list(categories.values())

    # ---- Marketplace ----

    def list_marketplace(self, category: str = None) -> list[dict]:
        from workflows.marketplace import MARKETPLACE_WORKFLOWS
        if category:
            return [w for w in MARKETPLACE_WORKFLOWS if w.get("category") == category]
        return list(MARKETPLACE_WORKFLOWS)

    def install_marketplace(self, marketplace_id: str, name: str = None) -> Optional[dict]:
        from workflows.marketplace import WorkflowMarketplace
        mp = WorkflowMarketplace(self.store)
        wf_id = mp.install_from_marketplace(marketplace_id, name)
        if wf_id:
            return self.get_workflow(wf_id)
        return None

    # ---- Dashboard Stats ----

    def get_stats(self) -> dict:
        workflows = self.store.list_workflows()
        records = self.store.list_executions(limit=1000)
        NodeRegistry.discover()
        return {
            "total_workflows": len(workflows),
            "active_workflows": len([w for w in workflows
                                     if w.status == WorkflowStatus.ACTIVE]),
            "scheduled_workflows": len([w for w in workflows if w.schedule]),
            "total_executions": len(records),
            "successful_executions": len([r for r in records
                                          if r.status == ExecutionStatus.COMPLETED]),
            "failed_executions": len([r for r in records
                                      if r.status == ExecutionStatus.FAILED]),
            "node_types": len(NodeRegistry.get_all()),
        }

    # ---- Helpers ----

    def _wf_to_dict(self, wf: WorkflowConfig) -> dict:
        return {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "schedule": wf.schedule,
            "status": wf.status.value if hasattr(wf.status, 'value') else wf.status,
            "version": wf.version,
            "author": wf.author,
            "tags": list(wf.tags),
            "owner": wf.owner,
            "error_policy": wf.error_policy,
            "nodes": [n.to_dict() for n in wf.nodes],
            "connections": [c.to_dict() for c in wf.connections],
            "created_at": wf.created_at.isoformat() if wf.created_at else None,
            "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
        }

    def _rec_to_dict(self, rec) -> dict:
        return {
            "id": rec.id,
            "workflow_id": rec.workflow_id,
            "status": rec.status.value if hasattr(rec.status, 'value') else rec.status,
            "started_at": rec.started_at.isoformat() if rec.started_at else None,
            "completed_at": rec.completed_at.isoformat() if rec.completed_at else None,
            "duration": rec.duration,
            "error": rec.error,
            "triggered_by": rec.triggered_by,
            "steps": rec.steps,
            "final_output": str(rec.final_output)[:500] if rec.final_output else None,
        }
