"""Dynamic team formation engine (Master 49 sections 39-41)."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import (
    MeshNode, MeshTask, MeshTeam, MeshNodeState, TopologyType, TrustDimension
)
from .trust import MeshTrust, TrustAssessment
from .router import MeshRouter, RouteCandidate, RoutingDecision

logger = logging.getLogger(__name__)


@dataclass
class TeamCandidate:
    """A candidate for team membership."""
    node: MeshNode
    role: str
    score: float
    capabilities_covered: Set[str]
    trust_assessment: TrustAssessment
    estimated_cost: float
    estimated_latency_ms: float


@dataclass
class TeamFormationResult:
    """Result of team formation."""
    team: MeshTeam
    candidates_considered: int
    formation_time_ms: float
    confidence: float
    reasoning: str
    alternatives: List[Dict[str, Any]] = field(default_factory=list)


class TeamFormationEngine:
    """Forms minimal effective teams for mesh tasks."""
    
    def __init__(
        self,
        trust_engine: MeshTrust,
        router: MeshRouter,
        nodes: Dict[str, MeshNode],
        config: Dict[str, Any] = None
    ):
        self.trust_engine = trust_engine
        self.router = router
        self.nodes = nodes
        self.config = config or {}
        
        # Role definitions for different topologies
        self.role_definitions = {
            TopologyType.SINGLE_AGENT: ["worker"],
            TopologyType.SEQUENTIAL: ["worker"] * 3,
            TopologyType.PARALLEL: ["worker"] * 3,
            TopologyType.DAG: ["coordinator"] + ["worker"] * 3,
            TopologyType.PIPELINE: ["stage_1", "stage_2", "stage_3"],
            TopologyType.HIERARCHICAL: ["coordinator", "team_lead", "specialist", "verifier"],
            TopologyType.SWARM: ["explorer"] * 3 + ["synthesizer"],
            TopologyType.DEBATE: ["proposer", "critic", "verifier"],
            TopologyType.MAP_REDUCE: ["reducer"] + ["mapper"] * 4,
            TopologyType.SPECIALIST_VERIFIER: ["specialist", "verifier"],
            TopologyType.LOCAL_REMOTE_HYBRID: ["local_worker", "remote_worker"],
        }
    
    def form_team(
        self,
        task: MeshTask,
        routing_decision: RoutingDecision = None,
        preferred_topology: TopologyType = None
    ) -> TeamFormationResult:
        """Form a team for the given task."""
        
        start_time = time.time()
        
        # Get routing decision if not provided
        if routing_decision is None:
            routing_decision = self.router.route(task, preferred_topology=preferred_topology)
        
        topology = routing_decision.topology
        selected_node_ids = routing_decision.selected_nodes
        
        # Get required roles for this topology
        required_roles = self.role_definitions.get(topology, ["worker"])
        
        # Assign roles to selected nodes
        members = []
        roles = {}
        
        for i, node_id in enumerate(selected_node_ids):
            role = required_roles[i] if i < len(required_roles) else "worker"
            members.append(node_id)
            roles[node_id] = role
        
        # Find coordinator
        coordinator_id = ""
        for node_id, role in roles.items():
            if role in ("coordinator", "reducer", "specialist", "proposer"):
                coordinator_id = node_id
                break
        if not coordinator_id and members:
            coordinator_id = members[0]
        
        # Create team
        team = MeshTeam(
            task_id=task.task_id,
            members=members,
            roles=roles,
            topology=topology,
            coordinator_id=coordinator_id,
            budget_allocated=task.cost_budget or 0.0,
        )
        
        # Calculate confidence
        confidence = routing_decision.confidence
        
        # Build reasoning
        reasoning = self._build_formation_reasoning(task, routing_decision, team)
        
        # Generate alternatives (what if we used different topology)
        alternatives = self._generate_alternatives(task, routing_decision)
        
        formation_time = (time.time() - start_time) * 1000
        
        return TeamFormationResult(
            team=team,
            candidates_considered=len(routing_decision.candidates),
            formation_time_ms=formation_time,
            confidence=confidence,
            reasoning=reasoning,
            alternatives=alternatives,
        )
    
    def _build_formation_reasoning(
        self,
        task: MeshTask,
        routing: RoutingDecision,
        team: MeshTeam
    ) -> str:
        """Build human-readable team formation reasoning."""
        parts = [
            f"Formed {routing.topology.value} team for task '{task.goal[:50]}...'",
            f"Team size: {len(team.members)} (roles: {dict(sorted(set(team.roles.values())))})",
            f"Coordinator: {team.coordinator_id[:12]}...",
            f"Routing confidence: {routing.confidence:.2f}",
            f"Estimated latency: {routing.estimated_latency_ms:.0f}ms, cost: ${routing.estimated_cost:.4f}",
        ]
        
        # Add capability coverage
        all_caps = set()
        for mid in team.members:
            node = self.nodes.get(mid)
            if node:
                all_caps.update(node.capabilities)
        
        required = set(task.required_capabilities)
        covered = required & all_caps
        missing = required - all_caps
        
        if missing:
            parts.append(f"WARNING: Missing capabilities: {missing}")
        else:
            parts.append(f"All {len(required)} required capabilities covered")
        
        return "; ".join(parts)
    
    def _generate_alternatives(
        self,
        task: MeshTask,
        chosen: RoutingDecision
    ) -> List[Dict[str, Any]]:
        """Generate alternative team formations."""
        alternatives = []
        
        # Try other topologies
        for topology in TopologyType:
            if topology == chosen.topology:
                continue
            
            # Quick check if topology is viable
            rule = self.router.topology_rules.get(topology, {})
            min_agents = rule.get("min_agents", 1)
            eligible_count = len([c for c in chosen.candidates if not c.rejection_reason])
            
            if eligible_count >= min_agents:
                # Simulate routing with this topology
                alt_routing = self.router.route(
                    task, 
                    available_nodes=[c.node for c in chosen.candidates if not c.rejection_reason],
                    preferred_topology=topology
                )
                
                if alt_routing.selected_nodes:
                    alternatives.append({
                        "topology": topology.value,
                        "team_size": len(alt_routing.selected_nodes),
                        "confidence": alt_routing.confidence,
                        "estimated_latency_ms": alt_routing.estimated_latency_ms,
                        "estimated_cost": alt_routing.estimated_cost,
                        "reasoning": f"Alternative {topology.value} topology",
                    })
        
        # Sort by confidence
        alternatives.sort(key=lambda a: a["confidence"], reverse=True)
        return alternatives[:3]  # Top 3 alternatives
    
    def reconfigure_team(
        self,
        team: MeshTeam,
        task: MeshTask,
        reason: str,
        failed_node_id: str = None,
        new_evidence: Dict[str, Any] = None
    ) -> TeamFormationResult:
        """Reconfigure team during execution (section 41)."""
        
        logger.info(f"Reconfiguring team {team.team_id}: {reason}")
        
        # Handle different reconfiguration reasons
        if reason == "agent_failure" and failed_node_id:
            return self._handle_agent_failure(team, task, failed_node_id)
        elif reason == "new_evidence" and new_evidence:
            return self._handle_new_evidence(team, task, new_evidence)
        elif reason == "budget_reduction":
            return self._handle_budget_reduction(team, task)
        elif reason == "latency_spike":
            return self._handle_latency_spike(team, task)
        elif reason == "policy_change":
            return self._handle_policy_change(team, task)
        
        # Default: re-form team
        return self.form_team(task)
    
    def _handle_agent_failure(
        self,
        team: MeshTeam,
        task: MeshTask,
        failed_node_id: str
    ) -> TeamFormationResult:
        """Replace a failed agent."""
        
        # Remove failed node
        if failed_node_id in team.members:
            team.members.remove(failed_node_id)
            del team.roles[failed_node_id]
        
        # Find replacement
        available = [
            n for n in self.nodes.values()
            if n.node_id not in team.members
            and n.is_available_for_task(task.required_capabilities)
            and n.get_overall_trust() >= 0.5
        ]
        
        if available:
            # Pick best replacement
            assessments = self.trust_engine.assess_nodes([n.node_id for n in available])
            best = max(available, key=lambda n: assessments[n.node_id].overall_score)
            
            team.members.append(best.node_id)
            team.roles[best.node_id] = team.roles.get(failed_node_id, "worker")
            
            logger.info(f"Replaced failed agent {failed_node_id[:12]} with {best.node_id[:12]}")
        
        # Recalculate confidence
        confidence = self._calculate_team_confidence(team)
        
        return TeamFormationResult(
            team=team,
            candidates_considered=len(available),
            formation_time_ms=0,
            confidence=confidence,
            reasoning=f"Replaced failed agent {failed_node_id[:12]}",
        )
    
    def _handle_new_evidence(
        self,
        team: MeshTeam,
        task: MeshTask,
        evidence: Dict[str, Any]
    ) -> TeamFormationResult:
        """Add verifier based on new evidence."""
        
        # Check if we need a verifier
        if evidence.get("requires_verification") and not any(r == "verifier" for r in team.roles.values()):
            # Find a verifier node
            available = [
                n for n in self.nodes.values()
                if n.node_id not in team.members
                and "verification" in n.capabilities
                and n.is_available_for_task(["verification"])
            ]
            
            if available:
                assessments = self.trust_engine.assess_nodes([n.node_id for n in available])
                best = max(available, key=lambda n: assessments[n.node_id].overall_score)
                
                team.members.append(best.node_id)
                team.roles[best.node_id] = "verifier"
                
                logger.info(f"Added verifier {best.node_id[:12]} based on new evidence")
        
        confidence = self._calculate_team_confidence(team)
        
        return TeamFormationResult(
            team=team,
            candidates_considered=len(available) if 'available' in locals() else 0,
            formation_time_ms=0,
            confidence=confidence,
            reasoning="Added verifier due to new evidence",
        )
    
    def _handle_budget_reduction(
        self,
        team: MeshTeam,
        task: MeshTask
    ) -> TeamFormationResult:
        """Simplify team due to budget reduction."""
        
        # Keep only essential roles
        essential_roles = {"coordinator", "specialist", "verifier", "reducer"}
        non_essential = [
            mid for mid, role in team.roles.items()
            if role not in essential_roles
        ]
        
        # Remove non-essential members (keep at least 1 worker)
        workers = [mid for mid, role in team.roles.items() if role == "worker"]
        removable = non_essential
        if len(workers) > 1:
            removable.extend(workers[:-1])  # Keep at least 1 worker
        
        for mid in removable:
            if mid in team.members:
                team.members.remove(mid)
            if mid in team.roles:
                del team.roles[mid]
        
        logger.info(f"Reduced team {team.team_id} to {len(team.members)} members due to budget")
        
        confidence = self._calculate_team_confidence(team)
        
        return TeamFormationResult(
            team=team,
            candidates_considered=0,
            formation_time_ms=0,
            confidence=confidence,
            reasoning="Simplified team due to budget reduction",
        )
    
    def _handle_latency_spike(
        self,
        team: MeshTeam,
        task: MeshTask
    ) -> TeamFormationResult:
        """Reroute to lower-latency agents."""
        
        # Find lower latency alternatives for current members
        for mid in team.members[:]:
            node = self.nodes.get(mid)
            if not node:
                continue
            
            current_latency = node.performance.get("avg_latency_ms", 1000)
            if current_latency > task.latency_sla_ms or current_latency > 5000:
                # Find faster alternative
                alternatives = [
                    n for n in self.nodes.values()
                    if n.node_id not in team.members
                    and n.performance.get("avg_latency_ms", 1000) < current_latency * 0.5
                    and n.is_available_for_task(task.required_capabilities)
                ]
                
                if alternatives:
                    assessments = self.trust_engine.assess_nodes([n.node_id for n in alternatives])
                    best = max(alternatives, key=lambda n: assessments[n.node_id].overall_score)
                    
                    team.members.remove(mid)
                    del team.roles[mid]
                    team.members.append(best.node_id)
                    team.roles[best.node_id] = "worker"
                    
                    logger.info(f"Replaced slow agent {mid[:12]} with faster {best.node_id[:12]}")
        
        confidence = self._calculate_team_confidence(team)
        
        return TeamFormationResult(
            team=team,
            candidates_considered=0,
            formation_time_ms=0,
            confidence=confidence,
            reasoning="Replaced slow agents due to latency spike",
        )
    
    def _handle_policy_change(
        self,
        team: MeshTeam,
        task: MeshTask
    ) -> TeamFormationResult:
        """Pause/replan due to policy change."""
        
        # Check if current team violates new policy
        # For now, just flag for replanning
        logger.warning(f"Policy change requires replanning for team {team.team_id}")
        
        return TeamFormationResult(
            team=team,
            candidates_considered=0,
            formation_time_ms=0,
            confidence=0.5,
            reasoning="Policy change detected - replan required",
        )
    
    def dissolve_team(self, team: MeshTeam) -> None:
        """Dissolve team after task completion (section 40)."""
        
        logger.info(f"Dissolving team {team.team_id}")
        
        team.active = False
        team.dissolved_at = time.time()
        
        # In a real implementation:
        # - Release resource locks
        # - Revoke temporary credentials
        # - Clear shared context
        # - Update node availability
        
        for mid in team.members:
            node = self.nodes.get(mid)
            if node and node.state == MeshNodeState.BUSY:
                node.update_state(MeshNodeState.AVAILABLE)
    
    def _calculate_team_confidence(self, team: MeshTeam) -> float:
        """Calculate team confidence score."""
        if not team.members:
            return 0.0
        
        assessments = self.trust_engine.assess_nodes(team.members)
        scores = [a.overall_score for a in assessments.values()]
        
        if not scores:
            return 0.0
        
        # Team confidence = average trust * role coverage bonus
        avg_trust = sum(scores) / len(scores)
        role_diversity = len(set(team.roles.values())) / max(len(team.members), 1)
        
        return round(avg_trust * 0.7 + role_diversity * 0.3, 4)
    
    def get_team_performance(self, team: MeshTeam) -> Dict[str, Any]:
        """Get team performance metrics."""
        if not team.members:
            return {}
        
        assessments = self.trust_engine.assess_nodes(team.members)
        
        return {
            "team_id": team.team_id,
            "size": len(team.members),
            "roles": team.roles,
            "topology": team.topology.value,
            "avg_trust": sum(a.overall_score for a in assessments.values()) / len(assessments),
            "avg_confidence": sum(a.overall_confidence for a in assessments.values()) / len(assessments),
            "budget_used": team.budget_used,
            "budget_allocated": team.budget_allocated,
            "active": team.active,
            "duration_s": time.time() - team.formed_at if team.active else team.dissolved_at - team.formed_at,
        }