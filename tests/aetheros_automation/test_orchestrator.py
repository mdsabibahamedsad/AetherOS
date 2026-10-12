from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from aetheros_automation.orchestrator import TaskOrchestrator, ExecutionEngine, CheckpointManager
from aetheros_automation.orchestrator.orchestrator import OrchestrationTask, AgentAssignment, AgentMessage
from aetheros_automation.models.models import (
    AgentRole, GraphExecutionMode, RiskLevel, TaskStatus, ApprovalAction, ApprovalResponse,
)
from aetheros_automation.multi_agent import AgentCollaborationManager, AgentMessaging, SubAgentManager
from aetheros_automation.routing.model_router import ModelRouter
from aetheros_automation.recovery import RetryHandler, FallbackHandler
from aetheros_automation.validation.validator import ResultValidator
from aetheros_automation.templates.templates import TaskTemplateManager
from aetheros_automation.nlp.nlp_automation import NLPAutomationEngine


class TestTaskOrchestrator:
    def setup_method(self):
        self.orchestrator = TaskOrchestrator()

    @pytest.mark.asyncio
    async def test_understand_objective(self):
        plan = await self.orchestrator.understand_objective("Research AI providers and compare pricing")
        assert plan is not None
        assert plan.goal == "Research AI providers and compare pricing"
        assert plan.id is not None

    @pytest.mark.asyncio
    async def test_create_execution_plan(self):
        plan = await self.orchestrator.understand_objective("Research AI providers, compare pricing, create a report")
        plan = await self.orchestrator.create_execution_plan(plan)
        assert len(plan.subtasks) > 0
        assert plan.estimated_cost > 0
        assert plan.estimated_time > 0
        assert plan.execution_graph is not None

    @pytest.mark.asyncio
    async def test_role_inference(self):
        text = "write a comprehensive research report about AI"
        plan = await self.orchestrator.understand_objective(text)
        plan = await self.orchestrator.create_execution_plan(plan)
        roles = [t.agent_role for t in plan.subtasks]
        assert AgentRole.RESEARCH in roles or AgentRole.WRITER in roles

    @pytest.mark.asyncio
    async def test_approval_detection(self):
        text = "Delete all files and install new software"
        plan = await self.orchestrator.understand_objective(text)
        plan = await self.orchestrator.create_execution_plan(plan)
        approval_tasks = [t for t in plan.subtasks if t.requires_approval]
        assert len(approval_tasks) > 0

    @pytest.mark.asyncio
    async def test_select_agent(self):
        task = OrchestrationTask(
            id="test-task-1",
            name="Test Task",
            description="Research AI models",
            agent_role=AgentRole.RESEARCH,
            tools=["web_search"],
        )
        agent = await self.orchestrator.select_agent(task)
        assert agent.role == AgentRole.RESEARCH
        assert agent.model is not None
        assert agent.provider is not None

    @pytest.mark.asyncio
    async def test_create_sub_agent(self):
        parent_id = "parent-1"
        sub = await self.orchestrator.create_sub_agent(
            parent_id=parent_id,
            role=AgentRole.RESEARCH,
            goal="Find information",
        )
        assert sub.is_sub_agent
        assert sub.parent_agent_id == parent_id
        assert sub.agent_id is not None

    @pytest.mark.asyncio
    async def test_terminate_sub_agent(self):
        sub = await self.orchestrator.create_sub_agent(
            parent_id="parent-2",
            role=AgentRole.DEVELOPER,
            goal="Write code",
        )
        await self.orchestrator.terminate_sub_agent(sub.agent_id)
        assert sub.agent_id not in self.orchestrator._agent_assignments

    @pytest.mark.asyncio
    async def test_agent_messaging(self):
        msg = await self.orchestrator.send_agent_message(
            sender_id="agent-a",
            receiver_id="agent-b",
            content="Hello from A",
        )
        assert msg.id is not None
        assert msg.sender_id == "agent-a"
        assert msg.receiver_id == "agent-b"

    @pytest.mark.asyncio
    async def test_risk_assessment(self):
        plan = await self.orchestrator.understand_objective(
            "Delete files, install software, and modify permissions"
        )
        plan = await self.orchestrator.create_execution_plan(plan)
        assert plan.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_plan_persistence(self):
        plan = asyncio.run(self.orchestrator.understand_objective("Test persistence"))
        plan = asyncio.run(self.orchestrator.create_execution_plan(plan))
        self.orchestrator.save_plan(plan)
        loaded = self.orchestrator.load_plan(plan.id)
        assert loaded is not None
        assert loaded.goal == plan.goal

    def test_infer_role(self):
        role = self.orchestrator._infer_role("research the latest AI trends")
        assert role == AgentRole.RESEARCH
        role = self.orchestrator._infer_role("write a document")
        assert role == AgentRole.WRITER

    def test_infer_tools(self):
        tools = self.orchestrator._infer_tools("search the web for information")
        assert "web_search" in tools
        tools = self.orchestrator._infer_tools("write code and run terminal commands")
        assert "code_execution" in tools
        assert "terminal" in tools


