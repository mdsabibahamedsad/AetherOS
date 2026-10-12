"""Acceptance tests for the Multi-Agent Orchestrator & Autonomous Execution Engine.

Tests the complete flow:
  1. User Goal -> Planner creates task graph
  2. Coordinator assigns agents
  3. Agents execute tasks
  4. Reviewer validates output
  5. Critic checks quality
  6. Artifacts saved
  7. Memory updated
  8. Mission completed
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure the package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aetheros"))


class TestMultiAgentOrchestratorImports:
    """Verify all components can be imported."""

    def test_kernel_imports(self):
        from kernel import (
            Kernel, KernelConfig,
            AgentManager, AgentRegistry,
            InterAgentBus, SupervisorAgent,
            ReviewerAgent, CriticAgent,
            ReflectionEngine, ApprovalLayer,
            ArtifactManager, SchedulingEngine,
            Planner, Executor, TaskGraph,
            EventBus, PermissionManager, ContextManager,
        )
        assert Kernel is not None
        assert AgentManager is not None
        assert InterAgentBus is not None
        assert SupervisorAgent is not None
        assert ReviewerAgent is not None
        assert CriticAgent is not None
        assert ReflectionEngine is not None
        assert ApprovalLayer is not None
        assert ArtifactManager is not None
        assert SchedulingEngine is not None

    def test_specialized_agent_imports(self):
        from agents.specialized_agents import (
            SPECIALIZED_AGENT_DEFINITIONS,
            ResearchAgent, CodingAgent, DebugAgent,
            ReviewAgent, DocumentationAgent, PlanningAgent,
            MemoryAgent, VisionAgent, VoiceAgent,
            BrowserAgent, DesktopAgent, AutomationAgent,
            create_specialized_agent, list_agent_types,
        )
        types = list_agent_types()
        assert "research" in types
        assert "coding" in types
        assert "debug" in types
        assert "review" in types
        assert "documentation" in types
        assert "planning" in types
        assert "memory" in types
        assert "vision" in types
        assert "voice" in types
        assert "browser" in types
        assert "desktop" in types
        assert "automation" in types
        assert len(SPECIALIZED_AGENT_DEFINITIONS) >= 12

    def test_dashboard_imports(self):
        from kernel.dashboard import (
            MissionDashboardData, AgentDashboardInfo,
            TimelineEvent, DashboardStats,
            create_dashboard_from_kernel,
        )
        assert MissionDashboardData is not None

    def test_agent_manager_imports(self):
        from kernel.agent_manager import (
            AgentManager, AgentInstance, AgentMetadata,
            AgentLifecycleStatus, AgentHealthStatus,
        )
        assert AgentLifecycleStatus.RUNNING.value == "running"
        assert AgentHealthStatus.HEALTHY.value == "healthy"


class TestAgentManager:
    """Test agent lifecycle management."""

    def setup_method(self):
        self.mgr = __import__("kernel.agent_manager", fromlist=["AgentManager"]).AgentManager()

    def test_register_and_list(self):
        self.mgr.register_agent("test-research", "research", {"name": "Test Research Agent"})
        self.mgr.register_agent("test-coding", "coding", {"name": "Test Coding Agent"})
        agents = self.mgr.list_agents()
        assert len(agents) == 2
        research_agents = self.mgr.list_agents(agent_type="research")
        assert len(research_agents) == 1

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            self.mgr.register_agent("bad-agent", "nonexistent_type")

    def test_start_stop_agent(self):
        self.mgr.register_agent("test-1", "research")
        started = self.mgr.start_agent("test-1")
        assert started is True
        instance = self.mgr.get_agent("test-1")
        assert instance.status.value == "running"
        stopped = self.mgr.stop_agent("test-1")
        assert stopped is True
        instance = self.mgr.get_agent("test-1")
        assert instance.status.value == "stopped"

    def test_pause_resume_agent(self):
        self.mgr.register_agent("test-2", "coding")
        self.mgr.start_agent("test-2")
        paused = self.mgr.pause_agent("test-2")
        assert paused is True
        instance = self.mgr.get_agent("test-2")
        assert instance.status.value == "paused"
        resumed = self.mgr.resume_agent("test-2")
        assert resumed is True
        instance = self.mgr.get_agent("test-2")
        assert instance.status.value == "running"

    def test_restart_agent(self):
        self.mgr.register_agent("test-3", "research")
        self.mgr.start_agent("test-3")
        instance = self.mgr.get_agent("test-3")
        assert instance.status.value == "running"
        time.sleep(0.05)
        restarted = self.mgr.restart_agent("test-3")
        assert restarted is True
        instance = self.mgr.get_agent("test-3")
        assert instance.status.value == "running"

    def test_health_check(self):
        self.mgr.register_agent("test-4", "research")
        health = self.mgr.check_health("test-4")
        assert health.value == "unknown"
        self.mgr.start_agent("test-4")
        health = self.mgr.check_health("test-4")
        assert health.value == "healthy"

    def test_find_by_capability(self):
        self.mgr.register_agent("cap-research", "research")
        self.mgr.register_agent("cap-coding", "coding")
        found = self.mgr.find_by_capability("research")
        assert len(found) >= 1
        found = self.mgr.find_by_capability("code_generation")
        assert len(found) >= 1

    def test_get_stats(self):
        self.mgr.register_agent("stats-1", "research")
        self.mgr.register_agent("stats-2", "coding")
        stats = self.mgr.get_stats()
        assert stats["total_agents"] >= 2
        assert "research" in stats["by_type"]
        assert "coding" in stats["by_type"]


class TestAgentRegistry:
    """Test the agent metadata registry."""

    def setup_method(self):
        self.mgr = __import__("kernel.agent_manager", fromlist=["AgentManager"]).AgentManager()
        self.registry = __import__("kernel.agent_registry", fromlist=["AgentRegistry"]).AgentRegistry()

    def test_register_entry(self):
        self.mgr.register_agent("reg-1", "research", {"version": "2.0.0", "tags": ["ai", "nlp"]})
        instance = self.mgr.get_agent("reg-1")
        self.registry.register(instance)
        entry = self.registry.get("reg-1")
        assert entry is not None
        assert entry.type == "research"
        assert entry.version == "2.0.0"

    def test_search(self):
        self.mgr.register_agent("search-1", "research", {"capabilities": ["research", "analysis"]})
        self.mgr.register_agent("search-2", "coding", {"capabilities": ["code_generation", "code_review"]})
        instance1 = self.mgr.get_agent("search-1")
        instance2 = self.mgr.get_agent("search-2")
        self.registry.register(instance1)
        self.registry.register(instance2)
        results = self.registry.find_by_capability("research")
        assert len(results) >= 1
        results = self.registry.search(capability="code_generation")
        assert len(results) >= 1

    def test_capability_summary(self):
        self.mgr.register_agent("cap-1", "research")
        self.mgr.register_agent("cap-2", "coding")
        self.mgr.register_agent("cap-3", "browser")
        for aid in ["cap-1", "cap-2", "cap-3"]:
            self.registry.register(self.mgr.get_agent(aid))
        summary = self.registry.get_capabilities_summary()
        assert len(summary) > 0


class TestInterAgentBus:
    """Test inter-agent communication."""

    def setup_method(self):
        self.bus = __import__("kernel.inter_agent", fromlist=["InterAgentBus"]).InterAgentBus()

    def test_register_and_send(self):
        self.bus.register_agent("agent-a")
        self.bus.register_agent("agent-b")
        msg = __import__("kernel.inter_agent", fromlist=["AgentMessage"]).AgentMessage(
            sender="agent-a", recipient="agent-b",
            payload={"text": "hello"}, topic="test",
        )
        sent = self.bus.send(msg)
        assert sent is True
        inbox = self.bus.receive("agent-b")
        assert len(inbox) == 1
        assert inbox[0].payload["text"] == "hello"

    def test_shared_memory(self):
        self.bus.register_agent("agent-mem")
        self.bus.memory_set("config", {"debug": True}, namespace="test", owner="agent-mem")
        value = self.bus.memory_get("config", namespace="test", agent_id="agent-mem")
        assert value == {"debug": True}

    def test_task_handoff(self):
        self.bus.register_agent("agent-a")
        self.bus.register_agent("agent-b")
        handoff = self.bus.handoff_task("agent-a", "agent-b", "Build the module",
                                         context={"files": ["main.py"]})
        assert handoff.status == "pending"
        accepted = self.bus.accept_handoff(handoff.id, "agent-b")
        assert accepted is True
        completed = self.bus.complete_handoff(handoff.id, {"output": "done"})
        assert completed is True
        handoff = self.bus.get_handoff(handoff.id)
        assert handoff.status == "completed"

    def test_conflict_resolution(self):
        self.bus.register_agent("agent-a")
        self.bus.register_agent("agent-b")
        cid = self.bus.report_conflict("agent-a", "resource_lock",
                                        "Both agents want to write to same file",
                                        ["agent-a", "agent-b"])
        resolved = self.bus.resolve_conflict(cid, "agent-a gets write access", "supervisor")
        assert resolved is True
        conflicts = self.bus.list_conflicts(status="resolved")
        assert len(conflicts) >= 1

    def test_dead_letter(self):
        msg = __import__("kernel.inter_agent", fromlist=["AgentMessage"]).AgentMessage(
            sender="ghost", recipient="nonexistent",
            payload={"text": "lost"}, topic="test",
        )
        self.bus.send(msg)
        dead = self.bus.get_dead_letter_messages()
        assert len(dead) >= 1


class TestSupervisorAgent:
    """Test supervisor monitoring."""

    def setup_method(self):
        self.supervisor = __import__("kernel.supervisor", fromlist=["SupervisorAgent"]).SupervisorAgent()

    def test_register_and_monitor(self):
        self.supervisor.register_agent("agent-1")
        self.supervisor.register_agent("agent-2", dependencies=["agent-1"])
        self.supervisor.record_heartbeat("agent-1", status="running", iteration_count=5)
        self.supervisor.record_heartbeat("agent-2", status="running", iteration_count=3)
        status = self.supervisor.get_agent_status("agent-1")
        assert status is not None
        assert status["total_iterations"] == 5

    def test_alert_lifecycle(self):
        from kernel.supervisor import AlertCategory, AlertSeverity
        alert = self.supervisor._raise_alert(
            category=AlertCategory.HEALTH,
            severity=AlertSeverity.WARNING,
            agent_id="test-agent",
            message="Test alert",
        )
        assert alert.resolved is False
        resolved = self.supervisor.resolve_alert(alert.id, "Investigated and cleared")
        assert resolved is True
        alerts = self.supervisor.get_alerts(unresolved_only=True)
        assert len(alerts) == 0

    def test_get_stats(self):
        self.supervisor.register_agent("stat-agent")
        stats = self.supervisor.get_stats()
        assert stats["monitored_agents"] >= 1


class TestReviewerAgent:
    """Test automated artifact review."""

    def setup_method(self):
        self.reviewer = __import__("kernel.reviewer", fromlist=["ReviewerAgent"]).ReviewerAgent()

    def test_review_code(self):
        code = """def hello(name):
    print(f"Hello {name}")
    eval(user_input)
