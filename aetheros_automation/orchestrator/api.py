"""API layer for the orchestrator - exposes REST-like interface."""

from __future__ import annotations

import logging
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    Objective, Plan, OrchestrationResult, TaskTemplate,
    TemplateCategory, NLCommand, AgentRole, ApprovalResponse,
    OrchestratorState, ExecutionStats,
)

logger = logging.getLogger(__name__)


class OrchestratorAPI:
    def __init__(self, orchestrator):
        self._orch = orchestrator

    async def submit_goal(self, goal: str, **kwargs) -> dict:
        objective = Objective(
            goal=goal,
            context=kwargs.get("context", {}),
            constraints=kwargs.get("constraints", []),
            priority=kwargs.get("priority"),
            output_format=kwargs.get("output_format", ""),
            max_budget=kwargs.get("max_budget", 0.0),
        )
        result = await self._orch.submit_objective(objective)
        return self._result_to_dict(result)

    async def submit_nl(self, text: str) -> dict:
        result = await self._orch.submit_nl(text)
        return self._result_to_dict(result)

    def get_plan(self, plan_id: str) -> Optional[dict]:
        plan = self._orch.get_plan(plan_id)
        if not plan:
            return None
        return self._plan_to_dict(plan)

    def list_plans(self, status: str = "", limit: int = 50) -> list[dict]:
        plans = self._orch.list_plans(
            status=status if status else None, limit=limit
        )
        return [self._plan_to_dict(p) for p in plans]

    async def pause(self, plan_id: str) -> dict:
        success = await self._orch.pause_plan(plan_id)
        return {"success": success, "plan_id": plan_id}

    async def resume(self, plan_id: str) -> dict:
        success = await self._orch.resume_plan(plan_id)
        return {"success": success, "plan_id": plan_id}

    async def cancel(self, plan_id: str) -> dict:
        success = await self._orch.cancel_plan(plan_id)
        return {"success": success, "plan_id": plan_id}

    async def retry_task(self, plan_id: str, task_id: str) -> dict:
        success = await self._orch.retry_task(plan_id, task_id)
        return {"success": success, "plan_id": plan_id, "task_id": task_id}

    def approve_request(self, request_id: str, approved: bool = True,
                        user_id: str = "", duration: str = "once") -> dict:
        response = ApprovalResponse(
            request_id=request_id,
            approved=approved,
            user_id=user_id,
            duration=duration,
        )
        success = self._orch.approval_manager.respond(response)
        return {"success": success, "request_id": request_id, "approved": approved}

    def get_pending_approvals(self, plan_id: str = "") -> list[dict]:
        requests = self._orch.approval_manager.get_pending_requests(plan_id)
        return [
            {
                "id": r.id,
                "plan_id": r.plan_id,
                "task_id": r.task_id,
                "action": r.action,
                "description": r.description,
                "reason": r.reason,
                "risk_level": r.risk_level.value if hasattr(r.risk_level, 'value') else str(r.risk_level),
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in requests
        ]

    def list_templates(self, category: str = "") -> list[dict]:
        cat = None
        if category:
            for c in TemplateCategory:
                if c.value == category:
                    cat = c
                    break
        templates = self._orch.template_manager.list_templates(cat)
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category.value if hasattr(t.category, 'value') else str(t.category),
                "estimated_duration": t.estimated_duration,
                "estimated_cost": t.estimated_cost,
                "risk_level": t.risk_level.value if hasattr(t.risk_level, 'value') else str(t.risk_level),
                "tags": t.tags,
                "is_builtin": t.is_builtin,
                "usage_count": t.usage_count,
            }
            for t in templates
        ]

    def get_template(self, template_id: str) -> Optional[dict]:
        template = self._orch.template_manager.get_template(template_id)
        if not template:
            return None
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category.value if hasattr(template.category, 'value') else str(template.category),
            "steps": [
                {
                    "description": s.description,
                    "agent_role": s.agent_role.value if hasattr(s.agent_role, 'value') else str(s.agent_role),
                    "tools": s.tools,
                    "estimated_duration": s.estimated_duration,
                    "requires_approval": s.requires_approval,
                }
                for s in template.steps
            ],
            "required_tools": template.required_tools,
            "required_permissions": template.required_permissions,
            "estimated_duration": template.estimated_duration,
            "risk_level": template.risk_level.value if hasattr(template.risk_level, 'value') else str(template.risk_level),
            "tags": template.tags,
            "is_builtin": template.is_builtin,
            "usage_count": template.usage_count,
        }

    async def create_from_template(self, template_id: str,
                                    variables: dict = None) -> dict:
        plan = self._orch.template_manager.create_from_template(
            template_id, variables
        )
        if not plan:
            return {"success": False, "error": "Template not found"}
        result = await self._orch.execute_plan(plan)
        return self._result_to_dict(result)

    def get_agents(self) -> list[dict]:
        definitions = self._orch.agent_manager.list_definitions()
        return [
            {
                "role": d.role.value if hasattr(d.role, 'value') else str(d.role),
                "name": d.name,
                "description": d.description,
                "tools": d.tools,
                "permissions": d.permissions,
                "max_sub_agents": d.max_sub_agents,
                "memory_enabled": d.memory_enabled,
            }
            for d in definitions
        ]

    def get_active_agents(self) -> list[dict]:
        instances = self._orch.agent_manager.list_active_agents()
        return [
            {
                "id": inst.id,
                "role": inst.definition.role.value if hasattr(inst.definition.role, 'value') else str(inst.definition.role),
                "name": inst.definition.name,
                "status": inst.status,
                "current_task_id": inst.current_task_id,
                "parent_id": inst.parent_id,
            }
            for inst in instances
        ]

    def get_model_routes(self) -> list[dict]:
        return self._orch.model_router.list_available_routes()

    def get_events(self, event_filter: str = "", limit: int = 100) -> list[dict]:
        return self._orch.event_bus.get_history(
            event_filter=event_filter, limit=limit
        )

    def get_graph(self, plan_id: str) -> Optional[dict]:
        plan = self._orch.get_plan(plan_id)
        if not plan:
            return None
        graph = plan.execution_graph
        if not graph:
            from aetheros_automation.orchestrator.graph import ExecutionGraphEngine
            engine = ExecutionGraphEngine()
            graph = engine.build_from_plan(plan)
            plan.execution_graph = graph
        return {
            "nodes": [
                {
                    "id": n.id,
                    "task_id": n.task_id,
                    "node_type": n.node_type.value if hasattr(n.node_type, 'value') else str(n.node_type),
                    "label": n.label,
                    "status": n.status.value if hasattr(n.status, 'value') else str(n.status),
                    "level": n.level,
                    "metadata": n.metadata,
                }
                for n in graph.nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "edge_type": e.edge_type,
                    "condition": e.condition,
                    "label": e.label,
                }
                for e in graph.edges
            ],
            "levels": graph.levels,
        }

    def get_sub_agents(self, parent_id: str = "") -> list[dict]:
        if parent_id:
            instances = self._orch.sub_agent_manager.get_sub_agents(parent_id)
        else:
            instances = self._orch.sub_agent_manager.get_active_sub_agents()
        return [
            {
                "id": inst.id,
                "role": inst.definition.role.value if hasattr(inst.definition.role, 'value') else str(inst.definition.role),
                "name": inst.definition.name,
                "status": inst.status,
                "parent_id": inst.parent_id,
                "current_task_id": inst.current_task_id,
            }
            for inst in instances
        ]

    async def parse_nl(self, text: str) -> dict:
        command = self._orch.nlp.parse(text)
        return {
            "intent": command.intent,
            "goal": command.goal,
            "schedule": command.schedule,
            "agents": [
                a.value if hasattr(a, 'value') else str(a) for a in command.agents
            ],
            "tools": command.tools,
            "permissions": command.permissions,
            "output_format": command.output_format,
            "constraints": command.constraints,
        }

    def get_stats(self) -> dict:
        stats = self._orch.get_stats()
        return {
            "total_plans": stats.total_plans,
            "completed_plans": stats.completed_plans,
            "failed_plans": stats.failed_plans,
            "running_plans": stats.running_plans,
            "total_tasks": stats.total_tasks,
            "completed_tasks": stats.completed_tasks,
            "failed_tasks": stats.failed_tasks,
            "avg_duration": stats.avg_duration,
            "agent_stats": self._orch.agent_manager.get_agent_stats(),
            "sub_agent_stats": self._orch.sub_agent_manager.get_stats(),
            "approval_stats": self._orch.approval_manager.get_stats(),
            "event_stats": self._orch.event_bus.get_stats(),
            "memory_stats": self._orch.memory.get_stats(),
            "template_stats": self._orch.template_manager.get_stats(),
            "limits": self._orch.limits_manager.get_stats(),
        }

    def get_status(self) -> dict:
        return self._orch.get_status()

    def _plan_to_dict(self, plan: Plan) -> dict:
        return {
            "id": plan.id,
            "goal": plan.goal,
            "status": plan.status,
            "steps": [
                {
                    "description": s.description,
                    "agent_role": s.agent_role.value if hasattr(s.agent_role, 'value') else str(s.agent_role),
                    "tools": s.tools,
                    "estimated_duration": s.estimated_duration,
                    "estimated_cost": s.estimated_cost,
                    "risk_level": s.risk_level.value if hasattr(s.risk_level, 'value') else str(s.risk_level),
                    "requires_approval": s.requires_approval,
                    "parallelizable": s.parallelizable,
                }
                for s in (plan.steps or [])
            ],
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "task_type": t.task_type.value if hasattr(t.task_type, 'value') else str(t.task_type),
                    "status": t.status.value if hasattr(t.status, 'value') else str(t.status),
                    "agent_role": t.agent_role.value if hasattr(t.agent_role, 'value') else str(t.agent_role),
                    "dependencies": t.dependencies,
                    "progress": t.progress,
                    "error": t.error,
                    "retry_count": t.retry_count,
                    "estimated_duration": t.estimated_duration,
                    "estimated_cost": t.estimated_cost,
                    "requires_approval": t.requires_approval,
                    "approval_status": getattr(t, 'approval_status', ""),
                }
                for t in (plan.tasks or [])
            ],
            "estimated_time": plan.estimated_time,
            "estimated_cost": plan.estimated_cost,
            "risk_level": plan.risk_level.value if hasattr(plan.risk_level, 'value') else str(plan.risk_level),
            "created_at": plan.created_at,
            "started_at": plan.started_at,
            "completed_at": plan.completed_at,
            "error": plan.error,
            "metadata": plan.metadata,
        }

    def _result_to_dict(self, result: OrchestrationResult) -> dict:
        return {
            "success": result.success,
            "plan_id": result.plan_id,
            "status": result.status,
            "tasks_completed": result.tasks_completed,
            "tasks_failed": result.tasks_failed,
            "total_duration": result.total_duration,
            "total_cost": result.total_cost,
            "error": result.error,
            "errors": result.errors,
        }
