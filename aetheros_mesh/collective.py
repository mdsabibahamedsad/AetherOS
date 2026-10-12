"""Collective intelligence engine (Master 49 sections 10-23, 64-67)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .models import (
    MeshNode, MeshTask, MeshTeam, CollectiveResult, CollectiveMode, TrustDimension
)
from .trust import MeshTrust, TrustAssessment
from .blackboard import MeshBlackboard

logger = logging.getLogger(__name__)


@dataclass
class AgentOutput:
    """Output from a single agent in collective execution."""
    agent_id: str
    node_id: str
    role: str
    output: Dict[str, Any]
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5
    latency_ms: float = 0.0
    cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    independent: bool = True  # Was this generated independently?


@dataclass
class Disagreement:
    """A detected disagreement between agents."""
    disagreement_id: str = field(default_factory=lambda: f"dis-{uuid.uuid4().hex[:12]}")
    type: str = ""  # factual, interpretation, strategy, prediction, tool_result, source
    agents: List[str] = field(default_factory=list)
    claims: Dict[str, Any] = field(default_factory=dict)
    evidence: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    severity: float = 0.5  # 0-1
    detected_at: float = field(default_factory=time.time)
    resolved: bool = False
    resolution: str = ""
    resolution_method: str = ""


@dataclass
class CollectiveExecutionContext:
    """Context for collective execution."""
    task: MeshTask
    team: MeshTeam
    blackboard: MeshBlackboard
    mode: CollectiveMode
    max_rounds: int = 3
    max_tokens: int = 100000
    max_cost: float = 10.0
    max_time_s: float = 300.0
    verification_quorum: int = 1


class DisagreementEngine:
    """Detect and categorize disagreements (section 17)."""
    
    def __init__(self):
        self.disagreement_types = {
            "factual": self._detect_factual,
            "interpretation": self._detect_interpretation,
            "strategy": self._detect_strategy,
            "prediction": self._detect_prediction,
            "tool_result": self._detect_tool_result,
            "source": self._detect_source,
        }
    
    def detect_disagreements(
        self, 
        outputs: List[AgentOutput],
        task: MeshTask
    ) -> List[Disagreement]:
        """Detect all disagreements among agent outputs."""
        disagreements = []
        
        if len(outputs) < 2:
            return disagreements
        
        # Run all detectors
        for dis_type, detector in self.disagreement_types.items():
            detected = detector(outputs, task)
            disagreements.extend(detected)
        
        return disagreements
    
    def _detect_factual(
        self, 
        outputs: List[AgentOutput], 
        task: MeshTask
    ) -> List[Disagreement]:
        """Detect factual disagreements (contradicting facts)."""
        disagreements = []
        
        # Compare key factual claims
        for i, out1 in enumerate(outputs):
            for out2 in outputs[i+1:]:
                facts1 = self._extract_facts(out1.output)
                facts2 = self._extract_facts(out2.output)
                
                # Find contradictory facts
                for key, val1 in facts1.items():
                    if key in facts2:
                        val2 = facts2[key]
                        if self._values_contradict(val1, val2):
                            disagreements.append(Disagreement(
                                type="factual",
                                agents=[out1.agent_id, out2.agent_id],
                                claims={out1.agent_id: val1, out2.agent_id: val2},
                                evidence={
                                    out1.agent_id: out1.evidence,
                                    out2.agent_id: out2.evidence,
                                },
                                severity=0.8,
                            ))
        
        return disagreements
    
    def _detect_interpretation(
        self, 
        outputs: List[AgentOutput], 
        task: MeshTask
    ) -> List[Disagreement]:
        """Detect interpretation disagreements (same facts, different conclusions)."""
        disagreements = []
        
        # Compare conclusions/recommendations
        conclusions = {}
        for out in outputs:
            conclusion = out.output.get("conclusion") or out.output.get("recommendation") or out.output.get("summary", "")
            if conclusion:
                conclusions[out.agent_id] = conclusion
        
        # Check for divergent conclusions
        if len(set(conclusions.values())) > 1:
            disagreements.append(Disagreement(
                type="interpretation",
                agents=list(conclusions.keys()),
                claims=conclusions,
                severity=0.6,
            ))
        
        return disagreements
    
    def _detect_strategy(
        self, 
        outputs: List[AgentOutput], 
        task: MeshTask
    ) -> List[Disagreement]:
        """Detect strategy disagreements (different approaches)."""
        disagreements = []
        
        strategies = {}
        for out in outputs:
            strategy = out.output.get("strategy") or out.output.get("approach") or out.output.get("plan", "")
            if strategy:
                strategies[out.agent_id] = strategy
        
        if len(set(strategies.values())) > 1:
            disagreements.append(Disagreement(
                type="strategy",
                agents=list(strategies.keys()),
                claims=strategies,
                severity=0.5,
            ))
        
        return disagreements
    
    def _detect_prediction(
        self, 
        outputs: List[AgentOutput], 
        task: MeshTask
    ) -> List[Disagreement]:
        """Detect prediction disagreements."""
        disagreements = []
        
        predictions = {}
        for out in outputs:
            pred = out.output.get("prediction") or out.output.get("forecast", {})
            if pred:
                predictions[out.agent_id] = pred
        
        if len(predictions) > 1:
            # Compare numeric predictions
            for key in set().union(*[set(p.keys()) for p in predictions.values()]):
                values = {aid: p.get(key) for aid, p in predictions.items() if key in p}
                if len(set(str(v) for v in values.values())) > 1:
                    disagreements.append(Disagreement(
                        type="prediction",
                        agents=list(values.keys()),
                        claims={key: values},
                        severity=0.5,
                    ))
        
        return disagreements
    
    def _detect_tool_result(
        self, 
        outputs: List[AgentOutput], 
        task: MeshTask
    ) -> List[Disagreement]:
        """Detect tool result disagreements."""
        disagreements = []
        
        tool_results = {}
        for out in outputs:
            for ev in out.evidence:
                if ev.get("source") == "tool":
                    tool_name = ev.get("tool", "unknown")
                    result = ev.get("result")
                    if tool_name not in tool_results:
                        tool_results[tool_name] = {}
                    tool_results[tool_name][out.agent_id] = result
        
        for tool, results in tool_results.items():
            if len(set(str(r) for r in results.values())) > 1:
                disagreements.append(Disagreement(
                    type="tool_result",
                    agents=list(results.keys()),
                    claims={tool: results},
                    severity=0.7,
                ))
        
        return disagreements
    
    def _detect_source(
        self, 
        outputs: List[AgentOutput], 
        task: MeshTask
    ) -> List[Disagreement]:
        """Detect source disagreements (different sources cited)."""
        disagreements = []
        
        sources_by_agent = {}
        for out in outputs:
            sources = []
            for ev in out.evidence:
                src = ev.get("source_id") or ev.get("url") or ev.get("title")
                if src:
                    sources.append(src)
            if sources:
                sources_by_agent[out.agent_id] = sources
        
        # Check for source overlap
        if len(sources_by_agent) > 1:
            all_sources = set().union(*sources_by_agent.values())
            for src in all_sources:
                citing = [aid for aid, srcs in sources_by_agent.items() if src in srcs]
                if len(citing) == 1:
                    # Unique source - potential diversity or isolation
                    pass
                elif len(citing) < len(sources_by_agent):
                    # Some agents didn't use this source
                    pass
        
        return disagreements
    
    def _extract_facts(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """Extract factual claims from output."""
        facts = {}
        
        # Look for structured facts
        for key in ["facts", "findings", "data", "results", "metrics"]:
            if key in output and isinstance(output[key], dict):
                facts.update(output[key])
        
        # Also check top-level numeric/boolean values
        for key, val in output.items():
            if isinstance(val, (int, float, bool, str)) and key not in ["summary", "conclusion"]:
                facts[key] = val
        
        return facts
    
    def _values_contradict(self, val1: Any, val2: Any) -> bool:
        """Check if two values contradict."""
        # Same value = no contradiction
        if val1 == val2:
            return False
        
        # Boolean contradiction
        if isinstance(val1, bool) and isinstance(val2, bool):
            return val1 != val2
        
        # Numeric contradiction (significant difference)
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            if val1 == 0 and val2 == 0:
                return False
            diff = abs(val1 - val2) / max(abs(val1), abs(val2), 1)
            return diff > 0.2  # 20% difference
        
        # String contradiction (exact match only for now)
        if isinstance(val1, str) and isinstance(val2, str):
            return val1.lower() != val2.lower()
        
        return False


class ConsensusEngine:
    """Build consensus from multiple agent outputs (section 19)."""
    
    def __init__(self, trust_engine: MeshTrust):
        self.trust_engine = trust_engine
    
    def build_consensus(
        self,
        outputs: List[AgentOutput],
        disagreements: List[Disagreement],
        task: MeshTask,
        mode: CollectiveMode
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Build consensus from outputs.
        
        Returns: (consensus_result, metadata)
        """
        
        if not outputs:
            return {}, {"method": "no_outputs"}
        
        if mode == CollectiveMode.INDEPENDENT:
            return self._independent_consensus(outputs)
        elif mode == CollectiveMode.ENSEMBLE:
            return self._ensemble_consensus(outputs, disagreements)
        elif mode == CollectiveMode.DEBATE:
            return self._debate_consensus(outputs, disagreements)
        elif mode == CollectiveMode.CONSENSUS:
            return self._weighted_consensus(outputs, disagreements)
        elif mode == CollectiveMode.SPECIALIST_PANEL:
            return self._specialist_panel_consensus(outputs, disagreements)
        elif mode == CollectiveMode.VERIFICATION_PANEL:
            return self._verification_panel_consensus(outputs, disagreements)
        elif mode == CollectiveMode.RED_TEAM:
            return self._red_team_consensus(outputs, disagreements)
        else:
            return self._synthesis_consensus(outputs, disagreements)
    
    def _independent_consensus(self, outputs: List[AgentOutput]) -> Tuple[Dict, Dict]:
        """Independent: just collect all outputs without merging."""
        return {
            "method": "independent",
            "outputs": {o.agent_id: o.output for o in outputs},
            "note": "No consensus attempted - independent results collected",
        }, {"method": "independent"}
    
    def _ensemble_consensus(self, outputs: List[AgentOutput], disagreements: List[Disagreement]) -> Tuple[Dict, Dict]:
        """Ensemble: weight by trust and agreement."""
        
        # Get trust assessments
        node_ids = list(set(o.node_id for o in outputs))
        assessments = self.trust_engine.assess_nodes(node_ids)
        
        # Weight outputs by trust
        weighted_outputs = {}
        for out in outputs:
            assessment = assessments.get(out.node_id)
            weight = assessment.overall_score * assessment.overall_confidence if assessment else 0.5
            weighted_outputs[out.agent_id] = {"output": out.output, "weight": weight}
        
        # Find agreement clusters
        agreement_clusters = self._find_agreement_clusters(outputs, disagreements)
        
        # Select highest-weight cluster
        best_cluster = max(agreement_clusters, key=lambda c: sum(
            weighted_outputs.get(aid, {}).get("weight", 0) for aid in c
        )) if agreement_clusters else []
        
        if best_cluster:
            # Merge outputs from best cluster
            merged = self._merge_outputs([o for o in outputs if o.agent_id in best_cluster])
            return {
                "method": "ensemble",
                "result": merged,
                "participants": best_cluster,
                "agreement_level": len(best_cluster) / len(outputs),
            }, {"method": "ensemble", "cluster_size": len(best_cluster)}
        else:
            # No agreement - return highest trust output
            best = max(outputs, key=lambda o: weighted_outputs.get(o.agent_id, {}).get("weight", 0))
            return {
                "method": "ensemble_fallback",
                "result": best.output,
                "selected_agent": best.agent_id,
            }, {"method": "ensemble_fallback"}
    
    def _debate_consensus(self, outputs: List[AgentOutput], disagreements: List[Disagreement]) -> Tuple[Dict, Dict]:
        """Debate: structured proposal-critique-revision."""
        # This would be run iteratively during execution
        # Here we just synthesize the final debate state
        
        proposer = next((o for o in outputs if o.role == "proposer"), None)
        critic = next((o for o in outputs if o.role == "critic"), None)
        verifier = next((o for o in outputs if o.role == "verifier"), None)
        
        result = {}
        if proposer:
            result["proposal"] = proposer.output
        if critic:
            result["critique"] = critic.output
        if verifier:
            result["verification"] = verifier.output
        
        return {
            "method": "debate",
            "result": result,
            "note": "Debate structure preserved - final synthesis needed",
        }, {"method": "debate"}
    
    def _weighted_consensus(self, outputs: List[AgentOutput], disagreements: List[Disagreement]) -> Tuple[Dict, Dict]:
        """Weighted consensus by trust and evidence."""
        
        assessments = self.trust_engine.assess_nodes(list(set(o.node_id for o in outputs)))
        
        # Weight by trust * evidence quality
        weighted = []
        for out in outputs:
            assessment = assessments.get(out.node_id)
            trust_weight = assessment.overall_score * assessment.overall_confidence if assessment else 0.5
            evidence_weight = min(1.0, len(out.evidence) / 5.0) if out.evidence else 0.3
            weight = trust_weight * 0.7 + evidence_weight * 0.3
            weighted.append((out, weight))
        
        # Sort by weight
        weighted.sort(key=lambda x: x[1], reverse=True)
        
        # Take top contributors (up to quorum)
        quorum = max(2, len(outputs) // 2 + 1)
        top = weighted[:quorum]
        
        merged = self._merge_outputs([o for o, _ in top])
        
        return {
            "method": "weighted_consensus",
            "result": merged,
            "participants": [o.agent_id for o, _ in top],
            "weights": [w for _, w in top],
            "agreement": len(top) / len(outputs),
        }, {"method": "weighted_consensus", "quorum": quorum}
    
    def _specialist_panel_consensus(self, outputs: List[AgentOutput], disagreements: List[Disagreement]) -> Tuple[Dict, Dict]:
        """Specialist panel: domain experts weigh in."""
        
        # Group by role
        by_role = {}
        for out in outputs:
            by_role.setdefault(out.role, []).append(out)
        
        # Specialist output gets highest weight
        specialist = by_role.get("specialist", [None])[0]
        verifier = by_role.get("verifier", [None])[0]
        reviewers = by_role.get("reviewer", [])
        
        result = {}
        if specialist:
            result["specialist_analysis"] = specialist.output
        if verifier:
            result["verification"] = verifier.output
        if reviewers:
            result["reviews"] = {r.agent_id: r.output for r in reviewers}
        
        # Synthesis
        if specialist and verifier:
            merged = self._merge_outputs([specialist, verifier] + reviewers)
            result["synthesis"] = merged
        
        return {
            "method": "specialist_panel",
            "result": result,
        }, {"method": "specialist_panel"}
    
    def _verification_panel_consensus(self, outputs: List[AgentOutput], disagreements: List[Disagreement]) -> Tuple[Dict, Dict]:
        """Verification panel: multiple independent verifiers."""
        
        verifiers = [o for o in outputs if o.role == "verifier"]
        execute = [o for o in outputs if o.role != "verifier"]
        
        if not verifiers:
            return self._weighted_consensus(outputs, disagreements)
        
        # Check verification results
        passed = [v for v in verifiers if v.output.get("passed", False)]
        failed = [v for v in verifiers if not v.output.get("passed", True)]
        
        result = {
            "method": "verification_panel",
            "executed_by": [o.agent_id for o in execute],
            "verifiers": [v.agent_id for v in verifiers],
            "passed": len(passed),
            "failed": len(failed),
        }
        
        if len(passed) >= len(verifiers) / 2:
            result["result"] = execute[0].output if execute else {}
            result["status"] = "verified"
        else:
            result["result"] = {"error": "Verification failed"}
            result["status"] = "failed"
        
        return result, {"method": "verification_panel"}
    
    def _red_team_consensus(self, outputs: List[AgentOutput], disagreements: List[Disagreement]) -> Tuple[Dict, Dict]:
        """Red team: attacker + defender + verifier."""
        
        attacker = next((o for o in outputs if o.role == "attacker"), None)
        defender = next((o for o in outputs if o.role == "defender"), None)
        verifier = next((o for o in outputs if o.role == "verifier"), None)
        
        result = {"method": "red_team"}
        if attacker:
            result["attack"] = attacker.output
        if defender:
            result["defense"] = defender.output
        if verifier:
            result["verification"] = verifier.output
        
        return result, {"method": "red_team"}
    
    def _synthesis_consensus(self, outputs: List[AgentOutput], disagreements: List[Disagreement]) -> Tuple[Dict, Dict]:
        """General synthesis."""
        
        merged = self._merge_outputs(outputs)
        
        return {
            "method": "synthesis",
            "result": merged,
            "participants": [o.agent_id for o in outputs],
            "disagreements_count": len(disagreements),
        }, {"method": "synthesis"}
    
    def _find_agreement_clusters(
        self, 
        outputs: List[AgentOutput], 
        disagreements: List[Disagreement]
    ) -> List[List[str]]:
        """Find clusters of agreeing agents."""
        # Build agreement graph
        agreeing = {o.agent_id: set() for o in outputs}
        
        # Start with all pairs agreeing
        for i, o1 in enumerate(outputs):
            for o2 in outputs[i+1:]:
                agreeing[o1.agent_id].add(o2.agent_id)
                agreeing[o2.agent_id].add(o1.agent_id)
        
        # Remove edges for disagreements
        for dis in disagreements:
            for a1 in dis.agents:
                for a2 in dis.agents:
                    if a1 != a2:
                        agreeing[a1].discard(a2)
                        agreeing[a2].discard(a1)
        
        # Find connected components (clusters)
        visited = set()
        clusters = []
        
        for agent in agreeing:
            if agent in visited:
                continue
            
            cluster = []
            stack = [agent]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                cluster.append(current)
                stack.extend(agreeing[current] - visited)
            
            if cluster:
                clusters.append(cluster)
        
        return clusters
    
    def _merge_outputs(self, outputs: List[AgentOutput]) -> Dict[str, Any]:
        """Merge multiple agent outputs."""
        if not outputs:
            return {}
        if len(outputs) == 1:
            return outputs[0].output
        
        # Simple merge: combine unique keys, for conflicts keep highest confidence
        merged = {}
        for out in sorted(outputs, key=lambda o: o.confidence, reverse=True):
            for key, val in out.output.items():
                if key not in merged:
                    merged[key] = val
                elif isinstance(val, dict) and isinstance(merged[key], dict):
                    merged[key].update(val)
        
        # Add metadata
        merged["_synthesized_from"] = [o.agent_id for o in outputs]
        merged["_synthesis_method"] = "confidence_weighted_merge"
        
        return merged


class CollectiveIntelligenceEngine:
    """Orchestrates collective intelligence execution (section 10)."""
    
    def __init__(
        self,
        trust_engine: MeshTrust,
        blackboard: MeshBlackboard,
        executor: Callable[[MeshTask, MeshNode, Dict], AgentOutput] = None
    ):
        self.trust_engine = trust_engine
        self.blackboard = blackboard
        self.executor = executor or self._default_executor
        self.disagreement_engine = DisagreementEngine()
        self.consensus_engine = ConsensusEngine(trust_engine)
    
    def execute_collective(
        self,
        task: MeshTask,
        team: MeshTeam,
        mode: CollectiveMode = CollectiveMode.ENSEMBLE,
        context: Dict[str, Any] = None
    ) -> CollectiveResult:
        """Execute a task using collective intelligence."""
        
        logger.info(f"Starting collective execution: {mode.value} for task {task.task_id}")
        
        # Phase 1: Independent execution (section 11)
        independent_results = self._execute_independent(task, team, context)
        
        # Phase 2: Detect disagreements (section 17)
        disagreements = self.disagreement_engine.detect_disagreements(
            independent_results, task
        )
        
        # Phase 3: Build consensus (section 19)
        consensus_result, consensus_meta = self.consensus_engine.build_consensus(
            independent_results, disagreements, task, mode
        )
        
        # Phase 4: Verification if required (section 64)
        verification = {}
        if task.verification_required:
            verification = self._verify_result(consensus_result, independent_results, task)
        
        # Phase 5: Calculate final confidence
        confidence = self._calculate_confidence(
            independent_results, disagreements, verification, consensus_meta
        )
        
        # Phase 6: Build collective result
        result = CollectiveResult(
            task_id=task.task_id,
            participants=[o.agent_id for o in independent_results],
            independentResults={o.agent_id: o.output for o in independent_results},
            agreements=self._extract_agreements(independent_results, disagreements),
            disagreements=[asdict(d) for d in disagreements],
            evidence=self._collect_evidence(independent_results),
            verification=verification,
            confidence=confidence,
            decision=consensus_result.get("result", consensus_result).get("summary", "") if isinstance(consensus_result.get("result"), dict) else str(consensus_result),
            rationale=consensus_result.get("rationale", ""),
            uncertainty=self._assess_uncertainty(disagreements, verification),
        )
        
        # Store in blackboard
        self.blackboard.put(f"collective_result:{task.task_id}", result.to_dict(), 
                          source_agent="collective_engine", confidence=confidence)
        
        return result
    
    def _execute_independent(
        self,
        task: MeshTask,
        team: MeshTeam,
        context: Dict[str, Any] = None
    ) -> List[AgentOutput]:
        """Execute task independently on each agent (section 11)."""
        
        outputs = []
        
        for node_id in team.members:
            node = self.nodes.get(node_id) if hasattr(self, 'nodes') else None
            if not node:
                # Create minimal node
                node = MeshNode(node_id=node_id, agent_id=node_id)
            
            role = team.roles.get(node_id, "worker")
            
            # Prepare agent-specific context
            agent_context = {
                "task": task.to_dict(),
                "team": team.to_dict(),
                "role": role,
                "blackboard_view": self.blackboard.get_view(node_id),
                **(context or {}),
            }
            
            # Execute (independent - no cross-agent visibility)
            try:
                output = self.executor(task, node, agent_context)
                output.independent = True
                outputs.append(output)
            except Exception as e:
                logger.error(f"Agent {node_id} execution failed: {e}")
                outputs.append(AgentOutput(
                    agent_id=node_id,
                    node_id=node_id,
                    role=role,
                    output={"error": str(e)},
                    confidence=0.0,
                ))
        
        return outputs
    
    def _default_executor(
        self,
        task: MeshTask,
        node: MeshNode,
        context: Dict[str, Any]
    ) -> AgentOutput:
        """Default executor - in reality would call actual agent."""
        # This is a placeholder - real implementation would delegate to actual agents
        return AgentOutput(
            agent_id=node.agent_id,
            node_id=node.node_id,
            role=context.get("role", "worker"),
            output={"summary": f"Executed by {node.agent_id}", "status": "completed"},
            evidence=[],
            confidence=0.7,
        )
    
    def _verify_result(
        self,
        consensus_result: Dict[str, Any],
        independent_results: List[AgentOutput],
        task: MeshTask
    ) -> Dict[str, Any]:
        """Independent result verification (section 64)."""
        
        # Find verifier agents
        verifiers = [o for o in independent_results if o.role == "verifier"]
        
        if not verifiers:
            return {"status": "no_verifier", "note": "No verifier agents in team"}
        
        verification_results = []
        for verifier in verifiers:
            # Verifier checks the consensus result
            v_context = {
                "result_to_verify": consensus_result,
                "original_outputs": {o.agent_id: o.output for o in independent_results},
                "task": task.to_dict(),
            }
            
            try:
                v_output = self.executor(task, 
                    MeshNode(node_id=verifier.node_id, agent_id=verifier.agent_id), 
                    v_context)
                verification_results.append({
                    "verifier": verifier.agent_id,
                    "passed": v_output.output.get("passed", False),
                    "details": v_output.output,
                })
            except Exception as e:
                verification_results.append({
                    "verifier": verifier.agent_id,
                    "passed": False,
                    "error": str(e),
                })
        
        passed_count = sum(1 for v in verification_results if v.get("passed"))
        required = task.verification_quorum
        
        return {
            "status": "passed" if passed_count >= required else "failed",
            "passed": passed_count,
            "total": len(verification_results),
            "required": required,
            "details": verification_results,
        }
    
    def _calculate_confidence(
        self,
        outputs: List[AgentOutput],
        disagreements: List[Disagreement],
        verification: Dict[str, Any],
        consensus_meta: Dict[str, Any]
    ) -> float:
        """Calculate final confidence (section 131)."""
        
        if not outputs:
            return 0.0
        
        # Base: average agent confidence weighted by trust
        node_ids = list(set(o.node_id for o in outputs))
        assessments = self.trust_engine.assess_nodes(node_ids)
        
        weighted_conf = 0.0
        total_weight = 0.0
        
        for out in outputs:
            assessment = assessments.get(out.node_id)
            trust_weight = assessment.overall_score * assessment.overall_confidence if assessment else 0.5
            weight = trust_weight * out.confidence
            weighted_conf += weight * out.confidence
            total_weight += weight
        
        base_confidence = weighted_conf / total_weight if total_weight else 0.5
        
        # Adjust for disagreements
        disagreement_penalty = min(0.5, len(disagreements) * 0.1)
        base_confidence *= (1.0 - disagreement_penalty)
        
        # Boost for verification
        if verification.get("status") == "passed":
            base_confidence = min(1.0, base_confidence + 0.1)
        elif verification.get("status") == "failed":
            base_confidence *= 0.5
        
        # Adjust for consensus method
        method = consensus_meta.get("method", "")
        if method == "ensemble":
            base_confidence *= 1.05
        elif method == "weighted_consensus":
            base_confidence *= 1.1
        
        return round(min(1.0, max(0.0, base_confidence)), 4)
    
    def _extract_agreements(
        self, 
        outputs: List[AgentOutput], 
        disagreements: List[Disagreement]
    ) -> List[Dict[str, Any]]:
        """Extract agreements from outputs."""
        agreements = []
        
        # Find common keys with same values across outputs
        if len(outputs) < 2:
            return agreements
        
        all_keys = set()
        for out in outputs:
            all_keys.update(out.output.keys())
        
        for key in all_keys:
            values = {}
            for out in outputs:
                if key in out.output:
                    values[out.agent_id] = out.output[key]
            
            # Check if all agree
            if len(values) >= 2 and len(set(str(v) for v in values.values())) == 1:
                agreements.append({
                    "key": key,
                    "value": list(values.values())[0],
                    "agents": list(values.keys()),
                })
        
        return agreements
    
    def _collect_evidence(self, outputs: List[AgentOutput]) -> List[Dict[str, Any]]:
        """Collect all evidence from outputs."""
        evidence = []
        for out in outputs:
            for ev in out.evidence:
                ev_copy = ev.copy()
                ev_copy["source_agent"] = out.agent_id
                evidence.append(ev_copy)
        return evidence
    
    def _assess_uncertainty(
        self, 
        disagreements: List[Disagreement], 
        verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess uncertainty in the result (section 132)."""
        
        uncertainty = {
            "known": [],
            "likely": [],
            "uncertain": [],
            "conflicting": [],
            "unknown": [],
        }
        
        # Disagreements -> conflicting
        for dis in disagreements:
            uncertainty["conflicting"].append({
                "type": dis.type,
                "agents": dis.agents,
                "claims": dis.claims,
                "severity": dis.severity,
            })
        
        # Verification failure -> uncertain
        if verification.get("status") == "failed":
            uncertainty["uncertain"].append({
                "reason": "verification_failed",
                "details": verification,
            })
        
        # No verification -> unknown
        if verification.get("status") == "no_verifier":
            uncertainty["unknown"].append({
                "reason": "no_independent_verification",
            })
        
        return uncertainty


def create_collective_engine(
    trust_engine: MeshTrust,
    blackboard: MeshBlackboard,
    executor: Callable = None
) -> CollectiveIntelligenceEngine:
    """Factory function to create a CollectiveIntelligenceEngine."""
    return CollectiveIntelligenceEngine(trust_engine, blackboard, executor)