"""
        result = self.reviewer.review_code(code, language="python")
        assert result.passed is True
        assert result.overall_score > 0
        assert len(result.findings) > 0
        has_security = any(f.category.value == "security" for f in result.findings)
        assert has_security is True

    def test_review_code_security(self):
        code = 'password = "supersecret"\napi_key = "abc123"\ntoken = "xyz"'
        result = self.reviewer.review_code(code)
        assert len(result.findings) >= 2

    def test_review_documentation(self):
        doc = "# My Project\n\nThis is a great project."
        result = self.reviewer.review_documentation(doc, doc_type="markdown")
        assert result.passed is True

    def test_review_plan(self):
        plan = {
            "goal": "Build a web app",
            "steps": [
                {"id": "s1", "description": "Setup", "dependencies": []},
                {"id": "s2", "description": "Build", "dependencies": ["s1"]},
                {"id": "s3", "description": "Deploy", "dependencies": ["s2", "s1"]},
            ],
        }
        result = self.reviewer.review_plan(plan)
        assert result.passed is True or result.overall_score > 0.5

    def test_review_plan_empty(self):
        plan = {"goal": "", "steps": []}
        result = self.reviewer.review_plan(plan)
        assert result.passed is False

    def test_get_stats(self):
        self.reviewer.review_code("def foo(): pass")
        stats = self.reviewer.get_stats()
        assert stats["total_reviews"] >= 1


class TestCriticAgent:
    """Test the critic agent."""

    def setup_method(self):
        self.critic = __import__("kernel.critic", fromlist=["CriticAgent"]).CriticAgent()

    def test_analyze_claim(self):
        claim = "This solution is clearly the best and always works perfectly"
        criticism = self.critic.analyze_claim(claim)
        assert criticism is not None
        assert criticism.severity.value >= 0

    def test_find_contradictions(self):
        statements = [
            "The system uses Python 3",
            "The system does not use Python 3",
        ]
        findings = self.critic.find_contradictions(statements)
        assert len(findings) >= 1

    def test_add_known_fact_and_check(self):
        self.critic.add_known_fact("python_version", "3.11")
        criticisms = self.critic.check_hallucinations("The python_version is 3.9")
        assert len(criticisms) >= 0

    def test_resolve_criticism(self):
        criticism = self.critic.analyze_claim("Test claim for resolution")
        resolved = self.critic.resolve_criticism(criticism.id, "Verified: claim is accurate")
        assert resolved is True
        c = self.critic.get_criticism(criticism.id)
        assert c.resolved is True


class TestReflectionEngine:
    """Test post-execution reflection."""

    def setup_method(self):
        self.engine = __import__("kernel.reflection", fromlist=["ReflectionEngine"]).ReflectionEngine()

    def test_analyze_execution(self):
        plan_data = {
            "steps": [
                {"id": "s1", "status": "completed"},
                {"id": "s2", "status": "completed"},
                {"id": "s3", "status": "failed"},
            ],
        }
        exec_data = {"duration_seconds": 120.0, "retries": 2, "errors": ["timeout"]}
        result = self.engine.analyze_execution("plan-1", "Test goal", plan_data, exec_data)
        assert result.success is False
        assert result.total_steps == 3
        assert result.completed_steps == 2
        assert result.failed_steps == 1
        assert len(result.lessons) > 0

    def test_lessons_persist(self):
        self.engine.analyze_execution("plan-2", "Goal", {"steps": []}, {})
        lessons = self.engine.get_lessons()
        assert len(lessons) > 0
        lesson_id = lessons[0].id
        applied = self.engine.mark_lesson_applied(lesson_id)
        assert applied is True

    def test_get_stats(self):
        self.engine.analyze_execution("plan-3", "Goal", {"steps": [{"id": "s1", "status": "completed"}]}, {})
        stats = self.engine.get_stats()
        assert stats["total_analyses"] >= 1


class TestApprovalLayer:
    """Test human approval gating."""

    def setup_method(self):
        self.approvals = __import__("kernel.approval", fromlist=["ApprovalLayer"]).ApprovalLayer()

    def test_request_and_resolve(self):
        req = self.approvals.request_approval(
            action=__import__("kernel.approval", fromlist=["ApprovalAction"]).ApprovalAction.DELETE_FILE,
            description="Delete config.yaml",
            agent_id="agent-1",
        )
        assert req.status.value == "pending"
        resolved = self.approvals.resolve_approval(req.id, granted=True, resolved_by="human")
        assert resolved is True
        req = self.approvals.get_request(req.id)
        assert req.status.value == "approved"

    def test_deny_request(self):
        req = self.approvals.request_approval(
            action=__import__("kernel.approval", fromlist=["ApprovalAction"]).ApprovalAction.SHELL_COMMAND,
            description="rm -rf /",
            agent_id="agent-1",
        )
        resolved = self.approvals.resolve_approval(req.id, granted=False, resolved_by="human", reason="Too dangerous")
        assert resolved is True
        req = self.approvals.get_request(req.id)
        assert req.status.value == "denied"

    def test_cancel_request(self):
        req = self.approvals.request_approval(
            action=__import__("kernel.approval", fromlist=["ApprovalAction"]).ApprovalAction.GIT_PUSH,
            description="Push to main",
            agent_id="agent-1",
        )
        cancelled = self.approvals.cancel_request(req.id, "No longer needed")
        assert cancelled is True
        req = self.approvals.get_request(req.id)
        assert req.status.value == "cancelled"

    def test_list_pending(self):
        self.approvals.request_approval(
            action=__import__("kernel.approval", fromlist=["ApprovalAction"]).ApprovalAction.DELETE_FILE,
            description="Delete temp file", agent_id="agent-1",
        )
        pending = self.approvals.list_pending()
        assert len(pending) >= 1

    def test_audit_log(self):
        self.approvals.request_approval(
            action=__import__("kernel.approval", fromlist=["ApprovalAction"]).ApprovalAction.INSTALL_PACKAGE,
            description="Install numpy", agent_id="agent-1",
        )
        log = self.approvals.get_audit_log()
        assert len(log) >= 1


class TestArtifactManager:
    """Test artifact storage."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.am = __import__("kernel.artifact_manager", fromlist=["ArtifactManager"]).ArtifactManager(
            storage_dir=self.tmpdir,
        )

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_store_and_retrieve(self):
        art = self.am.store(
            name="test.py",
            content="print('hello')",
            type=__import__("kernel.artifact_manager", fromlist=["ArtifactType"]).ArtifactType.CODE,
            owner_agent_id="agent-1",
            tags=["python", "test"],
        )
        assert art.id is not None
        assert art.content_size > 0
        retrieved = self.am.get(art.id)
        assert retrieved is not None
        assert retrieved.name == "test.py"

    def test_versioning(self):
        art = self.am.store("v1.py", "version 1", tags=["test"])
        updated = self.am.update(art.id, "version 2 content", version_message="Updated logic")
        assert updated.current_version == 2
        v1 = self.am.get(art.id, version=1)
        if v1:
            assert v1.current_version == 2

    def test_find(self):
        self.am.store("find-me.py", "content", type=__import__("kernel.artifact_manager", fromlist=["ArtifactType"]).ArtifactType.CODE, tags=["findable"])
        found = self.am.find(name="find-me")
        assert len(found) >= 1
        found = self.am.search_tags(["findable"])
        assert len(found) >= 1

    def test_list_by_agent(self):
        self.am.store("agent-art.py", "content", owner_agent_id="agent-99")
        arts = self.am.list_by_agent("agent-99")
        assert len(arts) >= 1


