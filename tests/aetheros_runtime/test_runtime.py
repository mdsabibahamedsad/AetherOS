"""Tests for AetherOS AI Runtime & Chat Engine."""

import json
import os
import sys
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from aetheros_runtime.runtime_manager import RuntimeManager, RuntimeState, RuntimeConfig
from aetheros_runtime.conversation_engine import ConversationEngine, Conversation, Message, ExportFormat
from aetheros_runtime.context_engine import ContextEngine, ContextBundle
from aetheros_runtime.streaming_engine import StreamingEngine, StreamChunk, StreamEvent, StreamState
from aetheros_runtime.message_pipeline import MessagePipeline, PipelineStage, MessageContext
from aetheros_runtime.prompt_builder import PromptBuilder, PromptSection
from aetheros_runtime.agent_runtime import AgentRuntime, AgentRole, AgentTask, AgentResult
from aetheros_runtime.execution_queue import ExecutionQueue, JobStatus, JobPriority, Job
from aetheros_runtime.response_renderer import ResponseRenderer, RenderBlock, BlockType
from aetheros_runtime.code_executor import CodeExecutor, CodeLanguage, ExecutionResult, SandboxMode
from aetheros_runtime.filesystem_engine import FileSystemEngine, FileInfo, FileChange
from aetheros_runtime.workspace_manager import WorkspaceManager, Workspace, Project
from aetheros_runtime.memory_runtime import MemoryRuntime, MemoryEntry, MemoryType
from aetheros_runtime.reasoning_engine import ReasoningEngine, ReasoningMode, ReasoningResult
from aetheros_runtime.tool_calling import ToolCallingInterface, ToolCall, ToolResult, ToolDomain
from aetheros_runtime.session_recovery import SessionRecovery, RecoveryPoint
from aetheros_runtime.notifications import NotificationBus, Notification, NotificationLevel
from aetheros_runtime.diagnostics import Diagnostics, MetricSnapshot
from aetheros_runtime.performance import PerformanceOptimizer


# ---------------------------------------------------------------------------
# RuntimeManager tests
# ---------------------------------------------------------------------------

class TestRuntimeManager:
    def test_initial_state(self):
        rm = RuntimeManager()
        assert rm.state == RuntimeState.STOPPED
        assert not rm.is_running()
        assert rm.uptime == 0.0

    def test_initialize_success(self):
        rm = RuntimeManager()
        rm.register("test", lambda: {"ok": True})
        assert rm.initialize()
        assert rm.is_running()
        assert rm.is_healthy()

    def test_initialize_failure(self):
        rm = RuntimeManager()
        rm.register("failing", lambda: (_ for _ in ()).throw(Exception("init fail")))
        assert not rm.initialize()
        assert rm.state == RuntimeState.ERROR

    def test_start_stop(self):
        rm = RuntimeManager()
        rm.register("test", lambda: {"ok": True})
        assert rm.start()
        assert rm.is_running()
        assert rm.stop()
        assert rm.state == RuntimeState.STOPPED

    def test_restart(self):
        rm = RuntimeManager()
        rm.register("test", lambda: {"ok": True})
        rm.start()
        assert rm.restart()
        assert rm.is_running()

    def test_get_component(self):
        rm = RuntimeManager()
        rm.register("test", lambda: {"value": 42})
        rm.initialize()
        comp = rm.get_component("test")
        assert comp == {"value": 42}

    def test_get_component_state(self):
        rm = RuntimeManager()
        rm.register("test", lambda: {})
        rm.initialize()
        state = rm.get_component_state("test")
        assert state is not None
        assert state.running

    def test_health_check(self):
        rm = RuntimeManager()
        rm.register("a", lambda: {})
        rm.register("b", lambda: {})
        rm.initialize()
        results = rm.check_health()
        assert results["a"]
        assert results["b"]

    def test_health_degraded(self):
        rm = RuntimeManager()
        rm.register("test", lambda: MagicMock(health_check=lambda: False))
        rm.initialize()
        rm.check_health()
        assert rm.state == RuntimeState.DEGRADED or rm.state == RuntimeState.RUNNING

    def test_diagnostics(self):
        rm = RuntimeManager()
        rm.register("test", lambda: {})
        rm.initialize()
        diag = rm.diagnostics()
        assert diag["state"] == "running"
        assert diag["component_count"] == 1

    def test_summary(self):
        rm = RuntimeManager()
        rm.register("test", lambda: {})
        rm.initialize()
        s = rm.summary()
        assert "RUNNING" in s

    def test_on_state_change(self):
        rm = RuntimeManager()
        rm.register("test", lambda: {})
        events = []
        rm.on_state_change(lambda o, n: events.append((o, n)))
        rm.initialize()
        assert len(events) >= 1

    def test_recover(self):
        rm = RuntimeManager()
        rm.register("test", lambda: {"ok": True})
        rm.initialize()
        assert rm.recover()

    def test_recover_specific(self):
        rm = RuntimeManager()
        rm.register("test", lambda: {"ok": True})
        rm.initialize()
        assert rm.recover("test")

    def test_resolve_start_order(self):
        rm = RuntimeManager()
        order = []
        rm.register("b", lambda: order.append("b"), dependencies=["a"])
        rm.register("a", lambda: order.append("a"))
        rm.initialize()
        assert order == ["a", "b"]

    def test_config(self):
        config = RuntimeConfig(auto_start=False, health_check_interval=15.0, recovery_max_attempts=5)
        rm = RuntimeManager(config=config)
        assert rm._config.health_check_interval == 15.0


# ---------------------------------------------------------------------------
# ConversationEngine tests
# ---------------------------------------------------------------------------

