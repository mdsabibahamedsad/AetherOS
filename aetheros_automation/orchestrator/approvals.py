from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    Plan, ApprovalRequest, ApprovalResponse, RiskLevel, OrchestrationTask,
    TaskStatus,
)
from aetheros_automation.orchestrator.events import EventBus

logger = logging.getLogger(__name__)

APPROVAL_CATEGORIES = {
    "dangerous_action": "This action could be dangerous or destructive",
    "destructive_action": "This action will permanently modify or delete data",
    "sensitive_data": "This action involves sensitive or personal data",
    "external_communication": "This action will communicate with external parties",
    "payment": "This action involves payment or financial transactions",
    "account_change": "This action will modify account settings",
    "permission_escalation": "This action requires elevated permissions",
    "uncertain_decision": "The system is uncertain about the best course of action",
}


class ApprovalManager:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._requests: dict[str, ApprovalRequest] = {}
        self._pending: dict[str, asyncio.Future] = {}
        self._session_approvals: dict[str, set[str]] = {}

    def register_plan_approvals(self, plan: Plan):
        for task in plan.tasks:
            if task.requires_approval:
                request = ApprovalRequest(
                    plan_id=plan.id,
                    task_id=task.id,
                    action=task.name,
                    description=task.description,
                    reason=self._get_approval_reason(task),
                    risk_level=task.risk_level,
                    status="pending",
                )
                self._requests[request.id] = request
                task.approval_status = "pending"
                self.event_bus.emit("approval.requested", {
                    "request_id": request.id,
                    "plan_id": plan.id,
                    "task_id": task.id,
                    "action": request.action,
                    "description": request.description,
                    "reason": request.reason,
                    "risk_level": request.risk_level.value if hasattr(request.risk_level, 'value') else str(request.risk_level),
                })

    def request_approval(
        self,
        plan_id: str,
        action: str,
        description: str,
        reason: str = "",
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        data_affected: str = "",
        agent_id: str = "",
        task_id: str = "",
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            plan_id=plan_id,
            task_id=task_id,
            agent_id=agent_id,
            action=action,
            description=description,
            reason=reason,
            risk_level=risk_level,
            data_affected=data_affected,
            status="pending",
        )
        self._requests[request.id] = request
        future: asyncio.Future = asyncio.Future()
        self._pending[request.id] = future
        self.event_bus.emit("approval.requested", {
            "request_id": request.id,
            "plan_id": plan_id,
            "action": action,
            "description": description,
            "reason": reason,
            "risk_level": risk_level.value if hasattr(risk_level, 'value') else str(risk_level),
            "data_affected": data_affected,
        })
        return request

    async def wait_for_response(
        self, request_id: str, timeout: float = 300.0
    ) -> Optional[ApprovalResponse]:
        future = self._pending.get(request_id)
        if not future:
            return None
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            return None

    def respond(self, response: ApprovalResponse) -> bool:
        request = self._requests.get(response.request_id)
        if not request or request.status != "pending":
            return False
        request.status = "responded"
        request.response = "approved" if response.approved else "denied"
        request.responded_at = time.time()
        request.responded_by = response.user_id
        if response.duration == "session":
            if response.user_id not in self._session_approvals:
                self._session_approvals[response.user_id] = set()
            self._session_approvals[response.user_id].add(request.action)
        future = self._pending.get(response.request_id)
        if future and not future.done():
            future.set_result(response)
        self.event_bus.emit("approval.responded", {
            "request_id": response.request_id,
            "approved": response.approved,
            "user_id": response.user_id,
            "duration": response.duration,
        })
        return True

    def get_pending_requests(self, plan_id: str = "") -> list[ApprovalRequest]:
        requests = [
            r for r in self._requests.values() if r.status == "pending"
        ]
        if plan_id:
            requests = [r for r in requests if r.plan_id == plan_id]
        return sorted(requests, key=lambda r: r.created_at)

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def check_session_approval(self, user_id: str, action: str) -> bool:
        approvals = self._session_approvals.get(user_id, set())
        return action in approvals

    def _get_approval_reason(self, task: OrchestrationTask) -> str:
        risk_map = {
            RiskLevel.CRITICAL: APPROVAL_CATEGORIES["dangerous_action"],
            RiskLevel.HIGH: APPROVAL_CATEGORIES["destructive_action"],
            RiskLevel.MEDIUM: APPROVAL_CATEGORIES["sensitive_data"],
            RiskLevel.LOW: APPROVAL_CATEGORIES["uncertain_decision"],
        }
        return risk_map.get(task.risk_level, APPROVAL_CATEGORIES["uncertain_decision"])

    def get_stats(self) -> dict:
        total = len(self._requests)
        pending = len([r for r in self._requests.values() if r.status == "pending"])
        approved = len([r for r in self._requests.values() if r.response == "approved"])
        denied = len([r for r in self._requests.values() if r.response == "denied"])
        return {
            "total_requests": total,
            "pending": pending,
            "approved": approved,
            "denied": denied,
        }