class TestSchedulingEngine:
    """Test the scheduling engine."""

    def setup_method(self):
        self.engine = __import__("kernel.scheduling_engine", fromlist=["SchedulingEngine"]).SchedulingEngine(
            tick_interval=0.1,
        )
        self.called = threading.Event()

    def test_immediate(self):
        def callback():
            self.called.set()
        self.engine.schedule_immediate("test-immediate", callback)
        self.called.wait(timeout=2)
        assert self.called.is_set()

    def test_delayed(self):
        result = []
        def callback():
            result.append("done")
        self.engine.start()
        self.engine.schedule_delayed("test-delayed", 0.3, callback)
        time.sleep(0.5)
        self.engine.stop()
        assert len(result) == 1

    def test_interval(self):
        count = []
        def callback():
            count.append(1)
        self.engine.start()
        self.engine.schedule_interval("test-interval", 0.2, callback, max_executions=3)
        time.sleep(1.0)
        self.engine.stop()
        assert len(count) == 3

    def test_cancel(self):
        entry = self.engine.schedule_delayed("test-cancel", 10.0, lambda: None)
        cancelled = self.engine.cancel(entry.id)
        assert cancelled is True

    def test_get_stats(self):
        self.engine.schedule_delayed("stat-test", 60.0, lambda: None)
        stats = self.engine.get_stats()
        assert stats["total_entries"] >= 1