class TestExecutionGraph:
    def test_decompose_goal(self):
        orch = TaskOrchestrator()
        tasks = [
            OrchestrationTask(id="a", name="Task A", dependencies=[], created_at=0),
            OrchestrationTask(id="b", name="Task B", dependencies=["a"], created_at=0),
            OrchestrationTask(id="c", name="Task C", dependencies=["a", "b"], created_at=0),
        ]
        graph = orch._build_execution_graph(tasks)
        assert "nodes" in graph
        assert "edges" in graph
        assert "levels" in graph

    def test_parallel_execution_levels(self):
        orch = TaskOrchestrator()
        tasks = [
            OrchestrationTask(id="a", name="A", dependencies=[], created_at=0),
            OrchestrationTask(id="b", name="B", dependencies=[], created_at=0),
            OrchestrationTask(id="c", name="C", dependencies=["a", "b"], created_at=0),
        ]
        graph = orch._build_execution_graph(tasks)
        assert len(graph["levels"]) >= 2
        assert "a" in graph["levels"][0]
        assert "b" in graph["levels"][0]

    def test_conditional_task(self):
        task = OrchestrationTask(
            id="cond", name="Conditional", execution_mode=GraphExecutionMode.CONDITIONAL
        )
        assert task.execution_mode == GraphExecutionMode.CONDITIONAL


class TestModelRouter:
    def setup_method(self):
        self.router = ModelRouter()

    @pytest.mark.asyncio
    async def test_select_model(self):
        result = await self.router.select_model(task_type="developer")
        assert result is not None
        assert "model" in result
        assert "provider" in result

    @pytest.mark.asyncio
    async def test_select_model_for_role(self):
        result = await self.router.select_model(task_type="research")
        assert result is not None

    @pytest.mark.asyncio
    async def test_fallback(self):
        fallback = await self.router.get_fallback(model="gpt-4o", provider="openai")
        assert fallback is not None
        assert fallback["model"] != "gpt-4o"

    @pytest.mark.asyncio
    async def test_model_info(self):
        info = self.router.get_model_info("gpt-4o")
        assert info is not None
        assert info["provider"] == "openai"

    def test_list_models(self):
        models = self.router.list_available_models()
        assert len(models) >= 5

    def test_add_remove_model(self):
        self.router.add_model("test-model", {"provider": "test", "reasoning": "low"})
        assert self.router.get_model_info("test-model") is not None
        self.router.remove_model("test-model")
        assert self.router.get_model_info("test-model") is None


class TestRetryHandler:
    def setup_method(self):
        self.handler = RetryHandler(max_retries=3, base_delay=0.1)

    def test_get_backoff(self):
        delay1 = self.handler.get_backoff(1)
        delay2 = self.handler.get_backoff(2)
        delay3 = self.handler.get_backoff(3)
        assert delay1 >= 0
        assert delay2 >= delay1
        assert delay3 >= delay2

    def test_backoff_capped(self):
        handler = RetryHandler(max_retries=5, base_delay=1.0, max_delay=10.0)
        delay = handler.get_backoff(10)
        assert delay <= 10.0

    def test_classify_failure(self):
        from aetheros_automation.models.models import FailureType

        timeout = self.handler.classify_failure(Exception("timeout exceeded"))
        assert timeout == FailureType.TIMEOUT

        rate = self.handler.classify_failure(Exception("rate limit exceeded"))
        assert rate == FailureType.RATE_LIMIT

        auth = self.handler.classify_failure(Exception("invalid_api_key"))
        assert auth == FailureType.AUTH_ERROR

        unknown = self.handler.classify_failure(Exception("something else"))
        assert unknown == FailureType.UNKNOWN


