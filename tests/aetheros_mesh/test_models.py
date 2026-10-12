"""Tests for aetheros_mesh models."""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path

from aetheros_mesh.models import (
    MeshNode, MeshNodeState, MeshEdge, EdgeType, 
    CollectiveResult, MeshTask, MeshTeam,
    TopologyType, CollectiveMode, TrustDimension,
    MeshConfig, create_mesh_node_from_agent_card
)
from aetheros_mesh.trust import MeshTrust, TrustSignal
from aetheros_mesh.blackboard import MeshBlackboard
from aetheros_mesh.router import MeshRouter
from aetheros_mesh.team import TeamFormationEngine
from aetheros_mesh.collective import CollectiveIntelligenceEngine
from aetheros_mesh.discovery import MeshDiscovery


class TestMeshNode:
    """Tests for MeshNode model."""
    
    def test_create_node(self):
        node = MeshNode(
            agent_id="test-agent",
            capabilities=["research", "coding"],
            protocols=["A2A/1.0"],
            endpoint="https://agent.example.com",
            location="local",
        )
        
        assert node.agent_id == "test-agent"
        assert "research" in node.capabilities
        assert node.state == MeshNodeState.DISCOVERED
        assert node.get_overall_trust() == 0.0
    
    def test_node_state_transitions(self):
        node = MeshNode(agent_id="test-agent")
        
        # Valid transitions
        assert node.update_state(MeshNodeState.VERIFYING)
        assert node.state == MeshNodeState.VERIFYING
        
        assert node.update_state(MeshNodeState.TRUSTED)
        assert node.state == MeshNodeState.TRUSTED
        
        assert node.update_state(MeshNodeState.AVAILABLE)
        assert node.state == MeshNodeState.AVAILABLE
        
        # Invalid transition (DISCOVERED -> AVAILABLE not allowed)
        node2 = MeshNode(agent_id="test-agent-2")
        assert not node2.update_state(MeshNodeState.AVAILABLE)
        assert node2.state == MeshNodeState.DISCOVERED
    
    def test_update_trust(self):
        node = MeshNode(agent_id="test-agent")
        
        node.update_trust(TrustDimension.IDENTITY, 0.8)
        node.update_trust(TrustDimension.SECURITY, 0.9)
        
        assert node.trust[TrustDimension.IDENTITY] == 0.8
        assert node.trust[TrustDimension.SECURITY] == 0.9
        
        # Clamping
        node.update_trust(TrustDimension.EXECUTION, 1.5)
        assert node.trust[TrustDimension.EXECUTION] == 1.0
        
        node.update_trust(TrustDimension.ECONOMIC, -0.5)
        assert node.trust[TrustDimension.ECONOMIC] == 0.0
    
    def test_is_available_for_task(self):
        node = MeshNode(
            agent_id="test-agent",
            capabilities=["research", "coding"],
        )
        
        node.update_state(MeshNodeState.AVAILABLE)
        assert node.is_available_for_task(["research"])
        assert not node.is_available_for_task(["unknown_cap"])
        
        node.update_state(MeshNodeState.SUSPENDED)
        assert not node.is_available_for_task(["research"])
    
    def test_serialization(self):
        node = MeshNode(
            agent_id="test-agent",
            capabilities=["research"],
            trust={TrustDimension.IDENTITY: 0.8},
        )
        
        data = node.to_dict()
        assert data["agent_id"] == "test-agent"
        assert "research" in data["capabilities"]
        assert data["trust"]["identity"] == 0.8
        assert data["state"] == "discovered"
        
        # Deserialize
        node2 = MeshNode.from_dict(data)
        assert node2.agent_id == "test-agent"
        assert node2.trust[TrustDimension.IDENTITY] == 0.8