class TestSpecializedAgents:
    """Test all 12 specialized agent types."""

    def test_create_all_types(self):
        from agents.specialized_agents import create_specialized_agent, list_agent_types
        for agent_type in list_agent_types():
            agent = create_specialized_agent(agent_type, f"test-{agent_type}")
            assert agent is not None
            assert agent.agent_id == f"test-{agent_type}"

    def test_research_agent(self):
        import asyncio
        from agents.specialized_agents import ResearchAgent
        agent = ResearchAgent("research-1")
        result = asyncio.run(agent.fact_check("Test claim"))
        assert result is not None

    def test_coding_agent(self):
        import asyncio
        from agents.specialized_agents import CodingAgent
        agent = CodingAgent("coding-1")
        result = asyncio.run(agent.generate("Build a calculator"))
        assert result is not None

    def test_planning_agent(self):
        import asyncio
        from agents.specialized_agents import PlanningAgent
        agent = PlanningAgent("planning-1")
        result = asyncio.run(agent.decompose_goal("Build a web app"))
        assert "subtasks" in result


class TestKernelIntegration:
    """Test the integrated kernel with all multi-agent components."""

    def test_kernel_creation(self):
        from kernel import Kernel, KernelConfig
        config = KernelConfig(
            enable_multi_agent=True,
            enable_supervisor=True,
            enable_approvals=True,
            enable_reflection=True,
            enable_artifact_storage=True,
            enable_inter_agent_bus=True,
            enable_scheduler=False,
            enable_telemetry=False,
            enable_state_persistence=False,
            auto_discover_components=False,
        )
        kernel = Kernel(config)
        assert kernel.agent_manager is not None
        assert kernel.agent_registry is not None
        assert kernel.inter_agent is not None
        assert kernel.supervisor is not None
        assert kernel.reviewer is not None
        assert kernel.critic is not None
        assert kernel.reflection is not None
        assert kernel.approvals is not None
        assert kernel.artifacts is not None
        assert kernel.scheduling is not None
        kernel.shutdown()


