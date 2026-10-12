"""
Human Oversight Manager — human approval as a kernel primitive.

Supports approval requests, grants, denials, expiration, delegation, and remember.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Set
from collections import defaultdict
from enum import Enum

from kernel.core.types import (
    ApprovalStatus,
    ApprovalResponse,
    CapabilityRiskLevel,
    DataClassification,
    ProvenanceType,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ApprovalType(Enum):
    """Types of approval requests."""
    CAPABILITY_USE = "capability_use"
    DATA_ACCESS = "data_access"
    NETWORK_EGRESS = "network_egress"
    FILESYSTEM_WRITE = "filesystem_write"
    FILESYSTEM_DELETE = "filesystem_delete"
    PROCESS_EXECUTION = "process_execution"
    AGENT_DELEGATION = "agent_delegation"
    AUTOMATION_CREATE = "automation_create"
    PHYSICAL_ACTION = "physical_action"
    FINANCIAL_TRANSACTION = "financial_transaction"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    EXTERNAL_COMMUNICATION = "external_communication"
    CUSTOM = "custom"


@dataclass
class ApprovalRequest:
    """A human approval request."""
    request_id: str
    approval_type: ApprovalType
    agent_id: str
    task_id: str = ""
    intent_id: str = ""
    capability_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    risk_level: CapabilityRiskLevel = CapabilityRiskLevel.READ_ONLY
    data_classification: DataClassification = DataClassification.INTERNAL
    affected_resources: List[str] = field(default_factory=list)
    expected_side_effects: List[str] = field(default_factory=list)
    reversibility: bool = False
    status: ApprovalStatus = ApprovalStatus.PENDING
    scope: str = "task"  # task, session, always
    created_at: float = field(default_factory=_now)
    expires_at: Optional[float] = None
    responded_at: Optional[float] = None
    response: Optional[ApprovalResponse] = None
    responded_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalPolicy:
    """Policy for automatic approval decisions."""
    policy_id: str
    name: str
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    auto_approve: bool = False
    auto_deny: bool = False
    default_scope: str = "task"
    expires_in: float = 3600  # 1 hour
    priority: int = 0
    enabled: bool = True


class HumanOversightManager:
    """
    Manages human approval workflows as a kernel primitive.
    
    Supports:
    - approval.request
    - approval.grant
    - approval.deny
    - approval.expire
    - approval.delegate
    - approval.remember
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        self._requests: Dict[str, ApprovalRequest] = {}
        self._agent_requests: Dict[str, List[str]] = defaultdict(list)  # agent_id -> request_ids
        self._policies: Dict[str, ApprovalPolicy] = {}
        self._remembered: Dict[str, ApprovalResponse] = {}  # Keyed by capability/action
        
        # Callbacks
        self._request_callbacks: List[Callable[[ApprovalRequest], None]] = []
        self._response_callbacks: List[Callable[[ApprovalRequest, ApprovalResponse], None]] = []

    def register_request_callback(self, callback: Callable[[ApprovalRequest], None]) -> None:
        """Register a callback for new approval requests."""
        self._request_callbacks.append(callback)

    def register_response_callback(self, callback: Callable[[ApprovalRequest, ApprovalResponse], None]) -> None:
        """Register a callback for approval responses."""
        self._response_callbacks.append(callback)

    def request_approval(
        self,
        approval_type: ApprovalType,
        agent_id: str,
        task_id: str = "",
        intent_id: str = "",
        capability_id: str = "",
        description: str = "",
        details: Dict[str, Any] = None,
        risk_level: CapabilityRiskLevel = CapabilityRiskLevel.READ_ONLY,
        data_classification: DataClassification = DataClassification.INTERNAL,
        affected_resources: List[str] = None,
        expected_side_effects: List[str] = None,
        reversibility: bool = False,
        scope: str = "task",
        expires_in: float = 3600,  # 1 hour
    ) -> ApprovalRequest:
        """Request human approval."""
        # Check for remembered decision
        remember_key = self._make_remember_key(approval_type, capability_id, agent_id)
        if remember_key in self._remembered:
            remembered = self._remembered[remember_key]
            if remembered != ApprovalResponse.DENY and remembered != ApprovalResponse.DENY_SESSION:
                # Auto-approve based on memory
                return self._create_auto_approved_request(
                    approval_type, agent_id, task_id, intent_id, capability_id,
                    description, details, risk_level, data_classification,
                    affected_resources, expected_side_effects, reversibility,
                    scope, remembered
                )

        # Check policies
        for policy in self._policies.values():
            if not policy.enabled:
                continue
            if self._policy_matches(policy, approval_type, capability_id, risk_level, data_classification):
                if policy.auto_approve:
                    return self._create_auto_approved_request(
                        approval_type, agent_id, task_id, intent_id, capability_id,
                        description, details, risk_level, data_classification,
                        affected_resources, expected_side_effects, reversibility,
                        scope, ApprovalResponse.APPROVE_SESSION if policy.default_scope == "session" else ApprovalResponse.APPROVE_ONCE
                    )
                elif policy.auto_deny:
                    return self._create_auto_denied_request(
                        approval_type, agent_id, task_id, intent_id, capability_id,
                        description, details, risk_level, data_classification,
                        affected_resources, expected_side_effects, reversibility,
                        scope
                    )

        # Create pending request
        request = ApprovalRequest(
            request_id=new_id("appr"),
            approval_type=approval_type,
            agent_id=agent_id,
            task_id=task_id,
            intent_id=intent_id,
            capability_id=capability_id,
            description=description,
            details=details or {},
            risk_level=risk_level,
            data_classification=data_classification,
            affected_resources=affected_resources or [],
            expected_side_effects=expected_side_effects or [],
            reversibility=reversibility,
            scope=scope,
            expires_at=_now() + expires_in,
        )

        with self._lock:
            self._requests[request.request_id] = request
            self._agent_requests[agent_id].append(request.request_id)

        # Notify callbacks
        for callback in self._request_callbacks:
            try:
                callback(request)
            except Exception as exc:
                logger.error("Approval request callback error: %s", exc)

        if self.event_bus:
            self.event_bus.emit("approval.requested", {
                "request_id": request.request_id,
                "agent_id": agent_id,
                "type": approval_type.value,
                "capability": capability_id,
                "risk": risk_level.value,
                "description": description,
                "expires_at": request.expires_at,
            })

        logger.info("HumanOversightManager: approval requested %s for agent %s",
                    request.request_id, agent_id)
        return request

    def _create_auto_approved_request(
        self,
        approval_type: ApprovalType,
        agent_id: str,
        task_id: str,
        intent_id: str,
        capability_id: str,
        description: str,
        details: Dict[str, Any],
        risk_level: CapabilityRiskLevel,
        data_classification: DataClassification,
        affected_resources: List[str],
        expected_side_effects: List[str],
        reversibility: bool,
        scope: str,
        response: ApprovalResponse,
    ) -> ApprovalRequest:
        """Create an auto-approved request."""
        request = ApprovalRequest(
            request_id=new_id("appr"),
            approval_type=approval_type,
            agent_id=agent_id,
            task_id=task_id,
            intent_id=intent_id,
            capability_id=capability_id,
            description=description,
            details=details or {},
            risk_level=risk_level,
            data_classification=data_classification,
            affected_resources=affected_resources or [],
            expected_side_effects=expected_side_effects or [],
            reversibility=reversibility,
            scope=scope,
            status=ApprovalStatus.GRANTED,
            responded_at=_now(),
            response=response,
            responded_by="auto_policy",
        )

        with self._lock:
            self._requests[request.request_id] = request
            self._agent_requests[agent_id].append(request.request_id)

        if self.event_bus:
            self.event_bus.emit("approval.auto_granted", {
                "request_id": request.request_id,
                "agent_id": agent_id,
                "response": response.value,
            })

        return request

    def _create_auto_denied_request(
        self,
        approval_type: ApprovalType,
        agent_id: str,
        task_id: str,
        intent_id: str,
        capability_id: str,
        description: str,
        details: Dict[str, Any],
        risk_level: CapabilityRiskLevel,
        data_classification: DataClassification,
        affected_resources: List[str],
        expected_side_effects: List[str],
        reversibility: bool,
        scope: str,
    ) -> ApprovalRequest:
        """Create an auto-denied request."""
        request = ApprovalRequest(
            request_id=new_id("appr"),
            approval_type=approval_type,
            agent_id=agent_id,
            task_id=task_id,
            intent_id=intent_id,
            capability_id=capability_id,
            description=description,
            details=details or {},
            risk_level=risk_level,
            data_classification=data_classification,
            affected_resources=affected_resources or [],
            expected_side_effects=expected_side_effects or [],
            reversibility=reversibility,
            scope=scope,
            status=ApprovalStatus.DENIED,
            responded_at=_now(),
            response=ApprovalResponse.DENY,
            responded_by="auto_policy",
        )

        with self._lock:
            self._requests[request.request_id] = request
            self._agent_requests[agent_id].append(request.request_id)

        if self.event_bus:
            self.event_bus.emit("approval.auto_denied", {
                "request_id": request.request_id,
                "agent_id": agent_id,
            })

        return request

    def _policy_matches(
        self,
        policy: ApprovalPolicy,
        approval_type: ApprovalType,
        capability_id: str,
        risk_level: CapabilityRiskLevel,
        data_classification: DataClassification,
    ) -> bool:
        """Check if a policy matches the request."""
        for condition in policy.conditions:
            cond_type = condition.get("type")
            if cond_type == "approval_type" and condition.get("value") != approval_type.value:
                return False
            elif cond_type == "capability" and condition.get("value") != capability_id:
                return False
            elif cond_type == "risk_level" and condition.get("value") != risk_level.value:
                return False
            elif cond_type == "data_classification" and condition.get("value") != data_classification.value:
                return False
        return True

    def _make_remember_key(
        self,
        approval_type: ApprovalType,
        capability_id: str,
        agent_id: str,
    ) -> str:
        """Create a key for remembered decisions."""
        return f"{approval_type.value}:{capability_id}:{agent_id}"

    def respond_approval(
        self,
        request_id: str,
        response: ApprovalResponse,
        responded_by: str = "human",
    ) -> bool:
        """Respond to an approval request."""
        with self._lock:
            request = self._requests.get(request_id)
        
        if not request:
            logger.warning("Approval request not found: %s", request_id)
            return False
        
        if request.status != ApprovalStatus.PENDING:
            logger.warning("Approval request already responded: %s", request_id)
            return False
        
        if request.expires_at and _now() > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            return False
        
        request.status = ApprovalStatus.GRANTED if response in (
            ApprovalResponse.APPROVE_ONCE, ApprovalResponse.APPROVE_SESSION, ApprovalResponse.ALWAYS_ALLOW
        ) else ApprovalStatus.DENIED
        request.responded_at = _now()
        request.response = response
        request.responded_by = responded_by

        # Handle "remember" responses
        if response in (ApprovalResponse.ALWAYS_ALLOW, ApprovalResponse.APPROVE_SESSION):
            remember_key = self._make_remember_key(request.approval_type, request.capability_id, request.agent_id)
            self._remembered[remember_key] = response

        # Notify callbacks
        for callback in self._response_callbacks:
            try:
                callback(request, response)
            except Exception as exc:
                logger.error("Approval response callback error: %s", exc)

        if self.event_bus:
            self.event_bus.emit("approval.responded", {
                "request_id": request_id,
                "agent_id": request.agent_id,
                "response": response.value,
                "responded_by": responded_by,
            })

        logger.info("HumanOversightManager: approval %s %s by %s",
                    request_id, response.value, responded_by)
        return True

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request."""
        with self._lock:
            return self._requests.get(request_id)

    def get_pending_requests(self, agent_id: str = "") -> List[ApprovalRequest]:
        """Get pending approval requests."""
        with self._lock:
            if agent_id:
                request_ids = self._agent_requests.get(agent_id, [])
                requests = [self._requests[rid] for rid in request_ids if rid in self._requests]
            else:
                requests = list(self._requests.values())
        
        return [r for r in requests if r.status == ApprovalStatus.PENDING]

    def expire_request(self, request_id: str) -> bool:
        """Expire an approval request."""
        with self._lock:
            request = self._requests.get(request_id)
        
        if not request or request.status != ApprovalStatus.PENDING:
            return False
        
        request.status = ApprovalStatus.EXPIRED
        
        if self.event_bus:
            self.event_bus.emit("approval.expired", {
                "request_id": request_id,
                "agent_id": request.agent_id,
            })
        
        return True

    def delegate_approval(
        self,
        request_id: str,
        delegate_to: str,
    ) -> bool:
        """Delegate approval to another human."""
        with self._lock:
            request = self._requests.get(request_id)
        
        if not request or request.status != ApprovalStatus.PENDING:
            return False
        
        request.status = ApprovalStatus.DELEGATED
        request.metadata["delegated_to"] = delegate_to
        
        if self.event_bus:
            self.event_bus.emit("approval.delegated", {
                "request_id": request_id,
                "delegated_to": delegate_to,
            })
        
        return True

    def forget_approval(self, approval_type: ApprovalType, capability_id: str, agent_id: str) -> bool:
        """Forget a remembered approval."""
        key = self._make_remember_key(approval_type, capability_id, agent_id)
        if key in self._remembered:
            del self._remembered[key]
            return True
        return False

    def register_policy(self, policy: ApprovalPolicy) -> None:
        """Register an approval policy."""
        with self._lock:
            self._policies[policy.policy_id] = policy

    def get_stats(self) -> Dict[str, Any]:
        """Get human oversight manager statistics."""
        with self._lock:
            total = len(self._requests)
            pending = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.PENDING)
            granted = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.GRANTED)
            denied = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.DENIED)
            expired = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.EXPIRED)
            remembered = len(self._remembered)
            policies = len(self._policies)

        return {
            "total_requests": total,
            "pending": pending,
            "granted": granted,
            "denied": denied,
            "expired": expired,
            "remembered_decisions": remembered,
            "policies": policies,
        }

    def shutdown(self) -> None:
        """Shutdown the human oversight manager."""
        logger.info("HumanOversightManager: shutting down")
        with self._lock:
            self._requests.clear()
            self._agent_requests.clear()
            self._policies.clear()
            self._remembered.clear()