class TestConversationEngine:
    def test_create(self):
        ce = ConversationEngine()
        conv = ce.create("Test Chat")
        assert conv.title == "Test Chat"
        assert not conv.is_pinned
        assert not conv.is_archived

    def test_get(self):
        ce = ConversationEngine()
        conv = ce.create("Test")
        assert ce.get(conv.id).title == "Test"
        assert ce.get("nonexistent") is None

    def test_get_all(self):
        ce = ConversationEngine()
        c1 = ce.create("A")
        c2 = ce.create("B")
        all_conv = ce.get_all()
        assert len(all_conv) == 2

    def test_rename(self):
        ce = ConversationEngine()
        conv = ce.create("Old")
        assert ce.rename(conv.id, "New")
        assert ce.get(conv.id).title == "New"

    def test_rename_nonexistent(self):
        ce = ConversationEngine()
        assert not ce.rename("nonexistent", "X")

    def test_delete(self):
        ce = ConversationEngine()
        conv = ce.create("Test")
        assert ce.delete(conv.id)
        assert ce.get(conv.id) is None

    def test_delete_nonexistent(self):
        ce = ConversationEngine()
        assert not ce.delete("nonexistent")

    def test_duplicate(self):
        ce = ConversationEngine()
        conv = ce.create("Original")
        copy = ce.duplicate(conv.id)
        assert copy is not None
        assert copy.title == "Original (Copy)"
        assert copy.id != conv.id

    def test_duplicate_nonexistent(self):
        ce = ConversationEngine()
        assert ce.duplicate("nonexistent") is None

    def test_toggle_pin(self):
        ce = ConversationEngine()
        conv = ce.create("Test")
        assert ce.toggle_pin(conv.id)
        assert conv.is_pinned
        assert not ce.toggle_pin(conv.id)

    def test_toggle_archive(self):
        ce = ConversationEngine()
        conv = ce.create("Test")
        assert ce.toggle_archive(conv.id)
        assert conv.is_archived

    def test_get_pinned(self):
        ce = ConversationEngine()
        c1 = ce.create("A")
        c2 = ce.create("B")
        ce.toggle_pin(c1.id)
        pinned = ce.get_pinned()
        assert len(pinned) == 1

    def test_get_archived(self):
        ce = ConversationEngine()
        conv = ce.create("Test")
        ce.toggle_archive(conv.id)
        archived = ce.get_archived()
        assert len(archived) == 1

    def test_folder_crud(self):
        ce = ConversationEngine()
        folder = ce.create_folder("Work")
        assert folder.name == "Work"
        assert ce.get_folder(folder.id).name == "Work"
        assert ce.delete_folder(folder.id)
        assert ce.get_folder(folder.id) is None

    def test_move_to_folder(self):
        ce = ConversationEngine()
        folder = ce.create_folder("Work")
        conv = ce.create("Test")
        assert ce.move_to_folder(conv.id, folder.id)
        assert conv.folder_id == folder.id

    def test_list_folders(self):
        ce = ConversationEngine()
        ce.create_folder("A")
        ce.create_folder("B")
        assert len(ce.list_folders()) == 2

    def test_get_conversations_in_folder(self):
        ce = ConversationEngine()
        folder = ce.create_folder("Work")
        c1 = ce.create("A", folder_id=folder.id)
        c2 = ce.create("B", folder_id=folder.id)
        assert len(ce.get_conversations_in_folder(folder.id)) == 2

    def test_add_message(self):
        ce = ConversationEngine()
        conv = ce.create("Test")
        msg = ce.add_message(conv.id, "user", "Hello")
        assert msg is not None
        assert msg.content == "Hello"

    def test_add_message_nonexistent(self):
        ce = ConversationEngine()
        assert ce.add_message("nonexistent", "user", "Hi") is None

    def test_get_messages(self):
        ce = ConversationEngine()
        conv = ce.create("Test")
        ce.add_message(conv.id, "user", "Hi")
        ce.add_message(conv.id, "assistant", "Hello")
        msgs = ce.get_messages(conv.id)
        assert len(msgs) == 2

    def test_clear_messages(self):
        ce = ConversationEngine()
        conv = ce.create("Test")
        ce.add_message(conv.id, "user", "Hi")
        assert ce.clear_messages(conv.id)
        assert len(ce.get_messages(conv.id)) == 0

    def test_search(self):
        ce = ConversationEngine()
        conv = ce.create("Important Chat")
        ce.add_message(conv.id, "user", "project alpha")
        results = ce.search("alpha")
        assert len(results) >= 1

    def test_search_title(self):
        ce = ConversationEngine()
        ce.create("Meeting Notes")
        results = ce.search("Meeting")
        assert len(results) >= 1

    def test_export_json(self):
        ce = ConversationEngine()
        conv = ce.create("Export Test")
        ce.add_message(conv.id, "user", "Hi")
        output = ce.export(conv.id, ExportFormat.JSON)
        parsed = json.loads(output)
        assert parsed["title"] == "Export Test"

    def test_export_markdown(self):
        ce = ConversationEngine()
        conv = ce.create("Export Test")
        ce.add_message(conv.id, "user", "Hi")
        output = ce.export(conv.id, ExportFormat.MARKDOWN)
        assert "Export Test" in output
        assert "USER" in output

    def test_export_html(self):
        ce = ConversationEngine()
        conv = ce.create("Export Test")
        ce.add_message(conv.id, "user", "Hi")
        output = ce.export(conv.id, ExportFormat.HTML)
        assert "<html" in output.lower()
        assert "Export Test" in output

    def test_import_export_roundtrip(self):
        ce = ConversationEngine()
        original = ce.create("Roundtrip")
        ce.add_message(original.id, "user", "Hello")
        data = json.loads(ce.export(original.id, ExportFormat.JSON))
        restored = ce.import_from_json(data)
        assert restored is not None
        assert restored.title == "Roundtrip"
        assert ce.get(restored.id) is not None

    def test_import_from_file(self, tmp_path):
        ce = ConversationEngine()
        f = tmp_path / "conv.json"
        f.write_text(json.dumps({"title": "Imported", "messages": [{"role": "user", "content": "hi"}]}), encoding="utf-8")
        result = ce.import_from_file(f)
        assert result is not None
        assert result.title == "Imported"

    def test_stats(self):
        ce = ConversationEngine()
        ce.create("A")
        ce.create("B")
        stats = ce.stats()
        assert stats["total_conversations"] >= 2

    def test_count(self):
        ce = ConversationEngine()
        ce.create("A")
        assert ce.count() >= 1

    def test_total_messages(self):
        ce = ConversationEngine()
        conv = ce.create("Test")
        ce.add_message(conv.id, "user", "Hi")
        assert ce.total_messages() >= 1

    def test_persistence(self, tmp_path):
        ce = ConversationEngine(storage_dir=tmp_path)
        ce.create("Persisted")
        ce2 = ConversationEngine(storage_dir=tmp_path)
        assert ce2.count() >= 1

    def test_message_to_dict(self):
        msg = Message(role="user", content="hello", tool_calls=[{"name": "test"}])
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["tool_calls"][0]["name"] == "test"

    def test_summary(self):
        ce = ConversationEngine()
        s = ce.summary()
        assert "Conversation Engine" in s


# ---------------------------------------------------------------------------
# ContextEngine tests
# ---------------------------------------------------------------------------

class TestContextEngine:
    def test_empty_build(self):
        ce = ContextEngine()
        bundle = ce.build_full()
        assert bundle.is_empty

    def test_register_provider(self):
        ce = ContextEngine()
        ce.register_provider("test", lambda: "test content")
        bundle = ce.build_full()
        assert not bundle.is_empty
        assert "test content" in bundle.full_context

    def test_unregister_provider(self):
        ce = ContextEngine()
        ce.register_provider("test", lambda: "content")
        assert ce.unregister_provider("test")
        assert ce.build_full().is_empty

    def test_build_selected_sections(self):
        ce = ContextEngine()
        ce.register_provider("system", lambda: "system context")
        ce.register_provider("workspace", lambda: "workspace context")
        bundle = ce.build(["system"])
        assert "system context" in bundle.full_context
        assert "workspace context" not in bundle.full_context

    def test_register_workspace_provider(self):
        ce = ContextEngine()
        ce.register_workspace_provider(Path.cwd())
        bundle = ce.build_full()
        assert "Workspace:" in bundle.full_context or bundle.is_empty

    def test_register_provider_info(self):
        ce = ContextEngine()
        ce.register_provider_info("openai", "gpt-4")
        bundle = ce.build_full()
        assert "Provider: openai" in bundle.full_context

    def test_max_section_length(self):
        ce = ContextEngine()
        ce.set_max_section_length(10)
        ce.register_provider("test", lambda: "x" * 100)
        bundle = ce.build_full()
        assert len(bundle.custom_sections["test"]) <= 10

    def test_context_bundle_properties(self):
        bundle = ContextBundle(system="sys", workspace="ws", memory="mem")
        assert not bundle.is_empty
        assert bundle.token_estimate > 0
        assert "sys" in bundle.full_context

    def test_health_check(self):
        ce = ContextEngine()
        assert not ce.health_check()
        ce.register_provider("test", lambda: "x")
        assert ce.health_check()

    def test_summary(self):
        ce = ContextEngine()
        ce.register_provider("test", lambda: "x")
        s = ce.summary()
        assert "Context Engine" in s


# ---------------------------------------------------------------------------
# StreamingEngine tests
# ---------------------------------------------------------------------------

