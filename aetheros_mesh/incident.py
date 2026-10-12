"""Mesh incident response engine (Master 49 sections 71-78)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .models import MeshNode, MeshNodeState, MeshEdge, EdgeType
from .trust import MeshTrust, TrustAssessment
from .governance import MeshGovernanceEngine

logger = logging.getLogger(__name__)


class IncidentType(Enum):
    """Types of mesh incidents (section 71)."""
    AGENT_COMPROMISE = "agent_compromise"
    CREDENTIAL_MISUSE = "credential_misuse"
    ANOMALOUS_COMMUNICATION = "anomalous_communication"
    DATA_LEAKAGE = "data_leakage"
    ECONOMIC_ANOMALY = "economic_anomaly"
    COORDINATION_ATTACK = "coordination_attack"
    REPUTATION_ATTACK = "reputation_attack"
    NETWORK_PARTITION = "network_partition"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CASCADING_FAILURE = "cascading_failure"


class IncidentSeverity(Enum):
    """Incident severity levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class IncidentStatus(Enum):
    """Incident lifecycle status."""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class Incident:
    """A mesh security incident."""
    incident_id: str = field(default_factory=lambda: f"inc-{uuid.uuid4().hex[:12]}")
    type: IncidentType = IncidentType.AGENT_COMPROMISE
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    status: IncidentStatus = IncidentStatus.DETECTED
    title: str = ""
    description: str = ""
    affected_agents: List[str] = field(default_factory=list)
    affected_tasks: List[str] = field(default_factory=list)
    affected_artifacts: List[str] = field(default_factory=list)
    blast_radius: Dict[str, Any] = field(default_factory=dict)
    detection_method: str = ""
    detection_time: float = field(default_factory=time.time)
    contained_time: float = 0.0
    resolved_time: float = 0.0
    closed_time: float = 0.0
    mitigation_actions: List[Dict[str, Any]] = field(default_factory=list)
    verification_status: str = "pending"
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    assigned_to: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value
        d["severity"] = self.severity.value
        d["status"] = self.status.value
        return d


