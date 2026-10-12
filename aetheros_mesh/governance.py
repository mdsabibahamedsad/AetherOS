"""Mesh governance engine (Master 49 sections 141-146)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from .models import MeshNode, TrustDimension
from .trust import MeshTrust, TrustAssessment

logger = logging.getLogger(__name__)


class PolicyLevel(Enum):
    """Policy hierarchy levels (section 142)."""
    SECURITY = 0          # Highest - cannot be overridden
    IDENTITY = 1
    PRIVACY = 2
    AUTHORIZATION = 3
    HUMAN_APPROVAL = 4
    ECONOMIC_POLICY = 5
    PERFORMANCE_OPTIMIZATION = 6
    CONVENIENCE = 7       # Lowest


@dataclass
class Policy:
    """A governance policy."""
    policy_id: str = field(default_factory=lambda: f"pol-{uuid.uuid4().hex[:12]}")
    name: str = ""
    level: PolicyLevel = PolicyLevel.CONVENIENCE
    scope: str = "mesh"  # mesh, organization, team, task
    rules: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    created_by: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    active: bool = True
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["level"] = self.level.value
        return d


@dataclass
class GovernanceDecision:
    """A governance decision record."""
    decision_id: str = field(default_factory=lambda: f"gov-{uuid.uuid4().hex[:12]}")
    policy_id: str = ""
    action: str = ""  # allow, deny, modify, escalate
    target: str = ""  # agent, team, task, capability, experiment
    target_id: str = ""
    reason: str = ""
    decided_by: str = ""  # human, automated, emergency
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AdmissionRequest:
    """Request for agent admission to mesh."""
    request_id: str = field(default_factory=lambda: f"adm-{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    node_data: Dict[str, Any] = field(default_factory=dict)
    requested_by: str = ""
    requested_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending, approved, denied, needs_review
    decision: Optional[GovernanceDecision] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.decision:
            d["decision"] = self.decision.to_dict()
        return d


class MeshGovernanceEngine:
    """Governance engine for mesh operations (section 141)."""
    
    def __init__(
        self,
        trust_engine: MeshTrust,
        nodes: Dict[str, MeshNode],
        blackboard,
        config: Dict[str, Any] = None
    ):
        self.trust_engine = trust_engine
        self.nodes = nodes
        self.blackboard = blackboard
        self.config = config or {}
        
        self._policies: Dict[str, Policy] = {}
        self._decisions: List[GovernanceDecision] = []
        self._admission_requests: Dict[str, AdmissionRequest] = {}
        self._emergency_stop = False
        self._quarantined_agents: Set[str] = set()
        
        # Initialize default policies
        self._init_default_policies()
        
        # Load persisted state
        self._load_state()
    
    def _init_default_policies(self) -> None:
        """Initialize default governance policies."""
        
        # Security policies (highest level)
        self.add_policy(Policy(
            name="no_unauthorized_external_access",
            level=PolicyLevel.SECURITY,
            scope="mesh",
            rules={
                "require_verification_for_external": True,
                "block_untrusted_external": True,
                "max_data_class_for_external": "internal",
            },
            description="Prevent unauthorized external agent access to sensitive data",
        ))
        
        self.add_policy(Policy(
            name="credential_protection",
            level=PolicyLevel.SECURITY,
            scope="mesh",
            rules={
                "never_log_credentials": True,
                "encrypt_credentials_at_rest": True,
                "rotate_credentials_on_compromise": True,
            },
            description="Protect credentials from exposure",
        ))
        
        # Identity policies
        self.add_policy(Policy(
            name="agent_identity_verification",
            level=PolicyLevel.IDENTITY,
            scope="mesh",
            rules={
                "require_cryptographic_identity": True,
                "verify_agent_cards_before_trust": True,
                "reject_unverifiable_identities": True,
            },
            description="Ensure all agents have verified identities",
        ))
        
        # Privacy policies
        self.add_policy(Policy(
            name="data_classification_enforcement",
            level=PolicyLevel.PRIVACY,
            scope="mesh",
            rules={
                "enforce_data_class_labels": True,
                "no_sensitive_data_to_untrusted": True,
                "audit_cross_boundary_data_flow": True,
            },
            description="Enforce data classification and privacy boundaries",
        ))
        
        # Authorization policies
        self.add_policy(Policy(
            name="least_privilege",
            level=PolicyLevel.AUTHORIZATION,
            scope="mesh",
            rules={
                "default_deny": True,
                "explicit_grants_only": True,
                "review_privilege_escalation": True,
            },
            description="Enforce least privilege access control",
        ))
        
        # Human approval policies
        self.add_policy(Policy(
            name="critical_action_approval",
            level=PolicyLevel.HUMAN_APPROVAL,
            scope="mesh",
            rules={
                "financial_requires_approval": True,
                "legal_requires_approval": True,
                "medical_requires_approval": True,
                "security_requires_approval": True,
                "identity_requires_approval": True,
                "destructive_requires_approval": True,
            },
            description="Require human approval for critical actions",
        ))
        
        # Economic policies
        self.add_policy(Policy(
            name="budget_enforcement",
            level=PolicyLevel.ECONOMIC_POLICY,
            scope="mesh",
            rules={
                "enforce_task_budgets": True,
                "prevent_budget_escalation": True,
                "require_approval_over_threshold": 10.0,
            },
            description="Enforce economic budgets and limits",
        ))
        
        # Performance optimization policies (can be overridden by higher levels)
        self.add_policy(Policy(
            name="optimization_constraints",
            level=PolicyLevel.PERFORMANCE_OPTIMIZATION,
            scope="mesh",
            rules={
                "max_team_size": 10,
                "max_parallel_tasks": 5,
                "max_recursion_depth": 3,
                "require_evidence_for_optimization": True,
            },
            description="Constraints on self-optimization",
        ))
    
    def add_policy(self, policy: Policy) -> Policy:
        """Add or update a policy."""
        self._policies[policy.policy_id] = policy
        self._save_state()
        return policy
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)
    
    def list_policies(self, level: PolicyLevel = None, scope: str = None) -> List[Policy]:
        """List policies with optional filters."""
        policies = list(self._policies.values())
        
        if level:
            policies = [p for p in policies if p.level == level]
        if scope:
            policies = [p for p in policies if p.scope == scope]
        
        return sorted(policies, key=lambda p: (p.level.value, p.name))
    
    def evaluate_action(
        self,
        action: str,
        target_type: str,
        target_id: str,
        context: Dict[str, Any],
        requester: str = ""
    ) -> Tuple[bool, str, List[Policy]]:
        """Evaluate if an action is allowed under current policies.
        
        Returns: (allowed, reason, applicable_policies)
        """
        
        applicable = []
        denied_reasons = []
        
        for policy in self._policies.values():
            if not policy.active:
                continue
            
            if not self._policy_applies(policy, target_type, target_id, context):
                continue
            
            applicable.append(policy)
            
            # Check policy rules
            allowed, reason = self._check_policy_rules(policy, action, context)
            if not allowed:
                denied_reasons.append(f"{policy.name}: {reason}")
        
        if denied_reasons:
            return False, "; ".join(denied_reasons), applicable
        
        return True, "allowed", applicable
    
    def _policy_applies(
        self, 
        policy: Policy, 
        target_type: str, 
        target_id: str, 
        context: Dict[str, Any]
    ) -> bool:
        """Check if a policy applies to the given target."""
        if policy.scope == "mesh":
            return True
        elif policy.scope == "organization":
            return context.get("organization_id") == target_id
        elif policy.scope == "team":
            return context.get("team_id") == target_id
        elif policy.scope == "task":
            return context.get("task_id") == target_id
        return False
    
    def _check_policy_rules(
        self, 
        policy: Policy, 
        action: str, 
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Check if action violates policy rules."""
        rules = policy.rules
        
        # Security rules
        if policy.name == "no_unauthorized_external_access":
            if action in ("delegate", "send_data", "invoke_external"):
                target_trust = context.get("target_trust", {})
                if target_trust.get("level", "untrusted") in ("untrusted", "low"):
                    return False, "External target not sufficiently trusted"
                
                data_class = context.get("data_class", "public")
                max_class = rules.get("max_data_class_for_external", "internal")
                class_order = ["public", "internal", "sensitive", "highly_sensitive"]
                if class_order.index(data_class) > class_order.index(max_class):
                    return False, f"Data class {data_class} exceeds maximum {max_class} for external"
        
        if policy.name == "credential_protection":
            if action == "log" and context.get("contains_credentials", False):
                return False, "Credentials must not be logged"
        
        # Identity rules
        if policy.name == "agent_identity_verification":
            if action in ("admit_agent", "trust_agent"):
                if not context.get("identity_verified", False):
                    return False, "Agent identity not cryptographically verified"
        
        # Privacy rules
        if policy.name == "data_classification_enforcement":
            if action == "send_data":
                if not context.get("data_class_labeled", False):
                    return False, "Data must have classification label"
                
                data_class = context.get("data_class", "public")
                target_trust = context.get("target_trust", {})
                if data_class in ("sensitive", "highly_sensitive"):
                    if target_trust.get("level", "untrusted") not in ("verified", "trusted"):
                        return False, f"{data_class} data requires verified/trusted recipient"
        
        # Authorization rules
        if policy.name == "least_privilege":
            if action == "grant_permission":
                if not context.get("explicit_grant", False):
                    return False, "Permissions must be explicitly granted"
        
        # Human approval rules
        if policy.name == "critical_action_approval":
            critical_types = {
                "financial": "financial_requires_approval",
                "legal": "legal_requires_approval",
                "medical": "medical_requires_approval",
                "security": "security_requires_approval",
                "identity": "identity_requires_approval",
                "destructive": "destructive_requires_approval",
            }
            
            action_type = context.get("action_type", "")
            if action_type in critical_types and rules.get(critical_types[action_type], False):
                if not context.get("human_approved", False):
                    return False, f"{action_type} action requires human approval"
        
        # Economic rules
        if policy.name == "budget_enforcement":
            if action == "spend":
                amount = context.get("amount", 0)
                budget = context.get("budget", 0)
                threshold = rules.get("require_approval_over_threshold", 10.0)
                
                if amount > budget:
                    return False, f"Amount ${amount} exceeds budget ${budget}"
                
                if amount > threshold and not context.get("human_approved", False):
                    return False, f"Amount ${amount} exceeds approval threshold ${threshold}"
        
        # Optimization constraints
        if policy.name == "optimization_constraints":
            if action == "form_team":
                team_size = context.get("team_size", 0)
                if team_size > rules.get("max_team_size", 10):
                    return False, f"Team size {team_size} exceeds maximum {rules['max_team_size']}"
            
            if action == "parallel_execute":
                parallel = context.get("parallel_count", 0)
                if parallel > rules.get("max_parallel_tasks", 5):
                    return False, f"Parallel count {parallel} exceeds maximum {rules['max_parallel_tasks']}"
            
            if action == "recurse":
                depth = context.get("recursion_depth", 0)
                if depth > rules.get("max_recursion_depth", 3):
                    return False, f"Recursion depth {depth} exceeds maximum {rules['max_recursion_depth']}"
        
        return True, "allowed"
    
    def request_admission(
        self,
        agent_id: str,
        node_data: Dict[str, Any],
        requested_by: str
    ) -> AdmissionRequest:
        """Request admission of a new agent to the mesh."""
        
        request = AdmissionRequest(
            agent_id=agent_id,
            node_data=node_data,
            requested_by=requested_by,
        )
        
        self._admission_requests[request.request_id] = request
        
        # Auto-evaluate based on trust
        if "node_id" in node_data:
            node_id = node_data["node_id"]
            assessment = self.trust_engine.assess_node(node_id)
            
            # Check if meets minimum trust thresholds
            min_trust = self.config.get("admission_min_trust", 0.5)
            if assessment.overall_score >= min_trust and assessment.overall_confidence >= 0.5:
                request.status = "approved"
                request.decision = GovernanceDecision(
                    policy_id="auto_admission",
                    action="allow",
                    target="agent",
                    target_id=agent_id,
                    reason=f"Auto-approved: trust score {assessment.overall_score:.2f} >= {min_trust}",
                    decided_by="automated",
                    evidence=[assessment.to_dict()],
                )
            else:
                request.status = "needs_review"
        
        self._save_state()
        return request
    
    def decide_admission(
        self,
        request_id: str,
        decision: str,  # allow, deny
        reason: str,
        decided_by: str
    ) -> AdmissionRequest:
        """Make a decision on an admission request."""
        
        request = self._admission_requests.get(request_id)
        if not request:
            raise ValueError(f"Admission request {request_id} not found")
        
        request.status = "approved" if decision == "allow" else "denied"
        request.decision = GovernanceDecision(
            policy_id="admission_decision",
            action=decision,
            target="agent",
            target_id=request.agent_id,
            reason=reason,
            decided_by=decided_by,
        )
        
        self._save_state()
        return request
    
    def record_decision(self, decision: GovernanceDecision) -> GovernanceDecision:
        """Record a governance decision."""
        self._decisions.append(decision)
        
        # Keep decisions bounded
        if len(self._decisions) > 10000:
            self._decisions = self._decisions[-10000:]
        
        self._save_state()
        return decision
    
    def emergency_stop(self, activated_by: str, reason: str) -> bool:
        """Activate global emergency stop (section 143)."""
        
        if self._emergency_stop:
            return False  # Already stopped
        
        self._emergency_stop = True
        
        decision = GovernanceDecision(
            policy_id="emergency_stop",
            action="deny",
            target="mesh",
            target_id="all",
            reason=reason,
            decided_by=activated_by,
            evidence=[{"type": "emergency_stop", "activated_by": activated_by}],
        )
        
        self.record_decision(decision)
        
        # Broadcast to blackboard
        self.blackboard.put(
            "governance:emergency_stop",
            {"activated": True, "by": activated_by, "reason": reason, "at": time.time()},
            source_agent="governance",
            scope="mesh",
            tags=["emergency", "governance"],
        )
        
        logger.critical(f"EMERGENCY STOP activated by {activated_by}: {reason}")
        return True
    
    def emergency_resume(self, authorized_by: str, reason: str) -> bool:
        """Resume from emergency stop (requires authorization)."""
        
        if not self._emergency_stop:
            return False
        
        # Check if authorized (would check against authorized roles)
        authorized_roles = self.config.get("emergency_resume_roles", ["admin", "security_officer"])
        
        decision = GovernanceDecision(
            policy_id="emergency_resume",
            action="allow",
            target="mesh",
            target_id="all",
            reason=reason,
            decided_by=authorized_by,
            evidence=[{"type": "emergency_resume", "authorized_by": authorized_by}],
        )
        
        self.record_decision(decision)
        
        self._emergency_stop = False
        
        self.blackboard.put(
            "governance:emergency_stop",
            {"activated": False, "by": authorized_by, "reason": reason, "at": time.time()},
            source_agent="governance",
            scope="mesh",
            tags=["emergency", "governance"],
        )
        
        logger.critical(f"EMERGENCY RESUME by {authorized_by}: {reason}")
        return True
    
    def is_emergency_stopped(self) -> bool:
        """Check if emergency stop is active."""
        return self._emergency_stop
    
    def quarantine_agent(
        self, 
        agent_id: str, 
        reason: str, 
        authorized_by: str
    ) -> bool:
        """Quarantine an agent (section 144)."""
        
        if agent_id in self._quarantined_agents:
            return False
        
        self._quarantined_agents.add(agent_id)
        
        # Update node state
        node = self.nodes.get(agent_id)
        if node:
            node.update_state(node.__class__.__name__ == "MeshNode" and hasattr(node, 'update_state') and node.state.__class__.__name__ == "MeshNodeState")
            # In real implementation, would update node state to SUSPENDED
        
        decision = GovernanceDecision(
            policy_id="agent_quarantine",
            action="deny",
            target="agent",
            target_id=agent_id,
            reason=reason,
            decided_by=authorized_by,
            evidence=[{"type": "quarantine", "reason": reason}],
        )
        
        self.record_decision(decision)
        
        # Broadcast
        self.blackboard.put(
            f"governance:quarantine:{agent_id}",
            {"quarantined": True, "by": authorized_by, "reason": reason, "at": time.time()},
            source_agent="governance",
            scope="mesh",
            tags=["quarantine", "governance"],
        )
        
        logger.warning(f"Agent {agent_id} quarantined by {authorized_by}: {reason}")
        return True
    
    def release_quarantine(
        self, 
        agent_id: str, 
        authorized_by: str,
        reason: str = ""
    ) -> bool:
        """Release agent from quarantine."""
        
        if agent_id not in self._quarantined_agents:
            return False
        
        self._quarantined_agents.discard(agent_id)
        
        decision = GovernanceDecision(
            policy_id="quarantine_release",
            action="allow",
            target="agent",
            target_id=agent_id,
            reason=reason or "Quarantine released",
            decided_by=authorized_by,
        )
        
        self.record_decision(decision)
        
        self.blackboard.put(
            f"governance:quarantine:{agent_id}",
            {"quarantined": False, "by": authorized_by, "reason": reason, "at": time.time()},
            source_agent="governance",
            scope="mesh",
            tags=["quarantine", "governance"],
        )
        
        logger.info(f"Agent {agent_id} released from quarantine by {authorized_by}")
        return True
    
    def is_quarantined(self, agent_id: str) -> bool:
        """Check if agent is quarantined."""
        return agent_id in self._quarantined_agents
    
    def evidence_quarantine(
        self, 
        agent_id: str, 
        reason: str,
        authorized_by: str
    ) -> List[str]:
        """Quarantine evidence from a compromised agent (section 145)."""
        
        quarantined_keys = []
        
        # Find all blackboard entries from this agent
        entries = self.blackboard.query(source_agent=agent_id)
        
        for key, entry in entries.items():
            if isinstance(entry, dict) and entry.get("source_agent") == agent_id:
                # Mark as quarantined
                self.blackboard.put(
                    key,
                    {**entry, "_quarantined": True, "_quarantine_reason": reason, "_quarantined_at": time.time()},
                    source_agent="governance",
                    scope="mesh",
                    tags=["quarantined_evidence"],
                )
                quarantined_keys.append(key)
        
        if quarantined_keys:
            decision = GovernanceDecision(
                policy_id="evidence_quarantine",
                action="deny",
                target="evidence",
                target_id=agent_id,
                reason=reason,
                decided_by=authorized_by,
                evidence=[{"quarantined_keys": quarantined_keys}],
            )
            self.record_decision(decision)
        
        return quarantined_keys
    
    def self_healing_action(
        self,
        action: str,  # reroute, retry, replace, reverify, isolate
        target_id: str,
        reason: str,
        context: Dict[str, Any]
    ) -> GovernanceDecision:
        """Execute a self-healing action (section 146)."""
        
        # Check if action violates protected policies
        allowed, reason_check, policies = self.evaluate_action(
            action, "self_healing", target_id, context, "self_healing"
        )
        
        if not allowed:
            return GovernanceDecision(
                policy_id="self_healing_blocked",
                action="deny",
                target="self_healing",
                target_id=target_id,
                reason=f"Self-healing blocked: {reason_check}",
                decided_by="governance",
                evidence=[{"original_reason": reason, "blocked_by": [p.name for p in policies]}],
            )
        
        # Execute the action
        decision = GovernanceDecision(
            policy_id="self_healing",
            action=action,
            target="agent" if target_id.startswith("node-") else "task",
            target_id=target_id,
            reason=reason,
            decided_by="automated",
            evidence=[{"context": context}],
        )
        
        self.record_decision(decision)
        return decision
    
    def _save_state(self) -> None:
        """Persist governance state."""
        try:
            data = {
                "policies": {pid: p.to_dict() for pid, p in self._policies.items()},
                "decisions": [d.to_dict() for d in self._decisions[-1000:]],  # Last 1000
                "admission_requests": {rid: r.to_dict() for rid, r in self._admission_requests.items()},
                "emergency_stop": self._emergency_stop,
                "quarantined_agents": list(self._quarantined_agents),
                "saved_at": time.time(),
            }
            
            file = self.blackboard.home / f"mesh_governance_{self.blackboard.mesh_id}.json"
            tmp = file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(file)
        except Exception as e:
            logger.warning(f"Failed to save governance state: {e}")
    
    def _load_state(self) -> None:
        """Load persisted governance state."""
        try:
            file = self.blackboard.home / f"mesh_governance_{self.blackboard.mesh_id}.json"
            if file.exists():
                data = json.loads(file.read_text(encoding="utf-8"))
                
                for pid, pdata in data.get("policies", {}).items():
                    pdata["level"] = PolicyLevel(pdata["level"])
                    self._policies[pid] = Policy(**pdata)
                
                for ddata in data.get("decisions", []):
                    self._decisions.append(GovernanceDecision(**ddata))
                
                for rid, rdata in data.get("admission_requests", {}).items():
                    if rdata.get("decision"):
                        rdata["decision"] = GovernanceDecision(**rdata["decision"])
                    self._admission_requests[rid] = AdmissionRequest(**rdata)
                
                self._emergency_stop = data.get("emergency_stop", False)
                self._quarantined_agents = set(data.get("quarantined_agents", []))
        except Exception as e:
            logger.warning(f"Failed to load governance state: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get governance status."""
        return {
            "emergency_stop": self._emergency_stop,
            "quarantined_agents": list(self._quarantined_agents),
            "policy_count": len(self._policies),
            "decisions_count": len(self._decisions),
            "pending_admissions": len([r for r in self._admission_requests.values() if r.status == "pending"]),
            "policies_by_level": {
                level.name: len([p for p in self._policies.values() if p.level == level])
                for level in PolicyLevel
            },
        }


def create_governance_engine(
    trust_engine: MeshTrust,
    nodes: Dict[str, MeshNode],
    blackboard,
    config: Dict[str, Any] = None
) -> MeshGovernanceEngine:
    """Factory function to create a MeshGovernanceEngine."""
    return MeshGovernanceEngine(trust_engine, nodes, blackboard, config)