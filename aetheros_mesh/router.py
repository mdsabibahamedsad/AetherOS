"""Mesh router with topology selection (Master 49 sections 8-9, 31-35)."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import (
    MeshNode, MeshTask, MeshNodeState, TopologyType, TrustDimension, MeshEdge, EdgeType
)
from .trust import MeshTrust, TrustAssessment

logger = logging.getLogger(__name__)


@dataclass
class RouteCandidate:
    """A candidate node for task routing."""
    node: MeshNode
    capability_coverage: float = 0.0
    trust_score: float = 0.0
    estimated_latency_ms: Optional[float] = None
    estimated_cost: Optional[float] = None
    availability_score: float = 1.0
    resource_fit: float = 1.0
    rejection_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["node"] = self.node.to_dict()
        return d


@dataclass
class RoutingDecision:
    """Result of mesh routing."""
    task_id: str
    topology: TopologyType
    candidates: List[RouteCandidate]
    selected_nodes: List[str]
    execution_plan: Dict[str, Any]
    trust_level: str = ""
    estimated_latency_ms: float = 0.0
    estimated_cost: float = 0.0
    confidence: float = 0.0
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["topology"] = self.topology.value
        d["candidates"] = [c.to_dict() for c in self.candidates]
        return d


class MeshRouter:
    """Routes tasks through the mesh using capability, trust, and topology awareness."""
    
    def __init__(
        self,
        trust_engine: MeshTrust,
        mesh_nodes: Dict[str, MeshNode],
        config: Dict[str, Any] = None
    ):
        self.trust_engine = trust_engine
        self.nodes = mesh_nodes
        self.config = config or {}
        
        # Default weights for candidate scoring
        self.weights = {
            "trust": self.config.get("weight_trust", 0.35),
            "capability": self.config.get("weight_capability", 0.25),
            "latency": self.config.get("weight_latency", 0.15),
            "cost": self.config.get("weight_cost", 0.10),
            "availability": self.config.get("weight_availability", 0.10),
            "resource": self.config.get("weight_resource", 0.05),
        }
        
        # Topology selection rules
        self.topology_rules = self._default_topology_rules()
    
    def _default_topology_rules(self) -> Dict[TopologyType, Dict[str, Any]]:
        """Default rules for topology selection."""
        return {
            TopologyType.SINGLE_AGENT: {
                "min_agents": 1, "max_agents": 1,
                "suitable_for": ["simple", "low_risk", "low_cost"],
                "description": "Single agent execution",
            },
            TopologyType.SEQUENTIAL: {
                "min_agents": 2, "max_agents": 5,
                "suitable_for": ["dependent_steps", "pipeline"],
                "description": "Sequential agent execution",
            },
            TopologyType.PARALLEL: {
                "min_agents": 2, "max_agents": 10,
                "suitable_for": ["independent_shards", "high_throughput"],
                "description": "Parallel independent execution",
            },
            TopologyType.DAG: {
                "min_agents": 3, "max_agents": 20,
                "suitable_for": ["complex_dependencies", "multi_stage"],
                "description": "DAG-based dependency execution",
            },
            TopologyType.PIPELINE: {
                "min_agents": 2, "max_agents": 10,
                "suitable_for": ["streaming", "multi_stage_transform"],
                "description": "Pipeline execution",
            },
            TopologyType.HIERARCHICAL: {
                "min_agents": 3, "max_agents": 15,
                "suitable_for": ["coordination", "multi_team"],
                "description": "Hierarchical team structure",
            },
            TopologyType.SWARM: {
                "min_agents": 5, "max_agents": 50,
                "suitable_for": ["exploration", "consensus_building"],
                "description": "Swarm intelligence",
            },
            TopologyType.DEBATE: {
                "min_agents": 3, "max_agents": 7,
                "suitable_for": ["high_stakes", "conflicting_views"],
                "description": "Structured debate",
            },
            TopologyType.MAP_REDUCE: {
                "min_agents": 3, "max_agents": 100,
                "suitable_for": ["large_sharding", "aggregation"],
                "description": "Map-reduce pattern",
            },
            TopologyType.SPECIALIST_VERIFIER: {
                "min_agents": 2, "max_agents": 5,
                "suitable_for": ["high_assurance", "critical_tasks"],
                "description": "Specialist + independent verifier",
            },
            TopologyType.LOCAL_REMOTE_HYBRID: {
                "min_agents": 2, "max_agents": 10,
                "suitable_for": ["privacy_sensitive", "cost_optimization"],
                "description": "Local + remote hybrid",
            },
        }
    
    def route(
        self,
        task: MeshTask,
        available_nodes: List[MeshNode] = None,
        preferred_topology: TopologyType = None
    ) -> RoutingDecision:
        """Route a task through the mesh."""
        
        if available_nodes is None:
            available_nodes = list(self.nodes.values())
        
        # Filter eligible nodes
        candidates = self._filter_candidates(task, available_nodes)
        
        if not candidates:
            return RoutingDecision(
                task_id=task.task_id,
                topology=TopologyType.SINGLE_AGENT,
                candidates=[],
                selected_nodes=[],
                execution_plan={},
                reasoning="No eligible nodes found",
            )
        
        # Select topology
        topology = self._select_topology(task, candidates, preferred_topology)
        
        # Select nodes based on topology
        selected_nodes, execution_plan = self._select_nodes_for_topology(
            task, candidates, topology
        )
        
        # Estimate latency and cost
        est_latency = self._estimate_latency(selected_nodes, topology)
        est_cost = self._estimate_cost(selected_nodes, topology)
        
        # Calculate confidence
        confidence = self._calculate_confidence(candidates, selected_nodes, topology)
        
        # Build reasoning
        reasoning = self._build_reasoning(task, candidates, selected_nodes, topology)
        
        return RoutingDecision(
            task_id=task.task_id,
            topology=topology,
            candidates=candidates,
            selected_nodes=selected_nodes,
            execution_plan=execution_plan,
            trust_level=self._get_overall_trust(selected_nodes),
            estimated_latency_ms=est_latency,
            estimated_cost=est_cost,
            confidence=confidence,
            reasoning=reasoning,
        )
    
    def _filter_candidates(
        self, 
        task: MeshTask, 
        nodes: List[MeshNode]
    ) -> List[RouteCandidate]:
        """Filter and score candidate nodes."""
        candidates = []
        
        # Get trust assessments for all nodes
        node_ids = [n.node_id for n in nodes]
        assessments = self.trust_engine.assess_nodes(node_ids)
        
        for node in nodes:
            # Skip unavailable nodes
            if not node.is_available_for_task(task.required_capabilities):
                continue
            
            # Check trust requirements
            assessment = assessments.get(node.node_id)
            if not assessment:
                continue
            
            trust_ok = True
            for dim, min_trust in task.trust_requirements.items():
                node_trust = node.trust.get(dim, 0.0)
                if node_trust < min_trust:
                    trust_ok = False
                    break
            if not trust_ok:
                continue
            
            # Check privacy/data class requirements
            if task.privacy_level in ("sensitive", "highly_sensitive"):
                if node.trust.get(TrustDimension.SECURITY, 0.0) < 0.7:
                    continue
                if task.privacy_level == "highly_sensitive" and node.location != "local":
                    if node.trust.get(TrustDimension.SECURITY, 0.0) < 0.9:
                        continue
            
            # Calculate capability coverage
            required = set(task.required_capabilities)
            available = set(node.capabilities)
            coverage = len(required & available) / len(required) if required else 1.0
            
            # Get trust score
            trust_score = assessment.overall_score
            
            # Estimate latency (from node metadata or defaults)
            latency = node.performance.get("avg_latency_ms", 1000.0)
            
            # Estimate cost
            cost = node.performance.get("avg_cost_per_task", 0.01)
            
            # Availability score
            avail_score = 1.0 if node.state == MeshNodeState.AVAILABLE else 0.5
            
            # Resource fit
            resource_fit = self._calculate_resource_fit(node, task)
            
            # Check SLA constraints
            rejection = ""
            if task.latency_sla_ms and latency > task.latency_sla_ms:
                rejection = f"latency {latency}ms exceeds SLA {task.latency_sla_ms}ms"
            elif task.cost_budget and cost > task.cost_budget:
                rejection = f"cost ${cost} exceeds budget ${task.cost_budget}"
            
            candidate = RouteCandidate(
                node=node,
                capability_coverage=coverage,
                trust_score=trust_score,
                estimated_latency_ms=latency,
                estimated_cost=cost,
                availability_score=avail_score,
                resource_fit=resource_fit,
                rejection_reason=rejection,
            )
            candidates.append(candidate)
        
        # Sort by weighted score (eligible first)
        eligible = [c for c in candidates if not c.rejection_reason]
        rejected = [c for c in candidates if c.rejection_reason]
        
        eligible.sort(key=self._score_candidate, reverse=True)
        
        return eligible + rejected
    
    def _score_candidate(self, candidate: RouteCandidate) -> float:
        """Score a candidate node."""
        score = (
            self.weights["trust"] * candidate.trust_score +
            self.weights["capability"] * candidate.capability_coverage +
            self.weights["availability"] * candidate.availability_score +
            self.weights["resource"] * candidate.resource_fit
        )
        
        # Latency and cost are negative weights (lower is better)
        if candidate.estimated_latency_ms:
            latency_norm = min(1.0, candidate.estimated_latency_ms / 10000.0)
            score -= self.weights["latency"] * latency_norm
        
        if candidate.estimated_cost:
            cost_norm = min(1.0, candidate.estimated_cost / 10.0)
            score -= self.weights["cost"] * cost_norm
        
        return score
    
    def _calculate_resource_fit(self, node: MeshNode, task: MeshTask) -> float:
        """Calculate how well node resources fit task requirements."""
        # Simplified - in reality would check CPU, memory, GPU, etc.
        cpu_avail = node.resource_state.get("cpu_available", 1.0)
        mem_avail = node.resource_state.get("memory_available", 1.0)
        
        # Task resource requirements (simplified)
        cpu_req = task.metadata.get("cpu_required", 0.1)
        mem_req = task.metadata.get("memory_required", 0.1)
        
        cpu_fit = min(1.0, cpu_avail / max(cpu_req, 0.01))
        mem_fit = min(1.0, mem_avail / max(mem_req, 0.01))
        
        return (cpu_fit + mem_fit) / 2.0
    
    def _select_topology(
        self,
        task: MeshTask,
        candidates: List[RouteCandidate],
        preferred: TopologyType = None
    ) -> TopologyType:
        """Select the best topology for the task."""
        
        if preferred and preferred in self.topology_rules:
            rule = self.topology_rules[preferred]
            eligible = [c for c in candidates if not c.rejection_reason]
            if len(eligible) >= rule["min_agents"]:
                return preferred
        
        # Auto-select based on task characteristics
        eligible = [c for c in candidates if not c.rejection_reason]
        num_eligible = len(eligible)
        
        # Check task metadata for hints
        task_type = task.metadata.get("task_type", "")
        requires_verification = task.verification_required
        requires_consensus = task.metadata.get("requires_consensus", False)
        is_shardable = task.metadata.get("shardable", False)
        has_dependencies = bool(task.subtasks)
        
        # High-value reasoning -> debate or specialist_verifier
        if requires_verification or requires_consensus:
            if num_eligible >= 3:
                return TopologyType.SPECIALIST_VERIFIER
            elif num_eligible >= 2:
                return TopologyType.DEBATE
        
        # Shardable tasks -> map_reduce or parallel
        if is_shardable and num_eligible >= 3:
            return TopologyType.MAP_REDUCE
        
        # Dependent subtasks -> DAG or sequential
        if has_dependencies:
            if num_eligible >= 3:
                return TopologyType.DAG
            else:
                return TopologyType.SEQUENTIAL
        
        # Independent parallelizable -> parallel
        if task.metadata.get("parallelizable", False) and num_eligible >= 2:
            return TopologyType.PARALLEL
        
        # Default: smallest topology that works
        if num_eligible >= 3 and task.metadata.get("complex", False):
            return TopologyType.DAG
        elif num_eligible >= 2:
            return TopologyType.PARALLEL
        else:
            return TopologyType.SINGLE_AGENT
    
    def _select_nodes_for_topology(
        self,
        task: MeshTask,
        candidates: List[RouteCandidate],
        topology: TopologyType
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Select nodes and build execution plan for a topology."""
        
        eligible = [c for c in candidates if not c.rejection_reason]
        rule = self.topology_rules.get(topology, {})
        max_agents = min(rule.get("max_agents", 10), task.max_agents, len(eligible))
        min_agents = rule.get("min_agents", 1)
        
        if len(eligible) < min_agents:
            # Fall back to single agent
            max_agents = 1
            topology = TopologyType.SINGLE_AGENT
        
        selected = eligible[:max_agents]
        node_ids = [c.node.node_id for c in selected]
        
        # Build execution plan based on topology
        execution_plan = self._build_execution_plan(task, selected, topology)
        
        return node_ids, execution_plan
    
    def _build_execution_plan(
        self,
        task: MeshTask,
        candidates: List[RouteCandidate],
        topology: TopologyType
    ) -> Dict[str, Any]:
        """Build execution plan for the selected topology."""
        
        node_ids = [c.node.node_id for c in candidates]
        node_roles = {}
        
        # Assign roles based on capabilities and topology
        for i, candidate in enumerate(candidates):
            node = candidate.node
            if topology == TopologyType.SPECIALIST_VERIFIER:
                if i == 0:
                    node_roles[node.node_id] = "specialist"
                elif i == 1:
                    node_roles[node.node_id] = "verifier"
                else:
                    node_roles[node.node_id] = "reviewer"
            elif topology == TopologyType.DEBATE:
                if i == 0:
                    node_roles[node.node_id] = "proposer"
                elif i == 1:
                    node_roles[node.node_id] = "critic"
                else:
                    node_roles[node.node_id] = "verifier"
            elif topology == TopologyType.HIERARCHICAL:
                if i == 0:
                    node_roles[node.node_id] = "coordinator"
                else:
                    node_roles[node.node_id] = "worker"
            elif topology == TopologyType.MAP_REDUCE:
                if i == 0:
                    node_roles[node.node_id] = "reducer"
                else:
                    node_roles[node.node_id] = "mapper"
            else:
                node_roles[node.node_id] = "worker"
        
        plan = {
            "topology": topology.value,
            "nodes": node_ids,
            "roles": node_roles,
            "task_id": task.task_id,
            "steps": [],
        }
        
        # Build steps based on topology
        if topology == TopologyType.SEQUENTIAL:
            for i, nid in enumerate(node_ids):
                plan["steps"].append({
                    "step": i,
                    "node": nid,
                    "role": node_roles[nid],
                    "depends_on": node_ids[i-1] if i > 0 else None,
                })
        
        elif topology == TopologyType.PARALLEL:
            for nid in node_ids:
                plan["steps"].append({
                    "step": 0,
                    "node": nid,
                    "role": node_roles[nid],
                    "depends_on": None,
                })
        
        elif topology == TopologyType.DAG:
            # Use task.subtasks for dependencies
            for i, subtask_id in enumerate(task.subtasks):
                if i < len(node_ids):
                    plan["steps"].append({
                        "step": i,
                        "node": node_ids[i],
                        "role": node_roles[node_ids[i]],
                        "subtask": subtask_id,
                        "depends_on": task.metadata.get("subtask_deps", {}).get(subtask_id, []),
                    })
        
        elif topology == TopologyType.MAP_REDUCE:
            mappers = [nid for nid, role in node_roles.items() if role == "mapper"]
            reducer = [nid for nid, role in node_roles.items() if role == "reducer"][0]
            
            # Map phase
            for i, nid in enumerate(mappers):
                plan["steps"].append({
                    "phase": "map",
                    "step": i,
                    "node": nid,
                    "role": "mapper",
                    "shard_id": i,
                    "depends_on": None,
                })
            
            # Reduce phase
            plan["steps"].append({
                "phase": "reduce",
                "step": 0,
                "node": reducer,
                "role": "reducer",
                "depends_on": mappers,
            })
        
        elif topology == TopologyType.SPECIALIST_VERIFIER:
            specialist = [nid for nid, role in node_roles.items() if role == "specialist"][0]
            verifier = [nid for nid, role in node_roles.items() if role == "verifier"][0]
            
            plan["steps"] = [
                {"phase": "execute", "node": specialist, "role": "specialist", "depends_on": None},
                {"phase": "verify", "node": verifier, "role": "verifier", "depends_on": [specialist]},
            ]
            
            reviewers = [nid for nid, role in node_roles.items() if role == "reviewer"]
            if reviewers:
                plan["steps"].append({
                    "phase": "review",
                    "node": reviewers[0],
                    "role": "reviewer",
                    "depends_on": [verifier],
                })
        
        elif topology == TopologyType.DEBATE:
            proposer = [nid for nid, role in node_roles.items() if role == "proposer"][0]
            critic = [nid for nid, role in node_roles.items() if role == "critic"][0]
            verifier = [nid for nid, role in node_roles.items() if role == "verifier"][0]
            
            plan["steps"] = [
                {"round": 1, "phase": "propose", "node": proposer, "role": "proposer", "depends_on": None},
                {"round": 1, "phase": "critique", "node": critic, "role": "critic", "depends_on": [proposer]},
                {"round": 2, "phase": "counter", "node": proposer, "role": "proposer", "depends_on": [critic]},
                {"round": 2, "phase": "verify", "node": verifier, "role": "verifier", "depends_on": [proposer, critic]},
            ]
        
        return plan
    
    def _estimate_latency(self, node_ids: List[str], topology: TopologyType) -> float:
        """Estimate total latency for the topology."""
        latencies = []
        for nid in node_ids:
            node = self.nodes.get(nid)
            if node:
                latencies.append(node.performance.get("avg_latency_ms", 1000.0))
        
        if not latencies:
            return 0.0
        
        if topology in (TopologyType.PARALLEL, TopologyType.MAP_REDUCE, TopologyType.SWARM):
            return max(latencies)  # Parallel = max
        elif topology in (TopologyType.SEQUENTIAL, TopologyType.PIPELINE, TopologyType.DAG):
            return sum(latencies)  # Sequential = sum
        else:
            return sum(latencies)  # Conservative
    
    def _estimate_cost(self, node_ids: List[str], topology: TopologyType) -> float:
        """Estimate total cost."""
        costs = []
        for nid in node_ids:
            node = self.nodes.get(nid)
            if node:
                costs.append(node.performance.get("avg_cost_per_task", 0.01))
        
        if not costs:
            return 0.0
        
        if topology in (TopologyType.PARALLEL, TopologyType.MAP_REDUCE):
            return sum(costs)
        else:
            return sum(costs)  # All topologies pay for all agents
    
    def _calculate_confidence(
        self,
        candidates: List[RouteCandidate],
        selected_ids: List[str],
        topology: TopologyType
    ) -> float:
        """Calculate routing confidence."""
        selected = [c for c in candidates if c.node.node_id in selected_ids]
        if not selected:
            return 0.0
        
        # Average trust and capability coverage
        avg_trust = sum(c.trust_score for c in selected) / len(selected)
        avg_coverage = sum(c.capability_coverage for c in selected) / len(selected)
        
        # Topology appropriateness
        rule = self.topology_rules.get(topology, {})
        min_agents = rule.get("min_agents", 1)
        max_agents = rule.get("max_agents", 10)
        agent_count = len(selected)
        
        topology_fit = 1.0
        if agent_count < min_agents:
            topology_fit = agent_count / min_agents
        elif agent_count > max_agents:
            topology_fit = max_agents / agent_count
        
        return round((avg_trust * 0.4 + avg_coverage * 0.4 + topology_fit * 0.2), 4)
    
    def _get_overall_trust(self, node_ids: List[str]) -> str:
        """Get overall trust level for selected nodes."""
        scores = []
        for nid in node_ids:
            node = self.nodes.get(nid)
            if node:
                scores.append(node.get_overall_trust())
        
        if not scores:
            return "unknown"
        
        avg = sum(scores) / len(scores)
        if avg >= 0.8:
            return "trusted"
        elif avg >= 0.6:
            return "verified"
        elif avg >= 0.4:
            return "medium"
        elif avg >= 0.2:
            return "low"
        return "untrusted"
    
    def _build_reasoning(
        self,
        task: MeshTask,
        candidates: List[RouteCandidate],
        selected_ids: List[str],
        topology: TopologyType
    ) -> str:
        """Build human-readable routing reasoning."""
        eligible = [c for c in candidates if not c.rejection_reason]
        selected = [c for c in candidates if c.node.node_id in selected_ids]
        
        parts = [
            f"Task '{task.goal[:60]}...' requires {len(task.required_capabilities)} capabilities: {task.required_capabilities[:3]}",
            f"Found {len(eligible)} eligible nodes from {len(candidates)} candidates",
            f"Selected topology: {topology.value} with {len(selected)} agents",
        ]
        
        if selected:
            roles = {}
            for c in selected:
                role = c.node.metadata.get("assigned_role", "worker")
                roles[role] = roles.get(role, 0) + 1
            parts.append(f"Roles: {roles}")
        
        rejected = [c for c in candidates if c.rejection_reason]
        if rejected:
            reasons = set(c.rejection_reason for c in rejected)
            parts.append(f"Rejected {len(rejected)} nodes: {', '.join(list(reasons)[:3])}")
        
        return "; ".join(parts)


def create_mesh_router(
    trust_engine: MeshTrust,
    mesh_nodes: Dict[str, MeshNode],
    config: Dict[str, Any] = None
) -> MeshRouter:
    """Factory function to create a MeshRouter."""
    return MeshRouter(trust_engine, mesh_nodes, config)