class TestMeshEdge:
    """Tests for MeshEdge model."""
    
    def test_create_edge(self):
        edge = MeshEdge(
            source_node_id="node-1",
            target_node_id="node-2",
            edge_type=EdgeType.TRUST,
            provenance={"source": "verification"},
        )
        
        assert edge.source_node_id == "node-1"
        assert edge.target_node_id == "node-2"
        assert edge.edge_type == EdgeType.TRUST
        assert edge.active is True
    
    def test_expiry(self):
        import time
        edge = MeshEdge(
            source_node_id="node-1",
            target_node_id="node-2",
            edge_type=EdgeType.COMMUNICATION,
            expires_at=time.time() - 100,  # Expired
        )
        
        assert edge.is_expired()
        
        edge2 = MeshEdge(
            source_node_id="node-1",
            target_node_id="node-2",
            edge_type=EdgeType.COMMUNICATION,
            expires_at=0,  # No expiry
        )
        
        assert not edge2.is_expired()


class TestCollectiveResult:
    """Tests for CollectiveResult model."""
    
    def test_create_result(self):
        result = CollectiveResult(
            task_id="task-1",
            participants=["agent-1", "agent-2"],
            confidence=0.85,
            decision="Approved",
            rationale="Strong consensus",
        )
        
        assert result.task_id == "task-1"
        assert len(result.participants) == 2
        assert result.confidence == 0.85
    
    def test_serialization(self):
        result = CollectiveResult(
            task_id="task-1",
            participants=["agent-1"],
            confidence=0.9,
        )
        
        data = result.to_dict()
        assert data["task_id"] == "task-1"
        assert data["confidence"] == 0.9


class TestMeshTask:
    """Tests for MeshTask model."""
    
    def test_create_task(self):
        task = MeshTask(
            goal="Research AI agents",
            required_capabilities=["research", "analysis"],
            privacy_level="internal",
            max_agents=5,
        )
        
        assert task.goal == "Research AI agents"
        assert "research" in task.required_capabilities
        assert task.privacy_level == "internal"
        assert task.max_agents == 5
    
    def test_serialization(self):
        task = MeshTask(
            goal="Test task",
            required_capabilities=["coding"],
            preferred_topology=TopologyType.PARALLEL,
        )
        
        data = task.to_dict()
        assert data["goal"] == "Test task"
        assert data["preferred_topology"] == "parallel"
        assert "coding" in data["required_capabilities"]


class TestMeshTeam:
    """Tests for MeshTeam model."""
    
    def test_create_team(self):
        team = MeshTeam(
            task_id="task-1",
            members=["node-1", "node-2", "node-3"],
            roles={"node-1": "coordinator", "node-2": "worker", "node-3": "verifier"},
            topology=TopologyType.SPECIALIST_VERIFIER,
            coordinator_id="node-1",
        )
        
        assert team.task_id == "task-1"
        assert len(team.members) == 3
        assert team.roles["node-1"] == "coordinator"
        assert team.topology == TopologyType.SPECIALIST_VERIFIER
    
    def test_serialization(self):
        team = MeshTeam(
            task_id="task-1",
            members=["node-1"],
            topology=TopologyType.SEQUENTIAL,
        )
        
        data = team.to_dict()
        assert data["topology"] == "sequential"
        
        team2 = MeshTeam.from_dict(data)
        assert team2.topology == TopologyType.SEQUENTIAL


class TestMeshConfig:
    """Tests for MeshConfig."""
    
    def test_default_config(self):
        config = MeshConfig()
        
        assert config.mesh_id.startswith("mesh-")
        assert config.organization_id == "default"
        assert len(config.discovery_sources) == 8
        assert config.max_parallel_agents == 10
        assert config.enable_self_optimization is True


class TestCreateNodeFromAgentCard:
    """Tests for creating nodes from agent cards."""
    
    def test_create_from_card(self):
        card_data = {
            "name": "Research Agent",
            "url": "https://agent.example.com",
            "version": "1.0",
            "description": "A research agent",
            "skills": [
                {"id": "research", "name": "Research", "description": "Research capability"},
                {"id": "analysis", "name": "Analysis", "description": "Analysis capability"},
            ],
            "protocolVersion": "1.0",
        }
        
        node = create_mesh_node_from_agent_card(
            card_data,
            organization_id="test-org",
            endpoint="https://agent.example.com",
            location="remote",
        )
        
        assert node.organization_id == "test-org"
        assert node.location == "remote"
        assert "research" in node.capabilities
        assert "analysis" in node.capabilities
        assert node.endpoint == "https://agent.example.com"
        assert node.identity["name"] == "Research Agent"