class TestResultValidator:
    def setup_method(self):
        self.validator = ResultValidator()

    @pytest.mark.asyncio
    async def test_validate_valid_result(self):
        task = OrchestrationTask(id="t1", name="Test", description="test")
        result = {"summary": "Task completed successfully", "data": "test output"}
        valid, message = await self.validator.validate(result, task)
        assert valid
        assert message == ""

    @pytest.mark.asyncio
    async def test_validate_none_result(self):
        task = OrchestrationTask(id="t2", name="Test")
        valid, message = await self.validator.validate(None, task)
        assert not valid

    def test_check_not_none(self):
        assert self.validator._check_not_none("data")
        assert not self.validator._check_not_none(None)

    def test_check_has_key(self):
        assert self.validator._check_has_key({"key": "value"}, "key")
        assert not self.validator._check_has_key({"other": "value"}, "key")


class TestTaskTemplateManager:
    def setup_method(self):
        self.manager = TaskTemplateManager()

    def test_list_templates(self):
        templates = self.manager.list_templates()
        assert len(templates) >= 5

    def test_get_template(self):
        template = self.manager.get_template("research_report")
        assert template is not None
        assert template["name"] == "Research Report"

    def test_get_templates_by_category(self):
        dev_templates = self.manager.get_templates_by_category("development")
        assert len(dev_templates) >= 1

    @pytest.mark.asyncio
    async def test_apply_template(self):
        template = self.manager.get_template("research_report")
        assert template is not None
        plan = await self.manager.apply_template(template, {"topic": "AI"})
        assert len(plan.subtasks) > 0
        assert plan.estimated_time > 0

    def test_add_remove_template(self):
        self.manager.add_template("custom", {"name": "Custom", "tasks": []})
        assert self.manager.get_template("custom") is not None
        self.manager.remove_template("custom")
        assert self.manager.get_template("custom") is None


class TestNLPAutomationEngine:
    def setup_method(self):
        self.engine = NLPAutomationEngine()

    @pytest.mark.asyncio
    async def test_process_simple_request(self):
        plan = await self.engine.process("Research AI trends")
        assert len(plan.subtasks) >= 1
        assert plan.goal == "Research AI trends"

    @pytest.mark.asyncio
    async def test_process_complex_request(self):
        plan = await self.engine.process(
            "Research AI providers, compare pricing, write a report, and save as PDF"
        )
        assert len(plan.subtasks) >= 3

    @pytest.mark.asyncio
    async def test_role_inference(self):
        role = self.engine._infer_role("write a detailed report")
        assert role == AgentRole.WRITER
        role = self.engine._infer_role("develop a web application")
        assert role == AgentRole.DEVELOPER

    def test_schedule_detection(self):
        schedule = self.engine._detect_schedule("Every Monday, research AI news")
        assert schedule is not None
        assert schedule["type"] == "weekly"

        schedule = self.engine._detect_schedule("Once, do this task")
        assert schedule is not None
        assert schedule["type"] == "oneshot"

        schedule = self.engine._detect_schedule("No schedule here")
        assert schedule is None


