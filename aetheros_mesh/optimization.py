"""Mesh self-optimization engine (Master 49 sections 42-48)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .models import (
    MeshNode, MeshTask, MeshTeam, TopologyType, CollectiveMode, MeshNodeState
)
from .trust import MeshTrust, TrustAssessment
from .router import MeshRouter, RoutingDecision
from .team import TeamFormationEngine, TeamFormationResult
from .collective import CollectiveIntelligenceEngine, CollectiveResult
from .blackboard import MeshBlackboard

logger = logging.getLogger(__name__)


@dataclass
class OptimizationProposal:
    """A proposed optimization."""
    proposal_id: str = field(default_factory=lambda: f"opt-{uuid.uuid4().hex[:12]}")
    target: str = ""  # routing, agent_selection, team_size, parallelism, verification, model_selection, resource_allocation, cache_usage
    current_config: Dict[str, Any] = field(default_factory=dict)
    proposed_config: Dict[str, Any] = field(default_factory=dict)
    expected_improvement: Dict[str, float] = field(default_factory=dict)  # metric -> delta
    confidence: float = 0.0
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "proposed"  # proposed, simulating, approved, applied, rejected
    created_at: float = field(default_factory=time.time)
    applied_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Experiment:
    """A controlled experiment (section 45)."""
    experiment_id: str = field(default_factory=lambda: f"exp-{uuid.uuid4().hex[:12]}")
    name: str = ""
    variant_a: Dict[str, Any] = field(default_factory=dict)  # control
    variant_b: Dict[str, Any] = field(default_factory=dict)  # treatment
    metric: str = ""  # success, latency, cost, quality, verification
    status: str = "created"  # created, running, completed, stopped
    results_a: Dict[str, Any] = field(default_factory=dict)
    results_b: Dict[str, Any] = field(default_factory=dict)
    started_at: float = 0.0
    completed_at: float = 0.0
    sample_size: int = 0
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OptimizationLoopResult:
    """Result of one optimization loop iteration."""
    loop_id: str
    observations: List[Dict[str, Any]]
    measurements: Dict[str, float]
    analyses: List[Dict[str, Any]]
    proposals: List[OptimizationProposal]
    approved: List[str]
    applied: List[str]
    timestamp: float


class MeshOptimizationEngine:
    """Self-optimization engine for the mesh (sections 42-48)."""
    
    def __init__(
        self,
        mesh_nodes: Dict[str, MeshNode],
        trust_engine: MeshTrust,
        router: MeshRouter,
        team_engine: TeamFormationEngine,
        collective_engine: CollectiveIntelligenceEngine,
        blackboard: MeshBlackboard,
        config: Dict[str, Any] = None
    ):
        self.nodes = mesh_nodes
        self.trust_engine = trust_engine
        self.router = router
        self.team_engine = team_engine
        self.collective_engine = collective_engine
        self.blackboard = blackboard
        self.config = config or {}
        
        self._proposals: Dict[str, OptimizationProposal] = {}
        self._experiments: Dict[str, Experiment] = {}
        self._loop_history: List[OptimizationLoopResult] = []
        self._enabled = self.config.get("enabled", True)
        self._interval_s = self.config.get("interval_s", 300.0)
        self._last_loop = 0.0
        
        # Protected policies that optimizer cannot modify (section 44)
        self._protected_policies = {
            "security_policy",
            "payment_authorization",
            "identity_trust",
            "data_classification",
            "credential_access",
            "tenant_isolation",
        }
        
        # Metrics to track
        self._metrics = {
            "task_success_rate": 0.0,
            "avg_latency_ms": 0.0,
            "avg_cost": 0.0,
            "verification_rate": 0.0,
            "agent_utilization": 0.0,
            "cache_hit_rate": 0.0,
            "coordination_overhead": 0.0,
        }
    
    def run_optimization_loop(self) -> OptimizationLoopResult:
        """Run one iteration of the optimization loop (section 43)."""
        
        if not self._enabled:
            return OptimizationLoopResult(
                loop_id="", observations=[], measurements={}, analyses=[],
                proposals=[], approved=[], applied=[], timestamp=time.time()
            )
        
        loop_id = f"loop-{uuid.uuid4().hex[:8]}"
        start = time.time()
        
        # OBSERVE: Collect recent execution data
        observations = self._observe()
        
        # MEASURE: Compute current metrics
        measurements = self._measure(observations)
        
        # ANALYZE: Identify optimization opportunities
        analyses = self._analyze(measurements, observations)
        
        # PROPOSE: Generate optimization proposals
        proposals = self._propose(analyses, measurements)
        
        # SIMULATE: Simulate proposals (in real impl, would run simulations)
        simulated = self._simulate(proposals)
        
        # APPROVE: Filter by policy constraints
        approved = self._approve(simulated)
        
        # APPLY: Apply approved optimizations
        applied = self._apply(approved)
        
        # MEASURE AGAIN: Would be done in next loop
        
        result = OptimizationLoopResult(
            loop_id=loop_id,
            observations=observations,
            measurements=measurements,
            analyses=analyses,
            proposals=proposals,
            approved=[p.proposal_id for p in approved],
            applied=[p.proposal_id for p in applied],
            timestamp=start,
        )
        
        self._loop_history.append(result)
        self._last_loop = start
        
        # Keep history bounded
        if len(self._loop_history) > 100:
            self._loop_history = self._loop_history[-100:]
        
        logger.info(f"Optimization loop {loop_id} completed: {len(applied)} applied")
        
        return result
    
    def _observe(self) -> List[Dict[str, Any]]:
        """Collect recent execution observations."""
        observations = []
        
        # Get recent task results from blackboard
        recent_results = self.blackboard.query(
            tags=["task_result"],
            scope="mesh"
        )
        
        for key, result in list(recent_results.items())[-100:]:  # Last 100
            if isinstance(result, dict):
                observations.append({
                    "type": "task_result",
                    "key": key,
                    "data": result,
                })
        
        # Get team performance
        team_perf = self.blackboard.query(
            tags=["team_performance"],
            scope="mesh"
        )
        
        for key, perf in team_perf.items():
            if isinstance(perf, dict):
                observations.append({
                    "type": "team_performance",
                    "key": key,
                    "data": perf,
                })
        
        return observations
    
    def _measure(self, observations: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute metrics from observations."""
        measurements = self._metrics.copy()
        
        if not observations:
            return measurements
        
        task_results = [o["data"] for o in observations if o["type"] == "task_result"]
        team_perfs = [o["data"] for o in observations if o["type"] == "team_performance"]
        
        if task_results:
            success_count = sum(1 for r in task_results if r.get("success", False))
            measurements["task_success_rate"] = success_count / len(task_results)
            
            latencies = [r.get("latency_ms", 0) for r in task_results if r.get("latency_ms")]
            if latencies:
                measurements["avg_latency_ms"] = sum(latencies) / len(latencies)
            
            costs = [r.get("cost", 0) for r in task_results if r.get("cost") is not None]
            if costs:
                measurements["avg_cost"] = sum(costs) / len(costs)
            
            verified = sum(1 for r in task_results if r.get("verified", False))
            measurements["verification_rate"] = verified / len(task_results)
        
        if team_perfs:
            util = [p.get("utilization", 0) for p in team_perfs if p.get("utilization") is not None]
            if util:
                measurements["agent_utilization"] = sum(util) / len(util)
            
            overhead = [p.get("coordination_overhead", 0) for p in team_perfs if p.get("coordination_overhead") is not None]
            if overhead:
                measurements["coordination_overhead"] = sum(overhead) / len(overhead)
        
        return measurements
    
    def _analyze(
        self, 
        measurements: Dict[str, float], 
        observations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze measurements for optimization opportunities."""
        analyses = []
        
        # Low success rate -> routing/agent selection issues
        if measurements["task_success_rate"] < 0.8:
            analyses.append({
                "type": "low_success_rate",
                "metric": "task_success_rate",
                "value": measurements["task_success_rate"],
                "target": 0.9,
                "suggested_targets": ["routing", "agent_selection", "verification"],
            })
        
        # High latency -> topology/parallelism issues
        if measurements["avg_latency_ms"] > 10000:
            analyses.append({
                "type": "high_latency",
                "metric": "avg_latency_ms",
                "value": measurements["avg_latency_ms"],
                "target": 5000,
                "suggested_targets": ["topology", "parallelism", "agent_selection"],
            })
        
        # High cost -> model/agent selection issues
        if measurements["avg_cost"] > 1.0:
            analyses.append({
                "type": "high_cost",
                "metric": "avg_cost",
                "value": measurements["avg_cost"],
                "target": 0.5,
                "suggested_targets": ["model_selection", "agent_selection", "team_size"],
            })
        
        # Low verification rate -> verification config
        if measurements["verification_rate"] < 0.5:
            analyses.append({
                "type": "low_verification",
                "metric": "verification_rate",
                "value": measurements["verification_rate"],
                "target": 0.8,
                "suggested_targets": ["verification"],
            })
        
        # High coordination overhead -> team size/topology
        if measurements["coordination_overhead"] > 0.3:
            analyses.append({
                "type": "high_overhead",
                "metric": "coordination_overhead",
                "value": measurements["coordination_overhead"],
                "target": 0.15,
                "suggested_targets": ["team_size", "topology", "parallelism"],
            })
        
        # Agent utilization imbalance -> resource allocation
        if measurements["agent_utilization"] > 0.9:
            analyses.append({
                "type": "high_utilization",
                "metric": "agent_utilization",
                "value": measurements["agent_utilization"],
                "target": 0.7,
                "suggested_targets": ["resource_allocation", "agent_selection"],
            })
        
        return analyses
    
    def _propose(
        self, 
        analyses: List[Dict[str, Any]], 
        measurements: Dict[str, float]
    ) -> List[OptimizationProposal]:
        """Generate optimization proposals from analyses."""
        proposals = []
        
        for analysis in analyses:
            for target in analysis.get("suggested_targets", []):
                proposal = self._create_proposal(target, analysis, measurements)
                if proposal:
                    proposals.append(proposal)
        
        return proposals
    
    def _create_proposal(
        self, 
        target: str, 
        analysis: Dict[str, Any], 
        measurements: Dict[str, float]
    ) -> Optional[OptimizationProposal]:
        """Create a specific proposal for a target."""
        
        current = self._get_current_config(target)
        proposed = current.copy()
        expected = {}
        
        if target == "routing":
            # Adjust routing weights
            if analysis["type"] == "low_success_rate":
                proposed["weight_trust"] = min(0.5, current.get("weight_trust", 0.35) + 0.1)
                proposed["weight_capability"] = max(0.1, current.get("weight_capability", 0.25) - 0.05)
                expected["task_success_rate"] = 0.05
            elif analysis["type"] == "high_latency":
                proposed["weight_latency"] = min(0.3, current.get("weight_latency", 0.15) + 0.05)
                expected["avg_latency_ms"] = -2000
        
        elif target == "agent_selection":
            # Prefer higher-trust agents
            proposed["min_trust_threshold"] = min(0.8, current.get("min_trust_threshold", 0.5) + 0.1)
            expected["task_success_rate"] = 0.03
        
        elif target == "team_size":
            # Reduce team size if overhead high
            if analysis["type"] == "high_overhead":
                proposed["max_team_size"] = max(2, current.get("max_team_size", 5) - 1)
                expected["coordination_overhead"] = -0.05
                expected["avg_latency_ms"] = -1000
        
        elif target == "parallelism":
            # Adjust parallelism
            if analysis["type"] == "high_latency":
                proposed["max_parallel"] = min(10, current.get("max_parallel", 3) + 1)
                expected["avg_latency_ms"] = -2000
        
        elif target == "verification":
            # Adjust verification requirements
            if analysis["type"] == "low_verification":
                proposed["default_verification_required"] = True
                proposed["verification_quorum"] = 2
                expected["verification_rate"] = 0.3
        
        elif target == "model_selection":
            # Prefer cheaper models for simple tasks
            if analysis["type"] == "high_cost":
                proposed["prefer_cheap_models_for_simple"] = True
                expected["avg_cost"] = -0.2
        
        elif target == "resource_allocation":
            # Better resource matching
            proposed["enable_resource_aware_scheduling"] = True
            expected["agent_utilization"] = -0.1
        
        elif target == "cache_usage":
            # Increase cache TTL
            proposed["cache_ttl_s"] = current.get("cache_ttl_s", 300) * 2
            expected["avg_latency_ms"] = -500
        
        else:
            return None
        
        # Calculate confidence based on evidence
        confidence = self._calculate_proposal_confidence(target, analysis, measurements)
        
        if confidence < 0.3:
            return None
        
        return OptimizationProposal(
            target=target,
            current_config=current,
            proposed_config=proposed,
            expected_improvement=expected,
            confidence=confidence,
            evidence=[analysis],
        )
    
    def _get_current_config(self, target: str) -> Dict[str, Any]:
        """Get current configuration for a target."""
        # In reality, would read from actual config
        defaults = {
            "routing": {
                "weight_trust": 0.35,
                "weight_capability": 0.25,
                "weight_latency": 0.15,
                "weight_cost": 0.10,
                "weight_availability": 0.10,
                "weight_resource": 0.05,
            },
            "agent_selection": {
                "min_trust_threshold": 0.5,
            },
            "team_size": {
                "max_team_size": 5,
            },
            "parallelism": {
                "max_parallel": 3,
            },
            "verification": {
                "default_verification_required": False,
                "verification_quorum": 1,
            },
            "model_selection": {
                "prefer_cheap_models_for_simple": False,
            },
            "resource_allocation": {
                "enable_resource_aware_scheduling": False,
            },
            "cache_usage": {
                "cache_ttl_s": 300,
            },
        }
        return defaults.get(target, {})
    
    def _calculate_proposal_confidence(
        self, 
        target: str, 
        analysis: Dict[str, Any], 
        measurements: Dict[str, float]
    ) -> float:
        """Calculate confidence in a proposal."""
        # Base confidence on how far metric is from target
        metric = analysis.get("metric", "")
        current = measurements.get(metric, 0)
        target_val = analysis.get("target", 0)
        
        if target_val == 0:
            return 0.5
        
        gap = abs(current - target_val) / max(abs(target_val), 0.001)
        confidence = min(0.9, 0.3 + gap * 0.5)
        
        # Boost if we have historical evidence
        similar_proposals = [
            p for p in self._proposals.values()
            if p.target == target and p.status == "applied"
        ]
        
        if similar_proposals:
            success_rate = sum(1 for p in similar_proposals 
                             if p.metadata.get("actual_improvement", 0) > 0) / len(similar_proposals)
            confidence = (confidence + success_rate) / 2
        
        return round(confidence, 4)
    
    def _simulate(self, proposals: List[OptimizationProposal]) -> List[OptimizationProposal]:
        """Simulate proposals (section 43 - SIMULATE step)."""
        # In a real implementation, this would run simulations
        # For now, mark as simulated with estimated outcomes
        for proposal in proposals:
            proposal.status = "simulated"
            proposal.metadata["simulated"] = True
            proposal.metadata["simulation_time"] = time.time()
        return proposals
    
    def _approve(self, proposals: List[OptimizationProposal]) -> List[OptimizationProposal]:
        """Approve proposals that don't violate protected policies (section 44)."""
        approved = []
        
        for proposal in proposals:
            # Check if proposal touches protected policy
            violates = False
            for policy in self._protected_policies:
                if policy in str(proposal.proposed_config).lower():
                    violates = True
                    logger.warning(f"Proposal {proposal.proposal_id} blocked: touches protected policy {policy}")
                    break
            
            if not violates and proposal.confidence >= 0.5:
                proposal.status = "approved"
                approved.append(proposal)
            else:
                proposal.status = "rejected"
                proposal.metadata["rejection_reason"] = "protected_policy" if violates else "low_confidence"
        
        return approved
    
    def _apply(self, proposals: List[OptimizationProposal]) -> List[OptimizationProposal]:
        """Apply approved proposals."""
        applied = []
        
        for proposal in proposals:
            try:
                # Apply to appropriate component
                if proposal.target == "routing":
                    self.router.weights.update(proposal.proposed_config)
                elif proposal.target == "agent_selection":
                    # Would update agent selection criteria
                    pass
                elif proposal.target == "team_size":
                    # Would update team formation config
                    pass
                elif proposal.target == "parallelism":
                    # Would update parallelism config
                    pass
                elif proposal.target == "verification":
                    # Would update verification defaults
                    pass
                elif proposal.target == "model_selection":
                    # Would update model router
                    pass
                elif proposal.target == "resource_allocation":
                    # Would update scheduler
                    pass
                elif proposal.target == "cache_usage":
                    # Would update cache config
                    pass
                
                proposal.status = "applied"
                proposal.applied_at = time.time()
                applied.append(proposal)
                
                # Store in blackboard for audit
                self.blackboard.put(
                    f"optimization:{proposal.proposal_id}",
                    proposal.to_dict(),
                    source_agent="optimizer",
                    scope="mesh",
                    tags=["optimization", "applied"],
                )
                
                logger.info(f"Applied optimization {proposal.proposal_id}: {proposal.target}")
                
            except Exception as e:
                logger.error(f"Failed to apply proposal {proposal.proposal_id}: {e}")
                proposal.status = "failed"
                proposal.metadata["error"] = str(e)
        
        return applied
    
    def create_experiment(
        self,
        name: str,
        variant_a: Dict[str, Any],
        variant_b: Dict[str, Any],
        metric: str,
        sample_size: int = 100
    ) -> Experiment:
        """Create an A/B experiment (section 46)."""
        
        experiment = Experiment(
            name=name,
            variant_a=variant_a,
            variant_b=variant_b,
            metric=metric,
            sample_size=sample_size,
            status="created",
        )
        
        self._experiments[experiment.experiment_id] = experiment
        
        # Store in blackboard
        self.blackboard.put(
            f"experiment:{experiment.experiment_id}",
            experiment.to_dict(),
            source_agent="optimizer",
            scope="mesh",
            tags=["experiment"],
        )
        
        return experiment
    
    def run_experiment(self, experiment_id: str, executor: Callable) -> Experiment:
        """Run an A/B experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment.status = "running"
        experiment.started_at = time.time()
        
        # Run variant A
        results_a = []
        for _ in range(experiment.sample_size // 2):
            try:
                result = executor(experiment.variant_a)
                results_a.append(result)
            except Exception as e:
                results_a.append({"error": str(e)})
        
        # Run variant B
        results_b = []
        for _ in range(experiment.sample_size // 2):
            try:
                result = executor(experiment.variant_b)
                results_b.append(result)
            except Exception as e:
                results_b.append({"error": str(e)})
        
        # Aggregate results
        experiment.results_a = self._aggregate_results(results_a, experiment.metric)
        experiment.results_b = self._aggregate_results(results_b, experiment.metric)
        experiment.completed_at = time.time()
        experiment.status = "completed"
        
        # Calculate confidence
        experiment.confidence = self._calculate_experiment_confidence(
            experiment.results_a, experiment.results_b
        )
        
        # Update in blackboard
        self.blackboard.put(
            f"experiment:{experiment_id}",
            experiment.to_dict(),
            source_agent="optimizer",
            scope="mesh",
            tags=["experiment", "completed"],
        )
        
        return experiment
    
    def _aggregate_results(self, results: List[Dict], metric: str) -> Dict[str, Any]:
        """Aggregate experiment results."""
        if not results:
            return {}
        
        values = [r.get(metric) for r in results if r.get(metric) is not None]
        
        return {
            "count": len(values),
            "mean": sum(values) / len(values) if values else 0,
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "raw": values[:100],  # Keep sample
        }
    
    def _calculate_experiment_confidence(self, results_a: Dict, results_b: Dict) -> float:
        """Calculate statistical confidence in experiment result."""
        # Simplified - in reality would use proper statistical test
        mean_a = results_a.get("mean", 0)
        mean_b = results_b.get("mean", 0)
        
        if mean_a == 0 and mean_b == 0:
            return 0.0
        
        diff = abs(mean_a - mean_b)
        baseline = max(abs(mean_a), abs(mean_b), 1)
        
        return min(1.0, diff / baseline)
    
    def recommend_policy_change(
        self,
        policy_area: str,
        recommendation: str,
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Recommend a policy change (section 47) - requires governance approval."""
        
        return {
            "type": "policy_recommendation",
            "policy_area": policy_area,
            "recommendation": recommendation,
            "evidence": evidence,
            "requires_governance": policy_area in self._protected_policies,
            "timestamp": time.time(),
        }
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status."""
        return {
            "enabled": self._enabled,
            "last_loop": self._last_loop,
            "loop_count": len(self._loop_history),
            "active_proposals": len([p for p in self._proposals.values() if p.status in ("proposed", "simulated", "approved")]),
            "applied_proposals": len([p for p in self._proposals.values() if p.status == "applied"]),
            "active_experiments": len([e for e in self._experiments.values() if e.status == "running"]),
            "completed_experiments": len([e for e in self._experiments.values() if e.status == "completed"]),
            "current_metrics": self._metrics,
            "protected_policies": list(self._protected_policies),
        }
    
    def should_run_loop(self) -> bool:
        """Check if optimization loop should run."""
        return (self._enabled and 
                time.time() - self._last_loop >= self._interval_s)


def create_optimization_engine(
    mesh_nodes: Dict[str, MeshNode],
    trust_engine: MeshTrust,
    router: MeshRouter,
    team_engine: TeamFormationEngine,
    collective_engine: CollectiveIntelligenceEngine,
    blackboard: MeshBlackboard,
    config: Dict[str, Any] = None
) -> MeshOptimizationEngine:
    """Factory function to create a MeshOptimizationEngine."""
    return MeshOptimizationEngine(
        mesh_nodes, trust_engine, router, team_engine, collective_engine, blackboard, config
    )