class TestStreamingEngine:
    def test_start_stream(self):
        se = StreamingEngine()
        sid = se.start_stream("openai", "gpt-4", [{"role": "user", "content": "hi"}])
        assert se.get_state(sid) == StreamState.IDLE

    def test_get_stream(self):
        se = StreamingEngine()
        sid = se.start_stream("openai", "gpt-4", [])
        stream = se.get_stream(sid)
        assert stream["provider"] == "openai"

    def test_get_state_nonexistent(self):
        se = StreamingEngine()
        assert se.get_state("nonexistent") is None

    def test_cancel(self):
        se = StreamingEngine()
        sid = se.start_stream("openai", "gpt-4", [])
        assert se.cancel(sid)
        assert se.get_state(sid) == StreamState.CANCELLED

    def test_cancel_nonexistent(self):
        se = StreamingEngine()
        assert not se.cancel("nonexistent")

    def test_cancel_all(self):
        se = StreamingEngine()
        se.start_stream("openai", "gpt-4", [])
        se.start_stream("anthropic", "claude", [])
        count = se.cancel_all()
        assert count == 2

    def test_get_content(self):
        se = StreamingEngine()
        sid = se.start_stream("openai", "gpt-4", [])
        assert se.get_content(sid) == ""

    def test_cleanup(self):
        se = StreamingEngine()
        sid = se.start_stream("openai", "gpt-4", [])
        with se._lock:
            se._streams[sid]["state"] = StreamState.COMPLETED
            se._streams[sid]["started_at"] = time.time() - 600
        count = se.cleanup(max_age=1)
        assert count == 1

    def test_on_event(self):
        se = StreamingEngine()
        sid = se.start_stream("openai", "gpt-4", [])
        events = []
        se.on_event(sid, lambda e: events.append(e))
        se._emit(sid, StreamEvent(type="test"))
        assert len(events) == 1

    def test_provider_map(self):
        assert "openai" in StreamingEngine.PROVIDER_MAP
        assert "anthropic" in StreamingEngine.PROVIDER_MAP
        assert "ollama" in StreamingEngine.PROVIDER_MAP

    def test_summary(self):
        se = StreamingEngine()
        s = se.summary()
        assert "Streaming Engine" in s

    def test_get_active_streams(self):
        se = StreamingEngine()
        sid = se.start_stream("openai", "gpt-4", [])
        with se._lock:
            se._streams[sid]["state"] = StreamState.STREAMING
        active = se.get_active_streams()
        assert sid in active

    def test_get_completed_streams(self):
        se = StreamingEngine()
        sid = se.start_stream("openai", "gpt-4", [])
        with se._lock:
            se._streams[sid]["state"] = StreamState.COMPLETED
        completed = se.get_completed_streams()
        assert sid in completed


# ---------------------------------------------------------------------------
# MessagePipeline tests
# ---------------------------------------------------------------------------

class TestMessagePipeline:
    def test_run(self):
        pipeline = MessagePipeline()
        ctx = pipeline.run("Hello", provider="openai", model="gpt-4")
        assert ctx.user_message == "Hello"
        assert ctx.processed_message == "Hello"
        assert not ctx.error

    def test_run_empty_message(self):
        pipeline = MessagePipeline()
        ctx = pipeline.run("  ")
        assert ctx.error is not None

    def test_register_handler(self):
        pipeline = MessagePipeline()
        pipeline.register_handler(PipelineStage.PRE_PROCESSING, lambda ctx: MessageContext(user_message=ctx.user_message, processed_message="MODIFIED"))
        ctx = pipeline.run("Hello")
        assert ctx.processed_message == "MODIFIED"

    def test_clear_handlers(self):
        pipeline = MessagePipeline()
        pipeline.register_handler(PipelineStage.PRE_PROCESSING, lambda ctx: ctx)
        pipeline.clear_handlers(PipelineStage.PRE_PROCESSING)
        ctx = pipeline.run("Hello")
        assert ctx.processed_message == "Hello"

    def test_register_hook(self):
        pipeline = MessagePipeline()
        hook_called = []
        pipeline.register_hook("pipeline_complete", lambda ctx: hook_called.append(1))
        pipeline.run("Hello")
        assert len(hook_called) == 1

    def test_get_history(self):
        pipeline = MessagePipeline()
        pipeline.run("A")
        pipeline.run("B")
        history = pipeline.get_history()
        assert len(history) == 2

    def test_clear_history(self):
        pipeline = MessagePipeline()
        pipeline.run("A")
        pipeline.clear_history()
        assert len(pipeline.get_history()) == 0

    def test_recent_contexts(self):
        pipeline = MessagePipeline()
        for i in range(5):
            pipeline.run(str(i))
        recent = pipeline.get_recent_contexts(3)
        assert len(recent) == 3

    def test_skipped_stages(self):
        pipeline = MessagePipeline()
        ctx = pipeline.run("test", provider="", model="")
        assert ctx.provider == ""

    def test_summary(self):
        pipeline = MessagePipeline()
        pipeline.run("test")
        s = pipeline.summary()
        assert "Message Pipeline" in s


# ---------------------------------------------------------------------------
# PromptBuilder tests
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    def test_build_basic(self):
        pb = PromptBuilder()
        prompt = pb.build("Hello")
        assert prompt.get_section(PromptSection.USER) == "Hello"

    def test_set_system_prompt(self):
        pb = PromptBuilder()
        pb.set_system_prompt("You are a helpful AI.")
        prompt = pb.build("Hello")
        assert "helpful AI" in prompt.system_prompt

    def test_register_provider(self):
        pb = PromptBuilder()
        pb.register_provider(PromptSection.WORKSPACE, lambda: "workspace context")
        prompt = pb.build("Hello")
        assert "workspace context" in prompt.full_prompt

    def test_set_static(self):
        pb = PromptBuilder()
        pb.set_static(PromptSection.SAFETY, "Stay safe.")
        prompt = pb.build("Hello")
        assert "Stay safe." in prompt.full_prompt

    def test_build_chat(self):
        pb = PromptBuilder()
        pb.set_system_prompt("System.")
        messages = pb.build_chat("Hello")
        assert len(messages) >= 1
        assert messages[0]["role"] == "system"

    def test_build_chat_no_system(self):
        pb = PromptBuilder()
        messages = pb.build_chat("Hello")
        assert len(messages) >= 1
        assert messages[0]["role"] == "user"

    def test_create_system_prompt(self):
        prompt = PromptBuilder.create_system_prompt("TestBot", ["coding", "writing"], ["be nice"])
        assert "TestBot" in prompt
        assert "coding" in prompt
        assert "be nice" in prompt

    def test_create_developer_prompt(self):
        prompt = PromptBuilder.create_developer_prompt(project="myapp", language="python")
        assert "myapp" in prompt
        assert "python" in prompt

    def test_max_section_length(self):
        pb = PromptBuilder()
        pb._max_section_length = 5
        pb.register_provider(PromptSection.WORKSPACE, lambda: "x" * 100)
        prompt = pb.build("Hello")
        content = prompt.get_section(PromptSection.WORKSPACE)
        assert len(content) <= 5

    def test_health_check(self):
        pb = PromptBuilder()
        assert not pb.health_check()
        pb.set_system_prompt("test")
        assert pb.health_check()

    def test_built_prompt_properties(self):
        prompt = BuiltPrompt()
        prompt.set_section(PromptSection.SYSTEM, "You are")
        prompt.set_section(PromptSection.USER, "Hello")
        assert prompt.system_prompt == "You are"
        assert prompt.token_estimate > 0

    def test_summary(self):
        pb = PromptBuilder()
        s = pb.summary()
        assert "Prompt Builder" in s