class TestAgentCollaboration:
    def setup_method(self):
        self.collab = AgentCollaborationManager()

    @pytest.mark.asyncio
    async def test_start_collaboration(self):
        collab_id = await self.collab.start_collaboration(
            agent_ids=["agent-1", "agent-2"],
            goal="Work together on research",
        )
        assert collab_id is not None
        conv = self.collab.get_conversation(collab_id)
        assert conv is not None
        assert conv["status"] == "active"

    @pytest.mark.asyncio
    async def test_send_message(self):
        collab_id = await self.collab.start_collaboration(
            agent_ids=["a1", "a2"], goal="test"
        )
        msg = await self.collab.send_message(collab_id, "a1", "Hello", "text")
        assert msg["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_share_result(self):
        collab_id = await self.collab.start_collaboration(
            agent_ids=["a1", "a2"], goal="test"
        )
        await self.collab.share_result(collab_id, "a1", "findings", {"key": "value"})
        result = self.collab.get_shared_result(collab_id, "findings")
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_end_collaboration(self):
        collab_id = await self.collab.start_collaboration(
            agent_ids=["a1", "a2"], goal="test"
        )
        await self.collab.end_collaboration(collab_id)
        conv = self.collab.get_conversation(collab_id)
        assert conv is None or conv["status"] == "completed"


class TestAgentMessaging:
    def setup_method(self):
        self.messaging = AgentMessaging()

    @pytest.mark.asyncio
    async def test_send_receive(self):
        await self.messaging.send("sender", "receiver", "Hello", "text")
        msgs = self.messaging.get_messages(agent_id="receiver")
        assert len(msgs) >= 1
        assert msgs[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_conversation(self):
        await self.messaging.send("a", "b", "Msg 1")
        await self.messaging.send("b", "a", "Reply 1")
        conv = self.messaging.get_conversation("a", "b")
        assert len(conv) == 2


class TestSubAgentManager:
    def setup_method(self):
        self.manager = SubAgentManager()

    @pytest.mark.asyncio
    async def test_create_sub_agent(self):
        sub = await self.manager.create_sub_agent(
            parent_id="parent-1",
            role=AgentRole.RESEARCH,
            goal="Find data",
        )
        assert sub.is_sub_agent
        assert sub.parent_agent_id == "parent-1"

    @pytest.mark.asyncio
    async def test_terminate_sub_agent(self):
        sub = await self.manager.create_sub_agent("p1", AgentRole.DEVELOPER, "code")
        await self.manager.terminate_sub_agent(sub.agent_id)
        assert self.manager.get_agent(sub.agent_id) is None

    @pytest.mark.asyncio
    async def test_terminate_all(self):
        for i in range(3):
            await self.manager.create_sub_agent("p2", AgentRole.RESEARCH, f"task {i}")
        await self.manager.terminate_all_sub_agents("p2")
        assert self.manager.get_active_sub_agents("p2") == 0


class TestCheckpointManager:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = CheckpointManager(base_dir=self.temp_dir)

    @pytest.mark.asyncio
    async def test_save_checkpoint(self):
        cp_id = await self.manager.save_checkpoint(
            plan_id="plan-1", task_id="task-1", result="done"
        )
        assert cp_id is not None

    @pytest.mark.asyncio
    async def test_load_checkpoint(self):
        cp_id = await self.manager.save_checkpoint("plan-1", "task-1", "done")
        loaded = await self.manager.load_checkpoint("plan-1", cp_id)
        assert loaded is not None
        assert loaded["result"] == "done"

    @pytest.mark.asyncio
    async def test_list_checkpoints(self):
        for i in range(3):
            await self.manager.save_checkpoint("plan-1", f"task-{i}", f"result-{i}")
        checkpoints = await self.manager.list_checkpoints("plan-1")
        assert len(checkpoints) == 3

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self):
        cp_id = await self.manager.save_checkpoint("plan-1", "task-1", "done")
        deleted = await self.manager.delete_checkpoint("plan-1", cp_id)
        assert deleted
        checkpoints = await self.manager.list_checkpoints("plan-1")
        assert len(checkpoints) == 0


class TestFallbackHandler:
    def setup_method(self):
        self.handler = FallbackHandler()

    @pytest.mark.asyncio
    async def test_fallback_chain(self):
        async def fail():
            raise ValueError("fail")

        async def succeed():
            return "success"

        success, result, fb_name = await self.handler.execute_fallback_chain(
            [fail, succeed]
        )
        assert success
        assert result == "success"
        assert fb_name == 1

    @pytest.mark.asyncio
    async def test_all_fail(self):
        async def fail():
            raise ValueError("fail")

        success, result, idx = await self.handler.execute_fallback_chain([fail, fail])
        assert not success
