"""Global Agent Mesh - Main orchestrator (Master 49)."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .models import (
    MeshNode, MeshNodeState, MeshTask, MeshTeam, MeshConfig, MeshEdge, EdgeType,
    TopologyType, CollectiveMode, CollectiveResult, TrustDimension,
    create_mesh_node_from_agent_card
)
from .discovery import MeshDiscovery, DiscoverySource, DiscoveryResult
from .trust import MeshTrust, TrustAssessment
from .router import MeshRouter, RoutingDecision
from .team import TeamFormationEngine, TeamFormationResult
from .collective import CollectiveIntelligenceEngine, AgentOutput
from .blackboard import MeshBlackboard
from .optimization import MeshOptimizationEngine, OptimizationProposal, Experiment
from .governance import MeshGovernanceEngine, Policy, GovernanceDecision, PolicyLevel
from .incident import MeshIncidentEngine, Incident, IncidentType, IncidentSeverity, IncidentStatus

logger = logging.getLogger(__name__)


@dataclass
class MeshStatus:
    """Current mesh status."""
    mesh_id: str
    state: str  # starting, running, degraded, stopped
    node_count: int = 0
    active_nodes: int = 0
    team_count: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    incidents_open: int = 0
    last_optimization: float = 0.0
    uptime_seconds: float = 0.0


class GlobalAgentMesh:
    """Main Global Agent Mesh orchestrator.
    
    Integrates all mesh components into a unified distributed intelligence layer.
    """
    
    def __init__(
        self,
        home: Path,
        organization_id: str = "default",
        mesh_id: str = "",
        config: Dict[str, Any] = None
    ):
        self.home = Path(home)
        self.organization_id = organization_id
        self.mesh_id = mesh_id or f"mesh-{uuid.uuid4().hex[:12]}"
        self.config = config or {}
        
        # Core state
        self._nodes: Dict[str, MeshNode] = {}
        self._edges: Dict[str, Dict[str, List[str]]] = {}  # source -> edge_type -> targets
        self._tasks: Dict[str, MeshTask] = {}
        self._teams: Dict[str, MeshTeam] = {}
        self._state = "starting"
        self._start_time = time.time()
        self._lock = threading.RLock()
        
        # Initialize components
        self._init_components()
        
        # Background threads
        self._running = False
        self._threads: List[threading.Thread] = []
        
        # Event callbacks
        self._event_callbacks: Dict[str, List[Callable]] = {}
    
    def _init_components(self) -> None:
        """Initialize all mesh components."""
        
        # Mesh config
        mesh_config_dict = self.config.get("mesh", {})
        self.mesh_config = MeshConfig(**mesh_config_dict)
        
        # Discovery
        self.discovery = MeshDiscovery(
            mesh_id=self.mesh_id,
            home=self.home,
            organization_id=self.organization_id,
        )
        
        # Trust engine
        self.trust = MeshTrust(self.home, self.mesh_id)
        
        # Blackboard
        self.blackboard = MeshBlackboard(self.home, self.mesh_id)
        
        # Router
        self.router = MeshRouter(self.trust, self._nodes, self.config.get("router", {}))
        
        # Team formation
        self.team_engine = TeamFormationEngine(
            self.trust, self.router, self._nodes, self.config.get("team", {})
        )
        
        # Collective intelligence
        self.collective = CollectiveIntelligenceEngine(
            self.trust, self.blackboard, executor=self._default_executor
        )
        
        # Optimization
        self.optimization = MeshOptimizationEngine(
            self._nodes, self.trust, self.router, self.team_engine,
            self.collective, self.blackboard, self.config.get("optimization", {})
        )
        
        # Governance
        self.governance = MeshGovernanceEngine(
            self.trust, self._nodes, self.blackboard, self.config.get("governance", {})
        )
        
        # Incident response
        self.incident = MeshIncidentEngine(
            self._nodes, self.trust, self.governance, self.blackboard, 
            self.config.get("incident", {})
        )
        
        # Wire discovery to nodes
        self.discovery.add_discovery_callback(self._on_node_discovered)
    
    def _default_executor(
        self,
        task: MeshTask,
        node: MeshNode,
        context: Dict[str, Any]
    ) -> AgentOutput:
        """Default task executor - integrates with AetherOS agent system."""
        # This would integrate with run_agent.py / delegate_tool
        # For now, return a placeholder
        return AgentOutput(
            agent_id=node.agent_id,
            node_id=node.node_id,
            role=context.get("role", "worker"),
            output={"summary": f"Executed by {node.agent_id}", "status": "completed"},
            evidence=[],
            confidence=0.7,
        )
    
    def _on_node_discovered(self, node: MeshNode) -> None:
        """Callback when a new node is discovered."""
        with self._lock:
            self._nodes[node.node_id] = node
            self._emit_event("node_discovered", node.to_dict())
    
    def start(self) -> None:
        """Start the mesh."""
        logger.info(f"Starting Global Agent Mesh: {self.mesh_id}")
        
        self._running = True
        self._state = "running"
        
        # Initial discovery
        self.discovery.discover_all(force_refresh=True)
        
        # Start background threads
        self._start_background_threads()
        
        self._emit_event("mesh_started", {"mesh_id": self.mesh_id})
        logger.info(f"Mesh {self.mesh_id} started with {len(self._nodes)} nodes")
    
    def stop(self) -> None:
        """Stop the mesh gracefully (section 95)."""
        logger.info(f"Stopping Global Agent Mesh: {self.mesh_id}")
        
        self._running = False
        self._state = "stopping"
        
        # Wait for background threads
        for thread in self._threads:
            thread.join(timeout=10.0)
        
        # Checkpoint active tasks
        self._checkpoint_tasks()
        
        # Persist state
        self._persist_all()
        
        self._state = "stopped"
        self._emit_event("mesh_stopped", {"mesh_id": self.mesh_id})
        logger.info(f"Mesh {self.mesh_id} stopped")
    
    def _start_background_threads(self) -> None:
        """Start background maintenance threads."""
        
        # Discovery refresh thread
        discovery_thread = threading.Thread(
            target=self._discovery_loop,
            daemon=True,
            name=f"mesh-discovery-{self.mesh_id}"
        )
        discovery_thread.start()
        self._threads.append(discovery_thread)
        
        # Incident scanning thread
        incident_thread = threading.Thread(
            target=self._incident_loop,
            daemon=True,
            name=f"mesh-incident-{self.mesh_id}"
        )
        incident_thread.start()
        self._threads.append(incident_thread)
        
        # Optimization thread
        if self.optimization._enabled:
            opt_thread = threading.Thread(
                target=self._optimization_loop,
                daemon=True,
                name=f"mesh-optimization-{self.mesh_id}"
            )
            opt_thread.start()
            self._threads.append(opt_thread)
        
        # Heartbeat/health check thread
        health_thread = threading.Thread(
            target=self._health_loop,
            daemon=True,
            name=f"mesh-health-{self.mesh_id}"
        )
        health_thread.start()
        self._threads.append(health_thread)
    
    def _discovery_loop(self) -> None:
        """Periodic discovery refresh."""
        while self._running:
            try:
                time.sleep(300)  # 5 minutes
                if self._running:
                    self.discovery.discover_all()
            except Exception as e:
                logger.error(f"Discovery loop error: {e}")
    
    def _incident_loop(self) -> None:
        """Periodic incident scanning."""
        while self._running:
            try:
                time.sleep(60)  # 1 minute
                if self._running:
                    self.incident.scan_for_incidents()
            except Exception as e:
                logger.error(f"Incident loop error: {e}")
    
    def _optimization_loop(self) -> None:
        """Periodic optimization loop."""
        while self._running:
            try:
                if self.optimization.should_run_loop():
                    self.optimization.run_optimization_loop()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Optimization loop error: {e}")
    
    def _health_loop(self) -> None:
        """Periodic health checks."""
        while self._running:
            try:
                time.sleep(30)
                if self._running:
                    self._check_node_health()
            except Exception as e:
                logger.error(f"Health loop error: {e}")
    
    def _check_node_health(self) -> None:
        """Check node health and update states."""
        with self._lock:
            now = time.time()
            timeout = self.mesh_config.node_timeout_s
            
            for node in self._nodes.values():
                if node.state in (MeshNodeState.AVAILABLE, MeshNodeState.BUSY):
                    if now - node.last_seen > timeout:
                        node.update_state(MeshNodeState.UNAVAILABLE)
                        self._emit_event("node_unavailable", node.to_dict())
    
    def _checkpoint_tasks(self) -> None:
        """Checkpoint active tasks for recovery."""
        for task in self._tasks.values():
            if task.status in ("running", "pending"):
                self.blackboard.put(
                    f"task_checkpoint:{task.task_id}",
                    task.to_dict(),
                    source_agent="mesh",
                    scope="mesh",
                    tags=["checkpoint"],
                )
    
    def _persist_all(self) -> None:
        """Persist all mesh state."""
        # Discovery cache is auto-saved
        # Trust signals auto-saved
        # Blackboard auto-saved
        # Governance auto-saved
        # Incidents auto-saved
        pass
    
    # --- Node Management ---
    
    def add_node(self, node: MeshNode) -> bool:
        """Add a node to the mesh."""
        with self._lock:
            if node.node_id in self._nodes:
                return False
            self._nodes[node.node_id] = node
            self._emit_event("node_added", node.to_dict())
            return True
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the mesh."""
        with self._lock:
            return self.discovery.remove_node(node_id)
    
    def get_node(self, node_id: str) -> Optional[MeshNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)
    
    def list_nodes(self, state: MeshNodeState = None) -> List[MeshNode]:
        """List all nodes, optionally filtered by state."""
        with self._lock:
            nodes = list(self._nodes.values())
            if state:
                nodes = [n for n in nodes if n.state == state]
            return nodes
    
    # --- Edge Management ---
    
    def add_edge(
        self, 
        source_id: str, 
        target_id: str, 
        edge_type: EdgeType,
        provenance: Dict[str, Any] = None
    ) -> bool:
        """Add an edge between nodes."""
        with self._lock:
            if source_id not in self._nodes or target_id not in self._nodes:
                return False
            
            edge_key = edge_type.value
            
            if source_id not in self._edges:
                self._edges[source_id] = {}
            if edge_key not in self._edges[source_id]:
                self._edges[source_id][edge_key] = []
            if target_id not in self._edges[source_id][edge_key]:
                self._edges[source_id][edge_key].append(target_id)
            
            # Also add reverse for undirected edge types
            if edge_type in (EdgeType.TRUST, EdgeType.COLLABORATION, EdgeType.ORGANIZATION):
                if target_id not in self._edges:
                    self._edges[target_id] = {}
                if edge_key not in self._edges[target_id]:
                    self._edges[target_id][edge_key] = []
                if source_id not in self._edges[target_id][edge_key]:
                    self._edges[target_id][edge_key].append(source_id)
            
            return True
    
    def get_neighbors(self, node_id: str, edge_type: EdgeType = None) -> List[str]:
        """Get neighbor node IDs."""
        with self._lock:
            if node_id not in self._edges:
                return []
            
            if edge_type:
                return self._edges[node_id].get(edge_type.value, [])
            
            neighbors = []
            for targets in self._edges[node_id].values():
                neighbors.extend(targets)
            return list(set(neighbors))
    
    # --- Task Execution ---
    
    def execute_task(
        self,
        goal: str,
        required_capabilities: List[str] = None,
        policy: Dict[str, Any] = None,
        privacy_level: str = "internal",
        trust_requirements: Dict[TrustDimension, float] = None,
        latency_sla_ms: float = None,
        cost_budget: float = None,
        max_agents: int = 10,
        verification_required: bool = False,
        verification_quorum: int = 1,
        preferred_topology: TopologyType = None,
        collective_mode: CollectiveMode = CollectiveMode.ENSEMBLE,
    ) -> CollectiveResult:
        """Execute a task through the mesh."""
        
        # Create task
        task = MeshTask(
            goal=goal,
            required_capabilities=required_capabilities or [],
            policy=policy or {},
            privacy_level=privacy_level,
            trust_requirements=trust_requirements or {},
            latency_sla_ms=latency_sla_ms,
            cost_budget=cost_budget,
            max_agents=max_agents,
            verification_required=verification_required,
            verification_quorum=verification_quorum,
            preferred_topology=preferred_topology,
        )
        
        self._tasks[task.task_id] = task
        task.status = "routing"
        task.started_at = time.time()
        
        self._emit_event("task_created", task.to_dict())
        
        try:
            # Route task
            routing = self.router.route(task)
            task.status = "team_formation"
            
            # Form team
            team_result = self.team_engine.form_team(task, routing, preferred_topology)
            team = team_result.team
            self._teams[team.team_id] = team
            
            task.assigned_nodes = team.members
            task.status = "executing"
            
            self._emit_event("task_routed", {"task_id": task.task_id, "routing": routing.to_dict()})
            self._emit_event("team_formed", team_result.team.to_dict())
            
            # Execute collectively
            result = self.collective.execute_collective(task, team, collective_mode)
            
            task.status = "completed"
            task.completed_at = time.time()
            task.result = result
            
            # Dissolve team
            self.team_engine.dissolve_team(team)
            
            # Record metrics
            self._record_task_metrics(task, result)
            
            self._emit_event("task_completed", {
                "task_id": task.task_id,
                "success": result.confidence > 0.5,
                "confidence": result.confidence,
            })
            
            return result
            
        except Exception as e:
            task.status = "failed"
            task.completed_at = time.time()
            logger.error(f"Task {task.task_id} failed: {e}")
            self._emit_event("task_failed", {"task_id": task.task_id, "error": str(e)})
            raise
    
    def _record_task_metrics(self, task: MeshTask, result: CollectiveResult) -> None:
        """Record task metrics for optimization."""
        self.blackboard.put(
            f"task_result:{task.task_id}",
            {
                "task_id": task.task_id,
                "success": result.confidence > 0.5,
                "confidence": result.confidence,
                "latency_ms": (task.completed_at - task.started_at) * 1000 if task.completed_at and task.started_at else 0,
                "cost": task.metadata.get("cost", 0),
                "verified": result.verification.get("status") == "passed",
                "team_size": len(task.assigned_nodes),
                "topology": task.metadata.get("topology", ""),
            },
            source_agent="mesh",
            scope="mesh",
            tags=["task_result"],
        )
        
        # Record team performance
        if task.assigned_nodes:
            self.blackboard.put(
                f"team_performance:{task.task_id}",
                {
                    "task_id": task.task_id,
                    "team_size": len(task.assigned_nodes),
                    "success": result.confidence > 0.5,
                    "latency_ms": (task.completed_at - task.started_at) * 1000 if task.completed_at and task.started_at else 0,
                    "coordination_overhead": 0.1,  # Would calculate actual
                    "utilization": 0.5,  # Would calculate actual
                },
                source_agent="mesh",
                scope="mesh",
                tags=["team_performance"],
            )
    
    # --- Mesh Status ---
    
    def get_status(self) -> MeshStatus:
        """Get current mesh status."""
        with self._lock:
            active_nodes = len([n for n in self._nodes.values() 
                               if n.state in (MeshNodeState.AVAILABLE, MeshNodeState.BUSY)])
            
            active_tasks = len([t for t in self._tasks.values() if t.status == "executing"])
            completed_tasks = len([t for t in self._tasks.values() if t.status == "completed"])
            failed_tasks = len([t for t in self._tasks.values() if t.status == "failed"])
            
            open_incidents = len([
                i for i in self.incident._incidents.values()
                if i.status in (IncidentStatus.DETECTED, IncidentStatus.INVESTIGATING, IncidentStatus.CONTAINED)
            ])
            
            return MeshStatus(
                mesh_id=self.mesh_id,
                state=self._state,
                node_count=len(self._nodes),
                active_nodes=active_nodes,
                team_count=len(self._teams),
                active_tasks=active_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                incidents_open=open_incidents,
                last_optimization=self.optimization._last_loop,
                uptime_seconds=time.time() - self._start_time,
            )
    
    def get_topology(self) -> Dict[str, Any]:
        """Get current mesh topology."""
        with self._lock:
            return {
                "mesh_id": self.mesh_id,
                "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
                "edges": self._edges,
                "node_count": len(self._nodes),
                "edge_count": sum(len(t) for edges in self._edges.values() for t in edges.values()),
                "states": {s.value: len([n for n in self._nodes.values() if n.state == s]) for s in MeshNodeState},
                "timestamp": time.time(),
            }
    
    # --- Event System ---
    
    def on(self, event: str, callback: Callable) -> None:
        """Register event callback."""
        if event not in self._event_callbacks:
            self._event_callbacks[event] = []
        self._event_callbacks[event].append(callback)
    
    def off(self, event: str, callback: Callable) -> None:
        """Unregister event callback."""
        if event in self._event_callbacks:
            try:
                self._event_callbacks[event].remove(callback)
            except ValueError:
                pass
    
    def _emit_event(self, event: str, data: Dict[str, Any]) -> None:
        """Emit event to callbacks."""
        for callback in self._event_callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.debug(f"Event callback failed for {event}: {e}")
    
    # --- CLI / External Interface ---
    
    def execute_cli_command(self, command: str, args: List[str]) -> Dict[str, Any]:
        """Execute a CLI command."""
        
        if command == "status":
            return self.get_status().to_dict()
        
        elif command == "topology":
            return self.get_topology()
        
        elif command == "nodes":
            state = MeshNodeState(args[0]) if args else None
            return {"nodes": [n.to_dict() for n in self.list_nodes(state)]}
        
        elif command == "edges":
            return {"edges": self._edges}
        
        elif command == "tasks":
            return {"tasks": [t.to_dict() for t in self._tasks.values()]}
        
        elif command == "teams":
            return {"teams": [t.to_dict() for t in self._teams.values()]}
        
        elif command == "incidents":
            status = IncidentStatus(args[0]) if args else None
            return {"incidents": [i.to_dict() for i in self.incident.list_incidents(status=status)]}
        
        elif command == "optimize":
            result = self.optimization.run_optimization_loop()
            return {"optimization_loop": result.__dict__}
        
        elif command == "verify":
            # Would run verification on recent results
            return {"verification": "not_implemented"}
        
        elif command == "isolate":
            agent_id = args[0] if args else ""
            if agent_id:
                self.governance.quarantine_agent(agent_id, "CLI isolation", "cli")
                return {"isolated": agent_id}
            return {"error": "agent_id required"}
        
        elif command == "revoke":
            agent_id = args[0] if args else ""
            if agent_id:
                self.governance.quarantine_agent(agent_id, "CLI revocation", "cli")
                node = self._nodes.get(agent_id)
                if node:
                    node.update_state(MeshNodeState.REVOKED)
                return {"revoked": agent_id}
            return {"error": "agent_id required"}
        
        elif command == "benchmark":
            return self._run_benchmark(args)
        
        elif command == "experiments":
            return {"experiments": [e.to_dict() for e in self.optimization._experiments.values()]}
        
        return {"error": f"Unknown command: {command}"}
    
    def _run_benchmark(self, args: List[str]) -> Dict[str, Any]:
        """Run mesh benchmark."""
        # Simplified benchmark
        return {
            "benchmark": "mesh_throughput",
            "nodes": len(self._nodes),
            "tasks_completed": len([t for t in self._tasks.values() if t.status == "completed"]),
            "avg_confidence": sum(t.result.confidence for t in self._tasks.values() if t.result) / max(1, len([t for t in self._tasks.values() if t.result])),
        }


def create_global_agent_mesh(
    home: Path,
    organization_id: str = "default",
    mesh_id: str = "",
    config: Dict[str, Any] = None
) -> GlobalAgentMesh:
    """Factory function to create a GlobalAgentMesh."""
    return GlobalAgentMesh(home, organization_id, mesh_id, config)