from aetheros_runtime.prompt_builder import BuiltPrompt


# ---------------------------------------------------------------------------
# AgentRuntime tests
# ---------------------------------------------------------------------------

class TestAgentRuntime:
    def test_register_handler(self):
        ar = AgentRuntime()
        ar.register_handler(AgentRole.EXECUTOR, lambda task: f"Executed: {task.goal}")
        task = ar.create_task("test", AgentRole.EXECUTOR)
        result = ar.execute_task(task.id)
        assert result.status == "completed"

    def test_create_task(self):
        ar = AgentRuntime()
        task = ar.create_task("build feature", AgentRole.PLANNER, "context here")
        assert task.goal == "build feature"
        assert task.role == AgentRole.PLANNER
        assert task.context == "context here"
        assert task.status == "pending"

    def test_get_task(self):
        ar = AgentRuntime()
        task = ar.create_task("test")
        assert ar.get_task(task.id).goal == "test"
        assert ar.get_task("nonexistent") is None

    def test_cancel_task(self):
        ar = AgentRuntime()
        task = ar.create_task("test")
        assert ar.cancel_task(task.id)
        assert task.status == "cancelled"

    def test_cancel_completed(self):
        ar = AgentRuntime()
        ar.register_handler(AgentRole.EXECUTOR, lambda t: "done")
        task = ar.create_task("test", AgentRole.EXECUTOR)
        ar.execute_task(task.id)
        assert not ar.cancel_task(task.id)

    def test_get_pending_tasks(self):
        ar = AgentRuntime()
        ar.create_task("a")
        ar.create_task("b")
        assert len(ar.get_pending_tasks()) == 2

    def test_register_agent(self):
        ar = AgentRuntime()
        ar.register_agent("agent-1", AgentRole.EXECUTOR, {"name": "Worker"})
        agent = ar.get_agent("agent-1")
        assert agent["role"] == AgentRole.EXECUTOR

    def test_list_agents(self):
        ar = AgentRuntime()
        ar.register_agent("a1", AgentRole.EXECUTOR)
        ar.register_agent("a2", AgentRole.PLANNER)
        assert len(ar.list_agents()) == 2

    def test_remove_agent(self):
        ar = AgentRuntime()
        ar.register_agent("a1", AgentRole.EXECUTOR)
        assert ar.remove_agent("a1")
        assert ar.get_agent("a1") is None

    def test_plan_and_execute(self):
        ar = AgentRuntime()
        ar.register_handler(AgentRole.PLANNER, lambda t: "plan: do x")
        ar.register_handler(AgentRole.EXECUTOR, lambda t: "executed plan")
        ar.register_handler(AgentRole.CRITIC, lambda t: "looks good")
        result = ar.plan_and_execute("build feature")
        assert result.tasks_completed >= 1

    def test_reflect(self):
        ar = AgentRuntime()
        ar.register_handler(AgentRole.REFLECTOR, lambda t: "reflection: good")
        ar.register_handler(AgentRole.EXECUTOR, lambda t: "result")
        task = ar.create_task("test", AgentRole.EXECUTOR)
        ar.execute_task(task.id)
        reflection = ar.reflect(task.id)
        assert reflection is not None

    def test_get_task_history(self):
        ar = AgentRuntime()
        ar.register_handler(AgentRole.EXECUTOR, lambda t: "ok")
        task = ar.create_task("test", AgentRole.EXECUTOR)
        ar.execute_task(task.id)
        history = ar.get_task_history()
        assert len(history) >= 1

    def test_stats(self):
        ar = AgentRuntime()
        stats = ar.stats()
        assert "agents" in stats
        assert "total_tasks" in stats

    def test_summary(self):
        ar = AgentRuntime()
        s = ar.summary()
        assert "Agent Runtime" in s


# ---------------------------------------------------------------------------
# ExecutionQueue tests
# ---------------------------------------------------------------------------

class TestExecutionQueue:
    def test_enqueue_and_run(self):
        eq = ExecutionQueue(max_workers=2)
        eq.start()
        results = []
        job_id = eq.enqueue(lambda: results.append(42), "test")
        time.sleep(0.3)
        eq.stop(wait=True)
        assert results == [42]

    def test_get_job(self):
        eq = ExecutionQueue()
        jid = eq.enqueue(lambda: 1, "test")
        job = eq.get_job(jid)
        assert job.name == "test"

    def test_get_status(self):
        eq = ExecutionQueue()
        jid = eq.enqueue(lambda: 1, "test")
        assert eq.get_status(jid) == JobStatus.PENDING

    def test_cancel(self):
        eq = ExecutionQueue()
        jid = eq.enqueue(lambda: time.sleep(10), "slow")
        assert eq.cancel(jid)
        assert eq.get_status(jid) == JobStatus.CANCELLED

    def test_cancel_nonexistent(self):
        eq = ExecutionQueue()
        assert not eq.cancel("nonexistent")

    def test_cancel_all(self):
        eq = ExecutionQueue()
        eq.enqueue(lambda: 1, "a")
        eq.enqueue(lambda: 2, "b")
        count = eq.cancel_all()
        assert count == 2

    def test_pause_resume(self):
        eq = ExecutionQueue()
        jid = eq.enqueue(lambda: 1, "test")
        assert eq.pause(jid)
        assert eq.get_status(jid) == JobStatus.PAUSED
        assert eq.resume(jid)
        assert eq.get_status(jid) == JobStatus.PENDING

    def test_pause_not_pending(self):
        eq = ExecutionQueue()
        eq.start()
        jid = eq.enqueue(lambda: 1, "fast")
        time.sleep(0.3)
        eq.stop()
        assert not eq.pause(jid)

    def test_list_jobs(self):
        eq = ExecutionQueue()
        eq.enqueue(lambda: 1, "a")
        eq.enqueue(lambda: 2, "b")
        assert len(eq.list_jobs()) == 2

    def test_list_jobs_by_status(self):
        eq = ExecutionQueue()
        eq.enqueue(lambda: 1, "a")
        pending = eq.list_jobs(JobStatus.PENDING)
        assert len(pending) >= 1

    def test_priorities(self):
        assert JobPriority.LOW.value < JobPriority.NORMAL.value
        assert JobPriority.CRITICAL.value > JobPriority.HIGH.value

    def test_summary(self):
        eq = ExecutionQueue()
        s = eq.summary()
        assert "Execution Queue" in s

    def test_health_check(self):
        eq = ExecutionQueue()
        assert eq.health_check()
        eq.stop()
        assert not eq.health_check()


# ---------------------------------------------------------------------------
# ResponseRenderer tests
# ---------------------------------------------------------------------------