class TestMeshTrust:
    """Tests for MeshTrust engine."""
    
    @pytest.fixture
    def trust_engine(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield MeshTrust(Path(tmpdir), "test-mesh")
    
    def test_record_signal(self, trust_engine):
        signal = trust_engine.record_signal(TrustSignal(
            node_id="node-1",
            dimension=TrustDimension.IDENTITY,
            source="verification",
            kind="identity_verified",
            value=0.8,
            confidence=0.9,
        ))
        
        assert signal.signal_id.startswith("sig-")
        assert signal.node_id == "node-1"
        assert signal.dimension == TrustDimension.IDENTITY
    
    def test_record_identity_verification(self, trust_engine):
        signal = trust_engine.record_identity_verification(
            "node-1", True, "tls+issuer", "evidence-123"
        )
        
        assert signal.dimension == TrustDimension.IDENTITY
        assert signal.value == 0.8
        assert signal.confidence == 0.9
    
    def test_record_execution_outcome(self, trust_engine):
        signals = trust_engine.record_execution_outcome(
            "node-1", True, "research", latency_ms=5000, cost_usd=0.01
        )
        
        assert len(signals) >= 1
        assert signals[0].dimension == TrustDimension.EXECUTION
        assert signals[0].value > 0  # Success
    
    def test_assess_dimension(self, trust_engine):
        # Add some signals
        trust_engine.record_signal(TrustSignal(
            node_id="node-1",
            dimension=TrustDimension.IDENTITY,
            source="verification",
            kind="identity_verified",
            value=0.8,
            confidence=0.9,
        ))
        
        assessment = trust_engine.assess_dimension("node-1", TrustDimension.IDENTITY)
        
        assert assessment["dimension"] == "identity"
        assert assessment["score"] > 0
        assert assessment["samples"] == 1
    
    def test_assess_node(self, trust_engine):
        # Add signals across dimensions
        for dim in TrustDimension:
            trust_engine.record_signal(TrustSignal(
                node_id="node-1",
                dimension=dim,
                source="verification",
                kind=f"{dim.value}_verified",
                value=0.5,
                confidence=0.8,
            ))
        
        assessment = trust_engine.assess_node("node-1")
        
        assert assessment.node_id == "node-1"
        assert len(assessment.dimensions) == len(TrustDimension)
        assert assessment.overall_score > 0
        assert assessment.get_level() in ("low", "medium", "high", "verified", "trusted")
    
    def test_detect_correlated_agents(self, trust_engine):
        # Add signals with same org for two agents
        for agent_id in ["node-1", "node-2"]:
            trust_engine.record_signal(TrustSignal(
                node_id=agent_id,
                dimension=TrustDimension.ORGANIZATION,
                source="organization",
                kind="org_attestation",
                value=0.7,
                confidence=0.8,
                provenance={"org_id": "shared-org"},
            ))
        
        correlations = trust_engine.detect_correlated_agents(["node-1", "node-2"])
        
        assert len(correlations) > 0
        assert correlations[0]["type"] == "shared_organization"
        assert set(correlations[0]["nodes"]) == {"node-1", "node-2"}


class TestMeshBlackboard:
    """Tests for MeshBlackboard."""
    
    @pytest.fixture
    def blackboard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield MeshBlackboard(Path(tmpdir), "test-mesh")
    
    def test_put_get(self, blackboard):
        blackboard.put("test_key", "test_value", source_agent="agent-1")
        
        value = blackboard.get("test_key", agent_id="agent-1")
        assert value == "test_value"
    
    def test_versioning(self, blackboard):
        blackboard.put("key", "v1", source_agent="agent-1")
        v1 = blackboard.get_version("key")
        
        blackboard.put("key", "v2", source_agent="agent-1", expected_version=v1)
        v2 = blackboard.get_version("key")
        
        assert v2 == v1 + 1
        
        # Try with wrong version - should fail
        with pytest.raises(Exception):
            blackboard.put("key", "v3", source_agent="agent-1", expected_version=v1)
    
    def test_compare_and_swap(self, blackboard):
        blackboard.put("counter", 0, source_agent="agent-1")
        
        # Successful CAS
        result = blackboard.compare_and_swap("counter", 0, 1, source_agent="agent-1")
        assert result is True
        assert blackboard.get("counter", agent_id="agent-1") == 1
        
        # Failed CAS
        result = blackboard.compare_and_swap("counter", 0, 2, source_agent="agent-1")
        assert result is False
        assert blackboard.get("counter", agent_id="agent-1") == 1
    
    def test_increment(self, blackboard):
        blackboard.put("counter", 5, source_agent="agent-1")
        
        new_val = blackboard.increment("counter", 3, source_agent="agent-1")
        assert new_val == 8
        assert blackboard.get("counter", agent_id="agent-1") == 8
    
    def test_append_to_list(self, blackboard):
        blackboard.put("items", ["a"], source_agent="agent-1")
        
        result = blackboard.append_to_list("items", "b", source_agent="agent-1")
        assert result is True
        assert blackboard.get("items", agent_id="agent-1") == ["a", "b"]
    
    def test_authorization(self, blackboard):
        blackboard.put(
            "secret", "value", 
            source_agent="agent-1",
            authorization=["agent-1", "admin"]
        )
        
        # Authorized agent can read
        assert blackboard.get("secret", agent_id="agent-1") == "value"
        assert blackboard.get("secret", agent_id="admin") == "value"
        
        # Unauthorized agent cannot read
        with pytest.raises(Exception):
            blackboard.get("secret", agent_id="agent-2")
    
    def test_scope_filtering(self, blackboard):
        blackboard.put("task_key", "task_value", source_agent="agent-1", scope="task")
        blackboard.put("mesh_key", "mesh_value", source_agent="agent-1", scope="mesh")
        
        # Query by scope
        task_view = blackboard.query(scope="task", agent_id="agent-1")
        mesh_view = blackboard.query(scope="mesh", agent_id="agent-1")
        
        assert "task_key" in task_view
        assert "mesh_key" not in task_view
        assert "mesh_key" in mesh_view
        assert "task_key" not in mesh_view
    
    def test_subscription(self, blackboard):
        events = []
        
        def callback(key, entry):
            events.append((key, entry.value))
        
        sub_id = blackboard.subscribe("test_*", callback)
        
        blackboard.put("test_key", "value1", source_agent="agent-1")
        blackboard.put("other_key", "value2", source_agent="agent-1")
        blackboard.put("test_another", "value3", source_agent="agent-1")
        
        assert len(events) == 2
        assert events[0] == ("test_key", "value1")
        assert events[1] == ("test_another", "value3")
        
        blackboard.unsubscribe("test_*", callback)


class TestMeshRouter:
    """Tests for MeshRouter."""
    
    @pytest.fixture
    def setup_router(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trust = MeshTrust(Path(tmpdir), "test-mesh")
            nodes = {
                "node-1": MeshNode(
                    node_id="node-1", agent_id="agent-1",
                    capabilities=["research", "coding"],
                    trust={d: 0.8 for d in TrustDimension},
                    state=MeshNodeState.AVAILABLE,
                    performance={"avg_latency_ms": 1000, "avg_cost_per_task": 0.01},
                ),
                "node-2": MeshNode(
                    node_id="node-2", agent_id="agent-2",
                    capabilities=["research", "analysis"],
                    trust={d: 0.6 for d in TrustDimension},
                    state=MeshNodeState.AVAILABLE,
                    performance={"avg_latency_ms": 2000, "avg_cost_per_task": 0.02},
                ),
                "node-3": MeshNode(
                    node_id="node-3", agent_id="agent-3",
                    capabilities=["coding"],
                    trust={d: 0.9 for d in TrustDimension},
                    state=MeshNodeState.BUSY,
                    performance={"avg_latency_ms": 500, "avg_cost_per_task": 0.05},
                ),
            }
            router = MeshRouter(trust, nodes)
            yield router, nodes
    
    def test_route_simple_task(self, setup_router):
        router, nodes = setup_router
        
        task = MeshTask(
            goal="Research task",
            required_capabilities=["research"],
            max_agents=2,
        )
        
        decision = router.route(task)
        
        assert decision.task_id == task.task_id
        assert len(decision.selected_nodes) > 0
        assert decision.topology in TopologyType
        assert decision.confidence >= 0
    
    def test_route_with_trust_requirements(self, setup_router):
        router, nodes = setup_router
        
        task = MeshTask(
            goal="High trust task",
            required_capabilities=["research"],
            trust_requirements={TrustDimension.SECURITY: 0.7},
        )
        
        decision = router.route(task)
        
        # node-2 has trust 0.6 < 0.7, should be excluded
        selected = decision.selected_nodes
        assert "node-2" not in selected or len(selected) == 0
    
    def test_route_with_sla(self, setup_router):
        router, nodes = setup_router
        
        task = MeshTask(
            goal="Fast task",
            required_capabilities=["coding"],
            latency_sla_ms=1500,  # node-2 has 2000ms, should be excluded
        )
        
        decision = router.route(task)
        
        # node-2 should be rejected due to latency
        rejected = [c for c in decision.candidates if c.rejection_reason]
        latency_rejected = [c for c in rejected if "latency" in c.rejection_reason]
        assert len(latency_rejected) > 0


class TestTeamFormationEngine:
    """Tests for TeamFormationEngine."""
    
    @pytest.fixture
    def setup_team_engine(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trust = MeshTrust(Path(tmpdir), "test-mesh")
            nodes = {
                "node-1": MeshNode(
                    node_id="node-1", agent_id="agent-1",
                    capabilities=["research", "coding"],
                    trust={d: 0.8 for d in TrustDimension},
                    state=MeshNodeState.AVAILABLE,
                ),
                "node-2": MeshNode(
                    node_id="node-2", agent_id="agent-2",
                    capabilities=["research", "verification"],
                    trust={d: 0.7 for d in TrustDimension},
                    state=MeshNodeState.AVAILABLE,
                ),
                "node-3": MeshNode(
                    node_id="node-3", agent_id="agent-3",
                    capabilities=["coding", "verification"],
                    trust={d: 0.9 for d in TrustDimension},
                    state=MeshNodeState.AVAILABLE,
                ),
            }
            router = MeshRouter(trust, nodes)
            team_engine = TeamFormationEngine(trust, router, nodes)
            yield team_engine, nodes, router
    
    def test_form_team(self, setup_team_engine):
        team_engine, nodes, router = setup_team_engine
        
        task = MeshTask(
            goal="Research with verification",
            required_capabilities=["research"],
            verification_required=True,
        )
        
        routing = router.route(task)
        result = team_engine.form_team(task, routing)
        
        assert result.team.task_id == task.task_id
        assert len(result.team.members) > 0
        assert result.team.topology in TopologyType
        assert result.confidence >= 0
    
    def test_form_specialist_verifier_team(self, setup_team_engine):
        team_engine, nodes, router = setup_team_engine
        
        task = MeshTask(
            goal="Critical research",
            required_capabilities=["research"],
            verification_required=True,
            max_agents=3,
        )
        
        # Force specialist_verifier topology
        result = team_engine.form_team(task, preferred_topology=TopologyType.SPECIALIST_VERIFIER)
        
        assert result.team.topology == TopologyType.SPECIALIST_VERIFIER
        roles = set(result.team.roles.values())
        assert "specialist" in roles or "verifier" in roles


class TestCollectiveIntelligenceEngine:
    """Tests for CollectiveIntelligenceEngine."""
    
    @pytest.fixture
    def setup_collective(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trust = MeshTrust(Path(tmpdir), "test-mesh")
            blackboard = MeshBlackboard(Path(tmpdir), "test-mesh")
            collective = CollectiveIntelligenceEngine(trust, blackboard)
            yield collective, trust, blackboard
    
    def test_execute_collective(self, setup_collective):
        collective, trust, blackboard = setup_collective
        
        # Add trust for nodes
        for node_id in ["node-1", "node-2"]:
            for dim in TrustDimension:
                trust.record_signal(TrustSignal(
                    node_id=node_id,
                    dimension=dim,
                    source="verification",
                    kind=f"{dim.value}_verified",
                    value=0.7,
                    confidence=0.8,
                ))
        
        task = MeshTask(
            task_id="test-task",
            goal="Test collective task",
            required_capabilities=["research"],
        )
        
        team = MeshTeam(
            team_id="test-team",
            task_id="test-task",
            members=["node-1", "node-2"],
            roles={"node-1": "worker", "node-2": "verifier"},
            topology=TopologyType.SPECIALIST_VERIFIER,
        )
        
        # Mock executor
        def mock_executor(task, node, context):
            from aetheros_mesh.collective import AgentOutput
            return AgentOutput(
                agent_id=node.agent_id,
                node_id=node.node_id,
                role=context.get("role", "worker"),
                output={"summary": f"Result from {node.agent_id}", "finding": "test"},
                evidence=[{"source": "test", "data": "evidence"}],
                confidence=0.8,
            )
        
        collective.executor = mock_executor
        collective.nodes = {
            "node-1": MeshNode(node_id="node-1", agent_id="agent-1"),
            "node-2": MeshNode(node_id="node-2", agent_id="agent-2"),
        }
        
        result = collective.execute_collective(task, team, CollectiveMode.ENSEMBLE)
        
        assert result.task_id == "test-task"
        assert len(result.participants) == 2
        assert result.confidence >= 0


class TestMeshDiscovery:
    """Tests for MeshDiscovery."""
    
    @pytest.fixture
    def discovery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield MeshDiscovery("test-mesh", Path(tmpdir), "test-org")
    
    def test_add_manual_card(self, discovery):
        card_data = {
            "name": "Test Agent",
            "url": "https://test.example.com",
            "version": "1.0",
            "skills": [{"id": "test", "name": "Test"}],
        }
        
        result = discovery.add_direct_card(card_data, "https://test.example.com")
        
        assert result.node is not None
        assert "test" in result.node.capabilities
        assert result.node.organization_id == "test-org"
    
    def test_get_nodes_by_capability(self, discovery):
        card_data = {
            "name": "Agent 1",
            "url": "https://a1.example.com",
            "version": "1.0",
            "skills": [{"id": "research", "name": "Research"}],
        }
        discovery.add_direct_card(card_data)
        
        card_data2 = {
            "name": "Agent 2",
            "url": "https://a2.example.com",
            "version": "1.0",
            "skills": [{"id": "coding", "name": "Coding"}],
        }
        discovery.add_direct_card(card_data2)
        
        research_nodes = discovery.get_nodes_by_capability("research")
        coding_nodes = discovery.get_nodes_by_capability("coding")
        
        assert len(research_nodes) == 1
        assert len(coding_nodes) == 1
        assert research_nodes[0].capabilities == ["research"]
        assert coding_nodes[0].capabilities == ["coding"]
    
    def test_suspend_revoke(self, discovery):
        card_data = {
            "name": "Test Agent",
            "url": "https://test.example.com",
            "version": "1.0",
            "skills": [{"id": "test", "name": "Test"}],
        }
        result = discovery.add_direct_card(card_data)
        node_id = result.node.node_id
        
        # Suspend
        assert discovery.suspend_node(node_id, "Testing")
        node = discovery.get_node(node_id)
        assert node.state == MeshNodeState.SUSPENDED
        
        # Revoke
        assert discovery.revoke_node(node_id, "Testing")
        node = discovery.get_node(node_id)
        assert node.state == MeshNodeState.REVOKED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])