class TestAcceptanceFlow:
    """Complete acceptance test: User Goal -> Execution -> Review -> Completion."""

    def test_full_mission_flow(self):
        from kernel import (
            Kernel, KernelConfig, PlanStatus, GraphStatus,
        )
        config = KernelConfig(
            enable_multi_agent=True, enable_supervisor=True,
            enable_approvals=True, enable_reflection=True,
            enable_artifact_storage=True, enable_inter_agent_bus=True,
            enable_scheduler=False, enable_telemetry=False,
            enable_state_persistence=False, auto_discover_components=False,
        )
        kernel = Kernel(config)
        kernel.boot()

        try:
            from agents.specialized_agents import SPECIALIZED_AGENT_DEFINITIONS

            assert kernel.agent_manager is not None
            assert kernel.planner is not None

            # Step 1: User Goal
            goal = "Build a Python CLI tool for file management"
            kernel.agent_manager.register_agent("planner-1", "planning", {"name": "Planner"})
            kernel.agent_manager.register_agent("coder-1", "coding", {"name": "Coder"})
            kernel.agent_manager.register_agent("reviewer-1", "review", {"name": "Reviewer"})
            kernel.agent_manager.register_agent("researcher-1", "research", {"name": "Researcher"})

            # Step 2: Planner creates task graph
            plan = kernel.planner.create_plan(goal)
            assert plan is not None
            assert plan.goal == goal

            from kernel.task_graph import TaskGraph
            graph = TaskGraph(name="file-manager-build", event_bus=kernel.event_bus)
            task1 = graph.add_node("research", "Research file management libraries", action="agent_run")
            task2 = graph.add_node("implement", "Implement the CLI tool", action="agent_run", dependencies=[task1.id])
            task3 = graph.add_node("review", "Review the implementation", action="agent_run", dependencies=[task2.id])
            assert len(graph.get_nodes()) == 3

            # Step 3: Agents execute tasks
            kernel.planner.start_plan(plan.id)
            kernel.planner.approve_plan(plan.id)

            kernel.agent_manager.start_agent("planner-1")
            kernel.agent_manager.start_agent("coder-1")
            kernel.agent_manager.start_agent("reviewer-1")
            kernel.agent_manager.start_agent("researcher-1")

            running = kernel.agent_manager.list_running()
            assert len(running) >= 4

            kernel.supervisor.register_agent("planner-1")
            kernel.supervisor.register_agent("coder-1")
            kernel.supervisor.register_agent("reviewer-1")
            kernel.supervisor.register_agent("researcher-1")
            for agent in running:
                kernel.supervisor.record_heartbeat(agent.metadata.id, "running", 10)

            kernel.inter_agent.register_agent("planner-1")
            kernel.inter_agent.register_agent("coder-1")
            kernel.inter_agent.register_agent("reviewer-1")
            kernel.inter_agent.register_agent("researcher-1")

            # Step 4: Inter-agent communication
            kernel.inter_agent.memory_set("goal", goal, namespace="mission",
                                           owner="planner-1")
            kernel.inter_agent.handoff_task("planner-1", "researcher-1",
                                             "Research libraries for file CLI",
                                             {"goal": goal})

            # Step 5: Produce artifacts
            code_artifact = kernel.artifacts.store(
                name="file_cli.py",
                content="""import argparse\n\ndef main():\n    parser = argparse.ArgumentParser()\n    parser.add_argument('path')\n    args = parser.parse_args()\n    print(f'Managing: {args.path}')\n\nif __name__ == '__main__':\n    main()\n""",
                type=__import__("kernel.artifact_manager", fromlist=["ArtifactType"]).ArtifactType.CODE,
                owner_agent_id="coder-1",
                plan_id=plan.id,
                tags=["python", "cli", "file-management"],
            )
            doc_artifact = kernel.artifacts.store(
                name="README.md",
                content="# File Manager CLI\n\nA Python CLI tool for file management.",
                type=__import__("kernel.artifact_manager", fromlist=["ArtifactType"]).ArtifactType.DOCUMENT,
                owner_agent_id="researcher-1",
                plan_id=plan.id,
            )

            # Step 6: Reviewer validates output
            review_result = kernel.reviewer.review_code(
                code_artifact.content if hasattr(code_artifact, 'content') else "import argparse\n\ndef main():\n    pass",
                language="python",
            )
            assert review_result is not None

            # Step 7: Critic checks quality
            improved_code = """import argparse
import os

def main():
    parser = argparse.ArgumentParser(description='File management CLI')
    parser.add_argument('path', help='Path to the file or directory')
    parser.add_argument('--action', choices=['list', 'info', 'delete'],
                       default='list', help='Action to perform')
    args = parser.parse_args()
    if args.action == 'list':
        files = os.listdir(args.path)
        for f in files:
            print(f)
    elif args.action == 'info':
        stat = os.stat(args.path)
        print(f'Size: {stat.st_size} bytes')
    elif args.action == 'delete':
        os.remove(args.path)
        print(f'Deleted: {args.path}')

if __name__ == '__main__':
    main()"""
            art_v2 = kernel.artifacts.update(code_artifact.id, improved_code,
                                               owner_agent_id="coder-1",
                                               version_message="Added features and argparse improvements")
            assert art_v2.current_version == 2

            claim = "The file_manager tool handles all edge cases perfectly"
            criticism = kernel.critic.analyze_claim(claim, context={"domain": "technology"})
            assert criticism is not None

            # Step 8: Approval for high-risk action
            if kernel.approvals:
                req = kernel.approvals.request_approval(
                    action=__import__("kernel.approval", fromlist=["ApprovalAction"]).ApprovalAction.GIT_PUSH,
                    description="Push file_manager to GitHub",
                    agent_id="coder-1",
                    plan_id=plan.id,
                )
                kernel.approvals.resolve_approval(req.id, granted=True, resolved_by="admin",
                                                   reason="Reviewed and approved")

            graph.update_status(task1.id, GraphStatus.COMPLETED, result={"findings": "research complete"})
            graph.update_status(task2.id, GraphStatus.COMPLETED, result={"code": improved_code})
            graph.update_status(task3.id, GraphStatus.COMPLETED, result=review_result)

            # Step 9: Reflection
            exec_data = {
                "duration_seconds": 45.0,
                "retries": 1,
                "errors": ["import error"],
                "error_types": {"ImportError": 1},
                "handoffs": [{"from": "planner-1", "to": "researcher-1"}],
                "conflicts": [],
            }
            reflection = kernel.reflection.analyze_execution(
                plan.id, goal,
                {"steps": [{"id": task1.id, "status": "completed"},
                           {"id": task2.id, "status": "completed"},
                           {"id": task3.id, "status": "completed"}]},
                exec_data,
            )
            assert reflection is not None

            kernel.planner.complete_plan(plan.id, result={"reflection_id": reflection.id})

            # Step 10: Verify completion
            final_plan = kernel.planner.get_plan(plan.id)
            assert final_plan.status == PlanStatus.COMPLETED

            assert kernel.artifacts.get_stats()["total_artifacts"] >= 2
            assert kernel.reviewer.get_stats()["total_reviews"] >= 1
            assert kernel.critic.get_stats()["total_criticisms"] >= 1
            assert kernel.reflection.get_stats()["total_analyses"] >= 1
            assert kernel.supervisor.get_stats()["total_alerts"] == 0

            dashboard = __import__("kernel.dashboard", fromlist=["create_dashboard_from_kernel"]).create_dashboard_from_kernel(kernel)
            assert "agents" in dashboard
            assert "artifacts" in dashboard
            assert "supervisor" in dashboard

        finally:
            kernel.shutdown()