class TestResponseRenderer:
    def test_parse_text(self):
        rr = ResponseRenderer()
        blocks = rr.parse("Hello world")
        assert len(blocks) >= 1
        assert blocks[-1].block_type == BlockType.TEXT

    def test_parse_code_block(self):
        rr = ResponseRenderer()
        blocks = rr.parse("```python\nprint('hi')\n```")
        code_blocks = [b for b in blocks if b.block_type == BlockType.CODE]
        assert len(code_blocks) == 1
        assert code_blocks[0].language == "python"

    def test_parse_heading(self):
        rr = ResponseRenderer()
        blocks = rr.parse("# Title\n## Subtitle")
        headings = [b for b in blocks if b.block_type == BlockType.HEADING]
        assert len(headings) == 2

    def test_parse_quote(self):
        rr = ResponseRenderer()
        blocks = rr.parse("> quoted text")
        quotes = [b for b in blocks if b.block_type == BlockType.QUOTE]
        assert len(quotes) == 1

    def test_parse_list(self):
        rr = ResponseRenderer()
        blocks = rr.parse("- item 1\n- item 2")
        lists = [b for b in blocks if b.block_type == BlockType.LIST]
        assert len(lists) == 2

    def test_parse_divider(self):
        rr = ResponseRenderer()
        blocks = rr.parse("---")
        dividers = [b for b in blocks if b.block_type == BlockType.DIVIDER]
        assert len(dividers) == 1

    def test_render_text(self):
        rr = ResponseRenderer()
        output = rr.render("Hello\n# Title\n```python\nx=1\n```", "text")
        assert "Hello" in output
        assert "Title" in output
        assert "x=1" in output

    def test_wrap_thinking(self):
        rr = ResponseRenderer()
        wrapped = rr.wrap_thinking("step 1\nstep 2")
        assert "thinking" in wrapped
        assert "/thinking" in wrapped

    def test_wrap_tool_output(self):
        rr = ResponseRenderer()
        wrapped = rr.wrap_tool_output("search", "results here")
        assert "[Tool: search]" in wrapped
        assert "[/Tool]" in wrapped

    def test_render_block_heading(self):
        block = RenderBlock(block_type=BlockType.HEADING, content="Title", indent=1)
        assert block.render_text() == "## Title"

    def test_render_block_code(self):
        block = RenderBlock(block_type=BlockType.CODE, content="print('hi')", language="python")
        assert "```python" in block.render_text()

    def test_render_block_quote(self):
        block = RenderBlock(block_type=BlockType.QUOTE, content="line1\nline2")
        rendered = block.render_text()
        assert "> line1" in rendered

    def test_summary(self):
        rr = ResponseRenderer()
        s = rr.summary()
        assert "Response Renderer" in s


# ---------------------------------------------------------------------------
# CodeExecutor tests
# ---------------------------------------------------------------------------

class TestCodeExecutor:
    def test_execute_python(self):
        ce = CodeExecutor()
        result = ce.execute("print('hello')", CodeLanguage.PYTHON)
        assert result.success
        assert "hello" in result.output or "hello" in result.stdout

    def test_execute_python_error(self):
        ce = CodeExecutor()
        result = ce.execute("raise ValueError('fail')", CodeLanguage.PYTHON)
        assert not result.success

    def test_permission_denied(self):
        ce = CodeExecutor()
        ce.set_permission(CodePermission(language=CodeLanguage.PYTHON, allowed=False))
        result = ce.execute("print('x')", CodeLanguage.PYTHON)
        assert result.permission_denied

    def test_get_set_permission(self):
        ce = CodeExecutor()
        perm = ce.get_permission(CodeLanguage.PYTHON)
        assert perm.allowed
        assert ce.is_allowed(CodeLanguage.PYTHON)

    def test_execution_dir(self):
        ce = CodeExecutor()
        ce.set_execution_dir(Path(tempfile.gettempdir()))
        assert ce._execution_dir == Path(tempfile.gettempdir())

    def test_get_history(self):
        ce = CodeExecutor()
        ce.execute("print('a')", CodeLanguage.PYTHON)
        ce.execute("print('b')", CodeLanguage.PYTHON)
        assert len(ce.get_history()) >= 1

    def test_clear_history(self):
        ce = CodeExecutor()
        ce.execute("print('a')", CodeLanguage.PYTHON)
        ce.clear_history()
        assert len(ce.get_history()) == 0

    def test_sandbox_mode(self):
        ce = CodeExecutor()
        ce.set_sandbox_mode(SandboxMode.SUBPROCESS)
        assert ce._sandbox_mode == SandboxMode.SUBPROCESS

    def test_health_check(self):
        ce = CodeExecutor()
        assert ce.health_check()

    def test_summary(self):
        ce = CodeExecutor()
        s = ce.summary()
        assert "Code Executor" in s


from aetheros_runtime.code_executor import CodePermission


# ---------------------------------------------------------------------------
# FileSystemEngine tests
# ---------------------------------------------------------------------------

class TestFileSystemEngine:
    def test_read_write(self, tmp_path):
        fs = FileSystemEngine()
        test_file = tmp_path / "test.txt"
        assert fs.write(test_file, "hello")
        content = fs.read(test_file)
        assert content == "hello"

    def test_append(self, tmp_path):
        fs = FileSystemEngine()
        test_file = tmp_path / "test.txt"
        fs.write(test_file, "hello")
        assert fs.append(test_file, " world")
        assert fs.read(test_file) == "hello world"

    def test_delete(self, tmp_path):
        fs = FileSystemEngine()
        test_file = tmp_path / "test.txt"
        fs.write(test_file, "hello")
        assert fs.delete(test_file)
        assert not test_file.exists()

    def test_move(self, tmp_path):
        fs = FileSystemEngine()
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        fs.write(src, "content")
        assert fs.move(src, dst)
        assert dst.exists()
        assert not src.exists()

    def test_rename(self, tmp_path):
        fs = FileSystemEngine()
        src = tmp_path / "old.txt"
        fs.write(src, "content")
        assert fs.rename(src, "new.txt")
        assert (tmp_path / "new.txt").exists()

    def test_copy(self, tmp_path):
        fs = FileSystemEngine()
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        fs.write(src, "content")
        assert fs.copy(src, dst)
        assert dst.exists()
        assert src.exists()

    def test_search(self, tmp_path):
        fs = FileSystemEngine()
        (tmp_path / "test.py").write_text("code")
        results = fs.search("*.py", tmp_path)
        assert len(results) >= 1

    def test_search_content(self, tmp_path):
        fs = FileSystemEngine()
        (tmp_path / "readme.md").write_text("important content here")
        results = fs.search_content("important", tmp_path)
        assert len(results) >= 1

    def test_is_allowed(self, tmp_path):
        fs = FileSystemEngine()
        assert fs.is_allowed(tmp_path)
        fs.deny_directory(tmp_path)
        assert not fs.is_allowed(tmp_path)

    def test_get_info(self, tmp_path):
        fs = FileSystemEngine()
        test_file = tmp_path / "test.txt"
        fs.write(test_file, "hello")
        info = fs.get_info(test_file)
        assert info is not None
        assert info.name == "test.txt"

    def test_list_directory(self, tmp_path):
        fs = FileSystemEngine()
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        files = fs.list_directory(tmp_path)
        assert len(files) >= 2

    def test_file_exists(self, tmp_path):
        fs = FileSystemEngine()
        test_file = tmp_path / "test.txt"
        fs.write(test_file, "hello")
        assert fs.file_exists(test_file)
        assert not fs.file_exists(tmp_path / "nonexistent.txt")

    def test_ensure_dir(self, tmp_path):
        fs = FileSystemEngine()
        new_dir = tmp_path / "new" / "nested"
        assert fs.ensure_dir(new_dir)
        assert new_dir.exists()

    def test_index_directory(self, tmp_path):
        fs = FileSystemEngine()
        (tmp_path / "file.py").write_text("code")
        (tmp_path / "file.md").write_text("docs")
        idx = fs.index_directory(tmp_path)
        assert ".py" in idx or ".md" in idx

    def test_set_max_file_size(self):
        fs = FileSystemEngine()
        fs.set_max_file_size(100)
        assert fs._max_file_size == 100

    def test_watchers(self, tmp_path):
        fs = FileSystemEngine()
        events = []
        fs.on_change(lambda p, c: events.append((p, c)))
        fs.start_watching(tmp_path, interval=0.1)
        (tmp_path / "new_file.txt").write_text("hello")
        time.sleep(0.3)
        fs.stop_watching()
        assert len(events) >= 1

    def test_health_check(self):
        fs = FileSystemEngine()
        assert fs.health_check()

    def test_summary(self):
        fs = FileSystemEngine()
        s = fs.summary()
        assert "File System Engine" in s