@dataclass
class ContaminationPath:
    """A path of evidence contamination (section 75)."""
    path_id: str = field(default_factory=lambda: f"cont-{uuid.uuid4().hex[:12]}")
    source_agent: str = ""
    source_output: str = ""
    propagation_steps: List[Dict[str, Any]] = field(default_factory=list)
    affected_artifacts: List[str] = field(default_factory=list)
    affected_agents: List[str] = field(default_factory=list)
    severity: float = 0.0
    detected_at: float = field(default_factory=time.time)
    contained: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MeshIncidentEngine:
    """Incident detection and response for the mesh (sections 71-78)."""
    
    def __init__(
        self,
        nodes: Dict[str, MeshNode],
        trust_engine: MeshTrust,
        governance: MeshGovernanceEngine,
        blackboard,
        config: Dict[str, Any] = None
    ):
        self.nodes = nodes
        self.trust_engine = trust_engine
        self.governance = governance
        self.blackboard = blackboard
        self.config = config or {}
        
        self._incidents: Dict[str, Incident] = {}
        self._contamination_paths: Dict[str, ContaminationPath] = {}
        self._detection_rules: List[Callable] = []
        self._response_handlers: Dict[IncidentType, Callable] = {}
        
        # Initialize default detection rules
        self._init_detection_rules()
        self._init_response_handlers()
        
        # Load persisted state
        self._load_state()
    
    def _init_detection_rules(self) -> None:
        """Initialize incident detection rules."""
        self._detection_rules = [
            self._detect_agent_compromise,
            self._detect_credential_misuse,
            self._detect_anomalous_communication,
            self._detect_data_leakage,
            self._detect_economic_anomaly,
            self._detect_coordination_attack,
            self._detect_reputation_attack,
            self._detect_network_partition,
            self._detect_resource_exhaustion,
        ]
    
    def _init_response_handlers(self) -> None:
        """Initialize incident response handlers."""
        self._response_handlers = {
            IncidentType.AGENT_COMPROMISE: self._handle_agent_compromise,
            IncidentType.CREDENTIAL_MISUSE: self._handle_credential_misuse,
            IncidentType.ANOMALOUS_COMMUNICATION: self._handle_anomalous_communication,
            IncidentType.DATA_LEAKAGE: self._handle_data_leakage,
            IncidentType.ECONOMIC_ANOMALY: self._handle_economic_anomaly,
            IncidentType.COORDINATION_ATTACK: self._handle_coordination_attack,
            IncidentType.REPUTATION_ATTACK: self._handle_reputation_attack,
            IncidentType.NETWORK_PARTITION: self._handle_network_partition,
            IncidentType.RESOURCE_EXHAUSTION: self._handle_resource_exhaustion,
            IncidentType.CASCADING_FAILURE: self._handle_cascading_failure,
        }
    
    def scan_for_incidents(self) -> List[Incident]:
        """Scan mesh for incidents using all detection rules."""
        new_incidents = []
        
        for rule in self._detection_rules:
            try:
                incidents = rule()
                new_incidents.extend(incidents)
            except Exception as e:
                logger.error(f"Detection rule {rule.__name__} failed: {e}")
        
        for incident in new_incidents:
            self._create_incident(incident)
        
        return new_incidents
    
    def _detect_agent_compromise(self) -> List[Incident]:
        """Detect compromised agents."""
        incidents = []
        
        for node_id, node in self.nodes.items():
            assessment = self.trust_engine.assess_node(node_id)
            
            # Check for security flags
            if "security_concerns" in assessment.flags:
                # Check for specific compromise indicators
                sec_dim = assessment.dimensions.get(TrustDimension.SECURITY, {})
                if sec_dim.get("score", 0) < -0.5:
                    incidents.append(Incident(
                        type=IncidentType.AGENT_COMPROMISE,
                        severity=IncidentSeverity.HIGH,
                        title=f"Possible agent compromise: {node_id}",
                        description=f"Security score {sec_dim.get('score', 0):.2f} indicates potential compromise",
                        affected_agents=[node_id],
                        detection_method="trust_assessment",
                        evidence=[assessment.to_dict()],
                    ))
            
            # Check for behavioral anomalies
            if "behavioral_anomalies" in assessment.flags:
                beh_dim = assessment.dimensions.get(TrustDimension.BEHAVIOR, {})
                if beh_dim.get("score", 0) < -0.5:
                    incidents.append(Incident(
                        type=IncidentType.AGENT_COMPROMISE,
                        severity=IncidentSeverity.MEDIUM,
                        title=f"Behavioral anomaly detected: {node_id}",
                        description=f"Behavior score {beh_dim.get('score', 0):.2f} indicates anomaly",
                        affected_agents=[node_id],
                        detection_method="trust_assessment",
                        evidence=[assessment.to_dict()],
                    ))
        
        return incidents
    
    def _detect_credential_misuse(self) -> List[Incident]:
        """Detect credential misuse."""
        incidents = []
        
        # Check for unusual access patterns
        access_log = self.blackboard.get_access_log(limit=1000)
        
        # Group by agent
        by_agent: Dict[str, List] = {}
        for entry in access_log:
            agent = entry.get("agent_id", "")
            if agent:
                by_agent.setdefault(agent, []).append(entry)
        
        for agent_id, entries in by_agent.items():
            # Check for rapid credential use
            if len(entries) > 100:  # Threshold
                time_span = entries[-1]["timestamp"] - entries[0]["timestamp"]
                if time_span < 60:  # More than 100 accesses in 1 minute
                    incidents.append(Incident(
                        type=IncidentType.CREDENTIAL_MISUSE,
                        severity=IncidentSeverity.HIGH,
                        title=f"Credential misuse suspected: {agent_id}",
                        description=f"{len(entries)} credential uses in {time_span:.0f}s",
                        affected_agents=[agent_id],
                        detection_method="access_pattern_analysis",
                        evidence=[{"agent_id": agent_id, "access_count": len(entries), "time_span": time_span}],
                    ))
        
        return incidents
    
    def _detect_anomalous_communication(self) -> List[Incident]:
        """Detect anomalous communication patterns."""
        incidents = []
        
        # Check for unusual message patterns in blackboard
        # This would analyze message flows between agents
        # For now, placeholder
        return incidents
    
    def _detect_data_leakage(self) -> List[Incident]:
        """Detect data leakage."""
        incidents = []
        
        # Check for sensitive data in unauthorized locations
        entries = self.blackboard.query(tags=["sensitive"])
        for key, entry in entries.items():
            if isinstance(entry, dict):
                # Check if entry has proper authorization
                auth = entry.get("_authorization", [])
                if not auth:
                    incidents.append(Incident(
                        type=IncidentType.DATA_LEAKAGE,
                        severity=IncidentSeverity.HIGH,
                        title=f"Unprotected sensitive data: {key}",
                        description="Sensitive data found without access controls",
                        affected_artifacts=[key],
                        detection_method="data_classification_audit",
                        evidence=[{"key": key, "entry": entry}],
                    ))
        
        return incidents
    
    def _detect_economic_anomaly(self) -> List[Incident]:
        """Detect economic anomalies."""
        incidents = []
        
        # Check for unusual spending patterns
        task_results = self.blackboard.query(tags=["task_result"], scope="mesh")
        
        by_agent: Dict[str, List[float]] = {}
        for key, result in task_results.items():
            if isinstance(result, dict):
                agent = result.get("agent_id", "")
                cost = result.get("cost", 0)
                if agent and cost > 0:
                    by_agent.setdefault(agent, []).append(cost)
        
        for agent_id, costs in by_agent.items():
            if len(costs) > 10:
                avg_cost = sum(costs) / len(costs)
                recent_costs = costs[-5:]
                recent_avg = sum(recent_costs) / len(recent_costs)
                
                if recent_avg > avg_cost * 3:  # 3x increase
                    incidents.append(Incident(
                        type=IncidentType.ECONOMIC_ANOMALY,
                        severity=IncidentSeverity.MEDIUM,
                        title=f"Economic anomaly: {agent_id}",
                        description=f"Cost increased from ${avg_cost:.4f} to ${recent_avg:.4f} avg",
                        affected_agents=[agent_id],
                        detection_method="cost_pattern_analysis",
                        evidence=[{"agent_id": agent_id, "baseline_avg": avg_cost, "recent_avg": recent_avg}],
                    ))
        
        return incidents
    
    def _detect_coordination_attack(self) -> List[Incident]:
        """Detect coordination attacks (e.g., Sybil, consensus manipulation)."""
        incidents = []
        
        # Check for correlated agents
        node_ids = list(self.nodes.keys())
        correlations = self.trust_engine.detect_correlated_agents(node_ids)
        
        for corr in correlations:
            if corr["type"] == "shared_organization" and corr["overlap"] > 0.8:
                incidents.append(Incident(
                    type=IncidentType.COORDINATION_ATTACK,
                    severity=IncidentSeverity.HIGH,
                    title=f"Potential Sybil/coordination attack",
                    description=f"Agents {corr['nodes']} share organization with {corr['overlap']:.0%} overlap",
                    affected_agents=corr["nodes"],
                    detection_method="correlation_analysis",
                    evidence=[corr],
                ))
            
            elif corr["type"] == "shared_reviewers" and corr["overlap"] > 0.5:
                incidents.append(Incident(
                    type=IncidentType.REPUTATION_ATTACK,
                    severity=IncidentSeverity.MEDIUM,
                    title=f"Potential reputation manipulation",
                    description=f"Agents {corr['nodes']} share reviewers with {corr['overlap']:.0%} overlap",
                    affected_agents=corr["nodes"],
                    detection_method="reviewer_correlation_analysis",
                    evidence=[corr],
                ))
        
        return incidents
    
    def _detect_reputation_attack(self) -> List[Incident]:
        """Detect reputation attacks."""
        incidents = []
        
        # Check for review bombing
        for node_id in self.nodes:
            assessment = self.trust_engine.assess_node(node_id)
            if "suspected_review_burst" in assessment.flags:
                incidents.append(Incident(
                    type=IncidentType.REPUTATION_ATTACK,
                    severity=IncidentSeverity.MEDIUM,
                    title=f"Review bombing suspected: {node_id}",
                    description="Burst of same-provenance feedback detected",
                    affected_agents=[node_id],
                    detection_method="reputation_analysis",
                    evidence=[assessment.to_dict()],
                ))
        
        return incidents
    
    def _detect_network_partition(self) -> List[Incident]:
        """Detect network partition."""
        incidents = []
        
        # Check for nodes that haven't been seen recently
        now = time.time()
        timeout = self.config.get("node_timeout_s", 120.0)
        
        unreachable = []
        for node_id, node in self.nodes.items():
            if node.last_seen < now - timeout:
                if node.state in (MeshNodeState.AVAILABLE, MeshNodeState.BUSY):
                    unreachable.append(node_id)
        
        if unreachable:
            # Check if it's a partition (multiple nodes) or single node failure
            if len(unreachable) > len(self.nodes) * 0.3:  # More than 30% unreachable
                incidents.append(Incident(
                    type=IncidentType.NETWORK_PARTITION,
                    severity=IncidentSeverity.CRITICAL,
                    title="Network partition detected",
                    description=f"{len(unreachable)} nodes unreachable ({len(unreachable)/len(self.nodes):.0%} of mesh)",
                    affected_agents=unreachable,
                    detection_method="heartbeat_monitoring",
                    evidence=[{"unreachable_count": len(unreachable), "total_nodes": len(self.nodes)}],
                ))
            else:
                for node_id in unreachable:
                    incidents.append(Incident(
                        type=IncidentType.NETWORK_PARTITION,
                        severity=IncidentSeverity.MEDIUM,
                        title=f"Node unreachable: {node_id}",
                        description=f"Node not seen for {now - self.nodes[node_id].last_seen:.0f}s",
                        affected_agents=[node_id],
                        detection_method="heartbeat_monitoring",
                        evidence=[{"node_id": node_id, "last_seen": self.nodes[node_id].last_seen}],
                    ))
        
        return incidents
    
    def _detect_resource_exhaustion(self) -> List[Incident]:
        """Detect resource exhaustion."""
        incidents = []
        
        for node_id, node in self.nodes.items():
            cpu_avail = node.resource_state.get("cpu_available", 1.0)
            mem_avail = node.resource_state.get("memory_available", 1.0)
            
            if cpu_avail < 0.1 or mem_avail < 0.1:
                incidents.append(Incident(
                    type=IncidentType.RESOURCE_EXHAUSTION,
                    severity=IncidentSeverity.HIGH,
                    title=f"Resource exhaustion: {node_id}",
                    description=f"CPU: {cpu_avail:.0%}, Memory: {mem_avail:.0%} available",
                    affected_agents=[node_id],
                    detection_method="resource_monitoring",
                    evidence=[{"cpu_available": cpu_avail, "memory_available": mem_avail}],
                ))
        
        return incidents
    
    def _detect_cascading_failure(self) -> List[Incident]:
        """Detect cascading failures (section 126)."""
        incidents = []
        
        # Check for multiple dependent failures
        recent_incidents = [
            inc for inc in self._incidents.values()
            if inc.detection_time > time.time() - 300  # Last 5 minutes
        ]
        
        if len(recent_incidents) >= 3:
            # Check if they're related (share agents or tasks)
            all_agents = set()
            for inc in recent_incidents:
                all_agents.update(inc.affected_agents)
            
            if len(all_agents) < len(recent_incidents) * 2:  # Overlap suggests cascade
                incidents.append(Incident(
                    type=IncidentType.CASCADING_FAILURE,
                    severity=IncidentSeverity.CRITICAL,
                    title="Cascading failure detected",
                    description=f"{len(recent_incidents)} incidents in 5min affecting {len(all_agents)} agents",
                    affected_agents=list(all_agents),
                    affected_tasks=list(set().union(*[set(inc.affected_tasks) for inc in recent_incidents])),
                    detection_method="incident_correlation",
                    evidence=[{"recent_incidents": [i.incident_id for i in recent_incidents]}],
                ))
        
        return incidents
    
    def _create_incident(self, incident: Incident) -> Incident:
        """Create and record an incident."""
        self._incidents[incident.incident_id] = incident
        
        # Log to blackboard
        self.blackboard.put(
            f"incident:{incident.incident_id}",
            incident.to_dict(),
            source_agent="incident_engine",
            scope="mesh",
            tags=["incident", incident.type.value],
        )
        
        # Trigger response
        self._respond_to_incident(incident)
        
        logger.warning(f"Incident detected: {incident.incident_id} - {incident.title}")
        return incident
    
    def _respond_to_incident(self, incident: Incident) -> None:
        """Execute incident response."""
        handler = self._response_handlers.get(incident.type)
        if handler:
            try:
                handler(incident)
            except Exception as e:
                logger.error(f"Incident response failed for {incident.incident_id}: {e}")
    
    def _handle_agent_compromise(self, incident: Incident) -> None:
        """Handle agent compromise (section 72)."""
        for agent_id in incident.affected_agents:
            # Isolate agent
            self.governance.quarantine_agent(agent_id, f"Incident {incident.incident_id}: {incident.title}", "incident_engine")
            
            # Quarantine evidence
            self.governance.evidence_quarantine(agent_id, f"Agent compromise: {incident.title}", "incident_engine")
            
            # Revoke capabilities
            node = self.nodes.get(agent_id)
            if node:
                node.update_state(MeshNodeState.SUSPENDED)
                node.metadata["compromise_incident"] = incident.incident_id
            
            # Record mitigation
            incident.mitigation_actions.append({
                "action": "quarantine_agent",
                "target": agent_id,
                "at": time.time(),
            })
            incident.mitigation_actions.append({
                "action": "quarantine_evidence",
                "target": agent_id,
                "at": time.time(),
            })
            
            # Build contamination graph
            self._build_contamination_graph(agent_id, incident.incident_id)
    
    def _handle_credential_misuse(self, incident: Incident) -> None:
        """Handle credential misuse."""
        for agent_id in incident.affected_agents:
            # Rotate credentials (would integrate with credential manager)
            # For now, quarantine
            self.governance.quarantine_agent(agent_id, f"Credential misuse: {incident.title}", "incident_engine")
            
            incident.mitigation_actions.append({
                "action": "quarantine_agent",
                "target": agent_id,
                "reason": "credential_misuse",
                "at": time.time(),
            })
    
    def _handle_anomalous_communication(self, incident: Incident) -> None:
        """Handle anomalous communication."""
        # Would implement communication analysis and blocking
        incident.mitigation_actions.append({
            "action": "monitor_communication",
            "target": incident.affected_agents[0] if incident.affected_agents else "unknown",
            "at": time.time(),
        })
    
    def _handle_data_leakage(self, incident: Incident) -> None:
        """Handle data leakage."""
        for artifact_id in incident.affected_artifacts:
            # Restrict access
            self.blackboard.put(
                artifact_id,
                {"_access_restricted": True, "_restriction_reason": f"Data leakage incident {incident.incident_id}"},
                source_agent="incident_engine",
                scope="mesh",
                tags=["restricted"],
            )
        
        incident.mitigation_actions.append({
            "action": "restrict_data_access",
            "targets": incident.affected_artifacts,
            "at": time.time(),
        })
    
    def _handle_economic_anomaly(self, incident: Incident) -> None:
        """Handle economic anomaly."""
        for agent_id in incident.affected_agents:
            # Freeze spending
            self.blackboard.put(
                f"economic:freeze:{agent_id}",
                {"frozen": True, "reason": f"Economic anomaly: {incident.title}", "at": time.time()},
                source_agent="incident_engine",
                scope="mesh",
                tags=["economic_freeze"],
            )
        
        incident.mitigation_actions.append({
            "action": "freeze_spending",
            "targets": incident.affected_agents,
            "at": time.time(),
        })
    
    def _handle_coordination_attack(self, incident: Incident) -> None:
        """Handle coordination attack."""
        for agent_id in incident.affected_agents:
            # Reduce trust significantly
            self.trust_engine.record_signal(
                self.trust_engine.record_signal(
                    type('Signal', (), {
                        'node_id': agent_id,
                        'dimension': 'security',
                        'source': 'security',
                        'kind': 'coordination_attack',
                        'value': -0.8,
                        'confidence': 0.9,
                        'evidence_ref': incident.incident_id,
                    })()
                )
            )
            
            # Quarantine if severe
            if incident.severity in (IncidentSeverity.HIGH, IncidentSeverity.CRITICAL):
                self.governance.quarantine_agent(agent_id, f"Coordination attack: {incident.title}", "incident_engine")
        
        incident.mitigation_actions.append({
            "action": "reduce_trust",
            "targets": incident.affected_agents,
            "at": time.time(),
        })
    
    def _handle_reputation_attack(self, incident: Incident) -> None:
        """Handle reputation attack."""
        # Flag affected agents' reputation
        for agent_id in incident.affected_agents:
            self.trust_engine.record_signal(
                type('Signal', (), {
                    'node_id': agent_id,
                    'dimension': 'behavior',
                    'source': 'security',
                    'kind': 'reputation_attack',
                    'value': -0.5,
                    'confidence': 0.7,
                    'evidence_ref': incident.incident_id,
                })()
            )
        
        incident.mitigation_actions.append({
            "action": "flag_reputation",
            "targets": incident.affected_agents,
            "at": time.time(),
        })
    
    def _handle_network_partition(self, incident: Incident) -> None:
        """Handle network partition (section 77)."""
        # Mark affected nodes as degraded/unavailable
        for agent_id in incident.affected_agents:
            node = self.nodes.get(agent_id)
            if node:
                node.update_state(MeshNodeState.DEGRADED)
        
        # If critical partition, activate degraded mode
        if incident.severity == IncidentSeverity.CRITICAL:
            self.blackboard.put(
                "mesh:degraded_mode",
                {"active": True, "reason": incident.incident_id, "at": time.time()},
                source_agent="incident_engine",
                scope="mesh",
                tags=["degraded_mode"],
            )
        
        incident.mitigation_actions.append({
            "action": "degraded_mode" if incident.severity == IncidentSeverity.CRITICAL else "mark_degraded",
            "targets": incident.affected_agents,
            "at": time.time(),
        })
    
    def _handle_resource_exhaustion(self, incident: Incident) -> None:
        """Handle resource exhaustion."""
        for agent_id in incident.affected_agents:
            node = self.nodes.get(agent_id)
            if node:
                node.update_state(MeshNodeState.DEGRADED)
            
            # Redistribute tasks from this node
            # Would integrate with task scheduler
        
        incident.mitigation_actions.append({
            "action": "mark_degraded_and_redistribute",
            "targets": incident.affected_agents,
            "at": time.time(),
        })
    
    def _handle_cascading_failure(self, incident: Incident) -> None:
        """Handle cascading failure."""
        # Emergency stop if critical
        if incident.severity == IncidentSeverity.CRITICAL:
            self.governance.emergency_stop("incident_engine", f"Cascading failure: {incident.title}")
        
        incident.mitigation_actions.append({
            "action": "emergency_stop" if incident.severity == IncidentSeverity.CRITICAL else "contain",
            "at": time.time(),
        })
    
    def _build_contamination_graph(self, source_agent: str, incident_id: str) -> ContaminationPath:
        """Build evidence contamination graph (section 75)."""
        
        # Find all outputs from this agent
        outputs = self.blackboard.query(source_agent=source_agent)
        
        path = ContaminationPath(
            source_agent=source_agent,
            source_output=list(outputs.keys())[0] if outputs else "unknown",
        )
        
        # Trace propagation through blackboard
        visited = set()
        queue = [(source_agent, "direct")]
        
        while queue:
            current_agent, step_type = queue.pop(0)
            if current_agent in visited:
                continue
            visited.add(current_agent)
            
            # Find agents that read this agent's outputs
            entries = self.blackboard.query(source_agent=current_agent)
            for key, entry in entries.items():
                if isinstance(entry, dict):
                    path.affected_artifacts.append(key)
                    
                    # Check if other agents used this
                    # This is simplified - real impl would track read access
                    for other_agent in self.nodes:
                        if other_agent != current_agent:
                            path.propagation_steps.append({
                                "from": current_agent,
                                "to": other_agent,
                                "artifact": key,
                                "step_type": step_type,
                            })
                            queue.append((other_agent, "derived"))
        
        path.affected_agents = list(visited)
        path.severity = min(1.0, len(path.affected_artifacts) / 10.0)
        
        self._contamination_paths[path.path_id] = path
        
        # Store in blackboard
        self.blackboard.put(
            f"contamination:{path.path_id}",
            path.to_dict(),
            source_agent="incident_engine",
            scope="mesh",
            tags=["contamination", incident_id],
        )
        
        return path
    
    def get_contamination_graph(self, agent_id: str) -> List[ContaminationPath]:
        """Get contamination paths for an agent."""
        return [
            p for p in self._contamination_paths.values()
            if p.source_agent == agent_id or agent_id in p.affected_agents
        ]
    
    def quarantine_evidence(self, path_id: str) -> bool:
        """Quarantine all evidence in a contamination path."""
        path = self._contamination_paths.get(path_id)
        if not path:
            return False
        
        for artifact in path.affected_artifacts:
            self.blackboard.put(
                artifact,
                {"_quarantined": True, "_quarantine_reason": f"Contamination path {path_id}", "_quarantined_at": time.time()},
                source_agent="incident_engine",
                scope="mesh",
                tags=["quarantined_evidence"],
            )
        
        path.contained = True
        return True
    
    def update_incident_status(
        self, 
        incident_id: str, 
        status: IncidentStatus,
        notes: str = ""
    ) -> Optional[Incident]:
        """Update incident status."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        
        incident.status = status
        
        if status == IncidentStatus.CONTAINED:
            incident.contained_time = time.time()
        elif status == IncidentStatus.RESOLVED:
            incident.resolved_time = time.time()
        elif status == IncidentStatus.CLOSED:
            incident.closed_time = time.time()
        
        if notes:
            incident.metadata["status_notes"] = incident.metadata.get("status_notes", "") + f"\n{time.time()}: {notes}"
        
        # Update in blackboard
        self.blackboard.put(
            f"incident:{incident_id}",
            incident.to_dict(),
            source_agent="incident_engine",
            scope="mesh",
            tags=["incident", incident.type.value],
        )
        
        return incident
    
    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get an incident by ID."""
        return self._incidents.get(incident_id)
    
    def list_incidents(
        self, 
        status: IncidentStatus = None,
        type: IncidentType = None,
        severity: IncidentSeverity = None,
        limit: int = 50
    ) -> List[Incident]:
        """List incidents with filters."""
        incidents = list(self._incidents.values())
        
        if status:
            incidents = [i for i in incidents if i.status == status]
        if type:
            incidents = [i for i in incidents if i.type == type]
        if severity:
            incidents = [i for i in incidents if i.severity == severity]
        
        incidents.sort(key=lambda i: i.detection_time, reverse=True)
        return incidents[:limit]
    
    def get_status(self) -> Dict[str, Any]:
        """Get incident engine status."""
        by_type = {}
        by_status = {}
        by_severity = {}
        
        for inc in self._incidents.values():
            by_type[inc.type.value] = by_type.get(inc.type.value, 0) + 1
            by_status[inc.status.value] = by_status.get(inc.status.value, 0) + 1
            by_severity[inc.severity.value] = by_severity.get(inc.severity.value, 0) + 1
        
        return {
            "total_incidents": len(self._incidents),
            "by_type": by_type,
            "by_status": by_status,
            "by_severity": by_severity,
            "contamination_paths": len(self._contamination_paths),
            "active_incidents": len([i for i in self._incidents.values() 
                                     if i.status in (IncidentStatus.DETECTED, IncidentStatus.INVESTIGATING, IncidentStatus.CONTAINED)]),
        }
    
    def _load_state(self) -> None:
        """Load persisted incident state."""
        try:
            file = self.blackboard.home / f"mesh_incidents_{self.blackboard.mesh_id}.json"
            if file.exists():
                data = json.loads(file.read_text(encoding="utf-8"))
                
                for inc_data in data.get("incidents", []):
                    inc_data["type"] = IncidentType(inc_data["type"])
                    inc_data["severity"] = IncidentSeverity(inc_data["severity"])
                    inc_data["status"] = IncidentStatus(inc_data["status"])
                    self._incidents[inc_data["incident_id"]] = Incident(**inc_data)
                
                for path_data in data.get("contamination_paths", []):
                    path = ContaminationPath(**path_data)
                    self._contamination_paths[path.path_id] = path
        except Exception as e:
            logger.warning(f"Failed to load incident state: {e}")
    
    def _save_state(self) -> None:
        """Persist incident state."""
        try:
            data = {
                "incidents": [i.to_dict() for i in self._incidents.values()],
                "contamination_paths": [p.to_dict() for p in self._contamination_paths.values()],
                "saved_at": time.time(),
            }
            
            file = self.blackboard.home / f"mesh_incidents_{self.blackboard.mesh_id}.json"
            tmp = file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(file)
        except Exception as e:
            logger.warning(f"Failed to save incident state: {e}")


def create_incident_engine(
    nodes: Dict[str, MeshNode],
    trust_engine: MeshTrust,
    governance: MeshGovernanceEngine,
    blackboard,
    config: Dict[str, Any] = None
) -> MeshIncidentEngine:
    """Factory function to create a MeshIncidentEngine."""
    return MeshIncidentEngine(nodes, trust_engine, governance, blackboard, config)