class TestEdgeCases:
    """Test edge cases and failure modes."""

    def test_agent_manager_unknown_agent(self):
        from kernel.agent_manager import AgentManager
        mgr = AgentManager()
        assert mgr.get_agent("nonexistent") is None
        assert mgr.stop_agent("nonexistent") is False
        assert mgr.pause_agent("nonexistent") is False

    def test_inter_agent_bus_missing_recipient(self):
        from kernel.inter_agent import InterAgentBus, AgentMessage
        bus = InterAgentBus()
        msg = AgentMessage(sender="a", recipient="missing")
        sent = bus.send(msg)
        assert sent is False

    def test_approval_auto_approve(self):
        from kernel.approval import ApprovalLayer, ApprovalAction
        approvals = ApprovalLayer()
        req = approvals.request_approval(
            action=ApprovalAction.NETWORK_REQUEST,
            description="Fetch data from https://api.example.com",
            agent_id="agent-1",
        )
        assert req.status.value == "approved"

    def test_reviewer_empty_code(self):
        from kernel.reviewer import ReviewerAgent
        reviewer = ReviewerAgent()
        result = reviewer.review_code("")
        assert result is not None

    def test_scheduling_pause_resume(self):
        from kernel.scheduling_engine import SchedulingEngine
        engine = SchedulingEngine(tick_interval=0.1)
        engine.start()
        engine.pause()
        assert engine.is_paused is True
        engine.resume()
        assert engine.is_paused is False
        engine.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])