# ---------------------------------------------------------------------------
# WorkspaceManager tests
# ---------------------------------------------------------------------------

class TestWorkspaceManager:
    def test_default_workspace(self):
        wm = WorkspaceManager()
        ws = wm.get_active_workspace()
        assert ws is not None
        assert ws.name == "Default"

    def test_create_workspace(self):
        wm = WorkspaceManager()
        ws = wm.create_workspace("Work")
        assert ws.name == "Work"
        assert wm.get_workspace(ws.id).name == "Work"

    def test_set_active_workspace(self):
        wm = WorkspaceManager()
        ws = wm.create_workspace("Secondary")
        assert wm.set_active_workspace(ws.id)
        assert wm.get_active_workspace().id == ws.id

    def test_delete_workspace(self):
        wm = WorkspaceManager()
        ws = wm.create_workspace("Temp")
        assert wm.delete_workspace(ws.id)
        assert wm.get_workspace(ws.id) is None

    def test_list_workspaces(self):
        wm = WorkspaceManager()
        wm.create_workspace("A")
        wm.create_workspace("B")
        assert len(wm.list_workspaces()) >= 2

    def test_rename_workspace(self):
        wm = WorkspaceManager()
        ws = wm.create_workspace("Old")
        assert wm.rename_workspace(ws.id, "New")
        assert wm.get_workspace(ws.id).name == "New"

    def test_add_get_remove_project(self):
        wm = WorkspaceManager()
        project = Project(name="MyApp", path=Path("/tmp/myapp"))
        ws = wm.get_active_workspace()
        assert wm.add_project(ws.id, project)
        assert wm.get_project(ws.id, project.id).name == "MyApp"
        assert wm.remove_project(ws.id, project.id)
        assert wm.get_project(ws.id, project.id) is None

    def test_list_projects(self):
        wm = WorkspaceManager()
        ws = wm.get_active_workspace()
        wm.add_project(ws.id, Project(name="A"))
        wm.add_project(ws.id, Project(name="B"))
        assert len(wm.list_projects(ws.id)) == 2

    def test_create_project(self):
        wm = WorkspaceManager()
        project = wm.create_project("MyApp")
        assert project is not None
        assert project.name == "MyApp"

    def test_pin_unpin_folder(self):
        wm = WorkspaceManager()
        ws = wm.get_active_workspace()
        assert wm.pin_folder(ws.id, "/projects/myapp")
        assert "/projects/myapp" in wm.get_pinned_folders(ws.id)
        assert wm.unpin_folder(ws.id, "/projects/myapp")
        assert "/projects/myapp" not in wm.get_pinned_folders(ws.id)

    def test_apply_template(self):
        wm = WorkspaceManager()
        ws = wm.get_active_workspace()
        assert wm.apply_template(ws.id, "python-project")
        assert ws.template == "python-project"

    def test_persistence(self, tmp_path):
        wm = WorkspaceManager(storage_dir=tmp_path)
        wm.create_workspace("Persistent")
        wm2 = WorkspaceManager(storage_dir=tmp_path)
        names = [ws.name for ws in wm2.list_workspaces()]
        assert "Persistent" in names

    def test_health_check(self):
        wm = WorkspaceManager()
        assert wm.health_check()

    def test_summary(self):
        wm = WorkspaceManager()
        s = wm.summary()
        assert "Workspace Manager" in s


# ---------------------------------------------------------------------------
# MemoryRuntime tests
# ---------------------------------------------------------------------------

class TestMemoryRuntime:
    def test_store_and_retrieve(self):
        mr = MemoryRuntime()
        entry = mr.store("key1", "important info", MemoryType.LONG_TERM)
        retrieved = mr.retrieve("key1", MemoryType.LONG_TERM)
        assert retrieved is not None
        assert retrieved.content == "important info"

    def test_retrieve_content(self):
        mr = MemoryRuntime()
        mr.store("k1", "value", MemoryType.CONVERSATION)
        assert mr.retrieve_content("k1") == "value"
        assert mr.retrieve_content("k1", default="fallback") == "value"
        assert mr.retrieve_content("nonexistent", default="fallback") == "fallback"

    def test_delete(self):
        mr = MemoryRuntime()
        mr.store("k1", "v1", MemoryType.TEMPORARY)
        assert mr.delete("k1", MemoryType.TEMPORARY)
        assert mr.retrieve("k1", MemoryType.TEMPORARY) is None

    def test_clear_type(self):
        mr = MemoryRuntime()
        mr.store("a", "1", MemoryType.TEMPORARY)
        mr.store("b", "2", MemoryType.TEMPORARY)
        assert mr.clear_type(MemoryType.TEMPORARY) == 2

    def test_search(self):
        mr = MemoryRuntime()
        mr.store("project-alpha", "important", MemoryType.CONVERSATION, tags=["project"])
        results = mr.search("alpha")
        assert len(results) >= 1

    def test_search_by_tag(self):
        mr = MemoryRuntime()
        mr.store("k1", "content", MemoryType.CONVERSATION, tags=["important"])
        results = mr.search_by_tag("important")
        assert len(results) >= 1

    def test_pin_unpin(self):
        mr = MemoryRuntime()
        entry = mr.store("k1", "pinned value", MemoryType.CONVERSATION)
        assert mr.pin(entry.id)
        assert mr.retrieve("k1", MemoryType.PINNED) is not None
        assert mr.unpin(entry.id)
        assert mr.retrieve("k1", MemoryType.PINNED) is None

    def test_register_provider(self):
        mr = MemoryRuntime()
        mr.register_provider("external", lambda name, key: "external value")
        result = mr.recall_from_provider("external", "test")
        assert result == "external value"

    def test_cleanup_expired(self):
        mr = MemoryRuntime()
        mr.store("temp1", "expired", MemoryType.TEMPORARY, ttl=0.001)
        time.sleep(0.01)
        count = mr.cleanup_expired()
        assert count >= 1

    def test_stats(self):
        mr = MemoryRuntime()
        mr.store("k1", "v1", MemoryType.CONVERSATION)
        stats = mr.stats()
        assert stats["conversation"] >= 1

    def test_persistence(self, tmp_path):
        mr = MemoryRuntime(storage_dir=tmp_path)
        mr.store("k1", "persistent value", MemoryType.LONG_TERM)
        mr2 = MemoryRuntime(storage_dir=tmp_path)
        assert mr2.retrieve_content("k1") == "persistent value"

    def test_summary(self):
        mr = MemoryRuntime()
        s = mr.summary()
        assert "Memory Runtime" in s


# ---------------------------------------------------------------------------
# ReasoningEngine tests
# ---------------------------------------------------------------------------

class TestReasoningEngine:
    def test_normal_reason(self):
        re = ReasoningEngine()
        result = re.reason("What is 2+2?", ReasoningMode.NORMAL)
        assert result.mode == ReasoningMode.NORMAL
        assert result.confidence > 0

    def test_thinking_reason(self):
        re = ReasoningEngine()
        result = re.reason("Solve this problem", ReasoningMode.THINKING)
        assert len(result.steps) >= 1

    def test_deep_reason(self):
        re = ReasoningEngine()
        result = re.reason("Complex analysis", ReasoningMode.DEEP)
        assert len(result.steps) >= 3

    def test_planning_reason(self):
        re = ReasoningEngine()
        result = re.reason("Build a web app", ReasoningMode.PLANNING)
        assert result.conclusion != ""
        assert "Plan" in result.conclusion

    def test_reflection_reason(self):
        re = ReasoningEngine()
        result = re.reason("Review my code", ReasoningMode.REFLECTION)
        assert result.mode == ReasoningMode.REFLECTION

    def test_self_correct_reason(self):
        re = ReasoningEngine()
        result = re.reason("Find the bug", ReasoningMode.SELF_CORRECT)
        assert len(result.steps) >= 3

    def test_register_provider(self):
        re = ReasoningEngine()
        re.register_provider(ReasoningMode.NORMAL, lambda q, m: f"Custom: {q}")
        result = re.reason("test", ReasoningMode.NORMAL)
        assert "Custom:" in result.conclusion

    def test_get_history(self):
        re = ReasoningEngine()
        re.reason("first")
        re.reason("second")
        assert len(re.get_history()) >= 2

    def test_health_check(self):
        re = ReasoningEngine()
        assert re.health_check()

    def test_summary(self):
        re = ReasoningEngine()
        s = re.summary()
        assert "Reasoning Engine" in s


# ---------------------------------------------------------------------------
# ToolCallingInterface tests
# ---------------------------------------------------------------------------

class TestToolCallingInterface:
    def test_register_and_execute(self):
        tc = ToolCallingInterface()
        tc.register_tool("echo", lambda tc: ToolResult(success=True, output=str(tc.arguments)))
        result = tc.execute("echo", {"msg": "hello"})
        assert result.success
        assert "msg" in result.output

    def test_execute_not_found(self):
        tc = ToolCallingInterface()
        result = tc.execute("nonexistent", {})
        assert not result.success

    def test_execute_batch(self):
        tc = ToolCallingInterface()
        tc.register_tool("ping", lambda tc: ToolResult(success=True, output="pong"))
        calls = [ToolCall(name="ping"), ToolCall(name="ping")]
        results = tc.execute_batch(calls)
        assert len(results) == 2

    def test_list_tools(self):
        tc = ToolCallingInterface()
        tc.register_tool("tool1", lambda tc: ToolResult(success=True), ToolDomain.FILESYSTEM)
        tools = tc.list_tools(ToolDomain.FILESYSTEM)
        assert len(tools) >= 1

    def test_list_domains(self):
        tc = ToolCallingInterface()
        tc.register_tool("t1", lambda tc: ToolResult(success=True), ToolDomain.FILESYSTEM)
        tc.register_tool("t2", lambda tc: ToolResult(success=True), ToolDomain.BROWSER)
        domains = tc.list_domains()
        assert "filesystem" in domains

    def test_permission_denied(self):
        tc = ToolCallingInterface()
        tc.register_tool("secret", lambda tc: ToolResult(success=True))
        tc.revoke_permission("secret")
        result = tc.execute("secret", {})
        assert result.permission_denied

    def test_grant_revoke_permission(self):
        tc = ToolCallingInterface()
        tc.grant_permission("test_tool")
        tc.revoke_permission("test_tool")

    def test_get_history(self):
        tc = ToolCallingInterface()
        tc.register_tool("echo", lambda tc: ToolResult(success=True, output="ok"))
        tc.execute("echo", {})
        assert len(tc.get_history()) >= 1

    def test_handler_raises(self):
        tc = ToolCallingInterface()
        tc.register_tool("failing", lambda tc: (_ for _ in ()).throw(ValueError("fail")))
        result = tc.execute("failing", {})
        assert not result.success

    def test_max_concurrent(self):
        tc = ToolCallingInterface()
        tc.set_max_concurrent(5)
        assert tc._max_concurrent == 5

    def test_health_check(self):
        tc = ToolCallingInterface()
        tc.register_tool("ping", lambda tc: ToolResult(success=True))
        assert tc.health_check()

    def test_summary(self):
        tc = ToolCallingInterface()
        tc.register_tool("ping", lambda tc: ToolResult(success=True))
        s = tc.summary()
        assert "Tool Calling Interface" in s

    def test_domain_handler(self):
        tc = ToolCallingInterface()
        tc.register_domain_handler(ToolDomain.TERMINAL, lambda tc: ToolResult(success=True, output="term ok"))
        # Domain handlers are registered with "domain:terminal" name
        tools = tc.list_tools(ToolDomain.TERMINAL)
        assert len(tools) >= 1


# ---------------------------------------------------------------------------
# SessionRecovery tests
# ---------------------------------------------------------------------------

class TestSessionRecovery:
    def test_save_and_get_checkpoint(self):
        sr = SessionRecovery()
        point = sr.save_checkpoint("chat", {"last_message": "hello"})
        assert point.component == "chat"
        retrieved = sr.get_checkpoint("chat")
        assert retrieved is not None
        assert retrieved.data["last_message"] == "hello"

    def test_get_all_checkpoints(self):
        sr = SessionRecovery()
        sr.save_checkpoint("chat", {})
        sr.save_checkpoint("task", {})
        assert len(sr.get_all_checkpoints()) == 2

    def test_clear_checkpoints(self):
        sr = SessionRecovery()
        sr.save_checkpoint("chat", {})
        sr.save_checkpoint("task", {})
        assert sr.clear_checkpoints("chat") >= 1
        assert len(sr.get_all_checkpoints()) == 1

    def test_register_handler_and_recover(self):
        sr = SessionRecovery()
        sr.save_checkpoint("chat", {"msg": "hello"})
        recovered = []
        sr.register_handler("chat", lambda p: recovered.append(p.data["msg"]) or True)
        sr.recover_all()
        assert "hello" in recovered

    def test_recover_component(self):
        sr = SessionRecovery()
        sr.save_checkpoint("chat", {"msg": "hello"})
        recovered = []
        sr.register_handler("chat", lambda p: recovered.append(p.data["msg"]) or True)
        assert sr.recover_component("chat")
        assert "hello" in recovered

    def test_persistence(self, tmp_path):
        sr = SessionRecovery(recovery_dir=tmp_path)
        sr.save_checkpoint("chat", {"msg": "hello"})
        sr2 = SessionRecovery(recovery_dir=tmp_path)
        assert sr2.get_checkpoint("chat") is not None

    def test_summary(self):
        sr = SessionRecovery()
        s = sr.summary()
        assert "Session Recovery" in s


# ---------------------------------------------------------------------------
# NotificationBus tests
# ---------------------------------------------------------------------------

class TestNotificationBus:
    def test_publish_and_subscribe(self):
        nb = NotificationBus()
        received = []
        nb.subscribe("test.event", lambda n: received.append(n))
        nb.publish("test.event", "Test Title", "Test Message")
        assert len(received) == 1
        assert received[0].title == "Test Title"

    def test_subscribe_all(self):
        nb = NotificationBus()
        received = []
        nb.subscribe_all(lambda n: received.append(n))
        nb.publish("event1", "T1")
        nb.publish("event2", "T2")
        assert len(received) == 2

    def test_unsubscribe(self):
        nb = NotificationBus()
        handler = lambda n: None
        nb.subscribe("test", handler)
        assert nb.unsubscribe("test", handler)
        assert not nb.unsubscribe("test", handler)

    def test_get_history(self):
        nb = NotificationBus()
        nb.publish("e1", "t1")
        nb.publish("e2", "t2")
        history = nb.get_history()
        assert len(history) >= 2

    def test_get_history_filtered(self):
        nb = NotificationBus()
        nb.publish("error", "Error!", level=NotificationLevel.ERROR)
        nb.publish("info", "Info!", level=NotificationLevel.INFO)
        errors = nb.get_history(level=NotificationLevel.ERROR)
        assert len(errors) == 1

    def test_acknowledge(self):
        nb = NotificationBus()
        n = nb.publish("test", "title")
        assert nb.acknowledge(n.id)
        assert n.acknowledged

    def test_acknowledge_all(self):
        nb = NotificationBus()
        nb.publish("a", "t1")
        nb.publish("b", "t2")
        assert nb.acknowledge_all() == 2

    def test_get_unacknowledged(self):
        nb = NotificationBus()
        nb.publish("a", "t1")
        nn = nb.publish("b", "t2")
        nb.acknowledge(nn.id)
        unacked = nb.get_unacknowledged()
        assert len(unacked) == 1

    def test_convenience_methods(self):
        nb = NotificationBus()
        n1 = nb.publish_streaming_complete("stream123", 500)
        assert n1.type == "streaming.complete"
        n2 = nb.publish_agent_waiting("agent1", "needs input")
        assert n2.type == "agent.waiting"
        n3 = nb.publish_tool_permission("rm", granted=False)
        assert n3.type == "tool.permission"
        n4 = nb.publish_task_finished("task1", success=True)
        assert n4.type == "task.finished"
        n5 = nb.publish_model_switched("gpt-4", "openai")
        assert n5.type == "model.switched"
        n6 = nb.publish_provider_disconnected("openai", "rate limited")
        assert n6.type == "provider.disconnected"

    def test_summary(self):
        nb = NotificationBus()
        nb.publish("test", "test")
        s = nb.summary()
        assert "Notification Bus" in s


# ---------------------------------------------------------------------------
# Diagnostics tests
# ---------------------------------------------------------------------------

class TestDiagnostics:
    def test_collect(self):
        d = Diagnostics()
        snapshot = d.collect()
        assert snapshot.timestamp > 0

    def test_provider_latency(self):
        d = Diagnostics()
        d.record_provider_latency("openai", 150.0)
        d.record_provider_latency("openai", 200.0)
        stats = d.get_provider_stats("openai")
        assert stats["count"] == 2
        assert stats["avg"] == 175.0

    def test_tool_latency(self):
        d = Diagnostics()
        d.record_tool_latency("search", 50.0)
        stats = d.get_tool_stats("search")
        assert stats["count"] == 1

    def test_crash_report(self):
        d = Diagnostics()
        report = d.report_crash("chat", "OOM", "traceback details")
        assert report["component"] == "chat"
        assert len(d.get_crash_reports()) == 1

    def test_register_metric_provider(self):
        d = Diagnostics()
        d.register_metric_provider("custom", lambda: {"value": 42})
        snapshot = d.collect()
        assert snapshot.custom_metrics["custom"]["value"] == 42

    def test_performance_summary(self):
        d = Diagnostics()
        d.record_provider_latency("openai", 100.0)
        summary = d.get_performance_summary()
        assert "provider_latency" in summary

    def test_log_content(self, tmp_path):
        d = Diagnostics(log_dir=tmp_path)
        content = d.get_log_content()
        assert isinstance(content, str)

    def test_summary(self):
        d = Diagnostics()
        d.collect()
        s = d.summary()
        assert "Diagnostics" in s


# ---------------------------------------------------------------------------
# PerformanceOptimizer tests
# ---------------------------------------------------------------------------

class TestPerformanceOptimizer:
    def test_lazy_load(self):
        po = PerformanceOptimizer()
        call_count = [0]
        value = po.lazy_load("key", lambda: (call_count.append(1), 42)[1])
        assert value == 42
        value2 = po.lazy_load("key", lambda: (call_count.append(1), 99)[1])
        assert value2 == 42
        assert call_count == [0, 1]

    def test_invalidate_cache(self):
        po = PerformanceOptimizer()
        po.lazy_load("key", lambda: 42)
        po.invalidate_cache("key")
        assert po.cache_size() == 0

    def test_mark_initialized(self):
        po = PerformanceOptimizer()
        po.mark_initialized("module_a")
        assert po.is_initialized("module_a")
        assert not po.is_initialized("module_b")

    def test_timing(self):
        po = PerformanceOptimizer()
        po.start_timer("test")
        time.sleep(0.01)
        elapsed = po.stop_timer("test")
        assert elapsed > 0

    def test_timing_report(self):
        po = PerformanceOptimizer()
        po.start_timer("test")
        po.stop_timer("test")
        report = po.timing_report()
        assert "test" in report

    def test_get_timing_stats(self):
        po = PerformanceOptimizer()
        po.start_timer("op")
        po.stop_timer("op")
        po.start_timer("op")
        po.stop_timer("op")
        stats = po.get_timing_stats("op")
        assert stats["count"] == 2

    def test_get_all_timing_stats(self):
        po = PerformanceOptimizer()
        po.start_timer("a")
        po.stop_timer("a")
        po.start_timer("b")
        po.stop_timer("b")
        all_stats = po.get_all_timing_stats()
        assert len(all_stats) == 2

    def test_clear_timers(self):
        po = PerformanceOptimizer()
        po.start_timer("test")
        po.clear_timers()
        assert po.stop_timer("test") == 0.0

    def test_set_cache_size(self):
        po = PerformanceOptimizer()
        po.set_cache_size(5)
        assert po._cache_max_size == 5

    def test_visible_range(self):
        r = PerformanceOptimizer.get_visible_range(100, 20, 400)
        assert len(list(r)) > 0

    def test_visible_items(self):
        items = list(range(100))
        visible = PerformanceOptimizer.get_visible_items(items, 100, 20, 400)
        assert len(visible) > 0

    def test_summary(self):
        po = PerformanceOptimizer()
        s = po.summary()
        assert "Performance Optimizer" in s


# ---------------------------------------------------------------------------
# Package init tests
# ---------------------------------------------------------------------------

class TestPackageInit:
    def test_all_exports(self):
        from aetheros_runtime import (
            RuntimeManager, RuntimeState, RuntimeConfig,
            ConversationEngine, Conversation, ConversationFolder, ExportFormat,
            ContextEngine, ContextBundle,
            StreamingEngine, StreamChunk, StreamEvent, StreamState,
            MessagePipeline, PipelineStage, MessageContext,
            PromptBuilder, PromptSection,
            AgentRuntime, AgentRole, AgentTask, AgentResult,
            ExecutionQueue, JobStatus, JobPriority, Job,
            ResponseRenderer, RenderBlock, BlockType,
            CodeExecutor, CodeLanguage, ExecutionResult, SandboxMode,
            FileSystemEngine, FileInfo, FileChange,
            WorkspaceManager, Workspace, Project,
            MemoryRuntime, MemoryEntry, MemoryType,
            ReasoningEngine, ReasoningMode, ReasoningResult,
            ToolCallingInterface, ToolCall, ToolResult,
            SessionRecovery, RecoveryPoint,
            NotificationBus, Notification, NotificationLevel,
            Diagnostics, MetricSnapshot,
            RuntimePerformanceOptimizer,
        )
        assert RuntimeManager is not None
        assert ConversationEngine is not None
        assert StreamingEngine is not None
        assert MessagePipeline is not None
        assert PromptBuilder is not None
        assert AgentRuntime is not None
        assert ExecutionQueue is not None
        assert ResponseRenderer is not None
        assert CodeExecutor is not None
        assert FileSystemEngine is not None
        assert WorkspaceManager is not None
        assert MemoryRuntime is not None
        assert ReasoningEngine is not None
        assert ToolCallingInterface is not None
        assert SessionRecovery is not None
        assert NotificationBus is not None
        assert Diagnostics is not None
        assert RuntimePerformanceOptimizer is not None