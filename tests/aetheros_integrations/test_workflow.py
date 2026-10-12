"""Tests for aetheros_integrations.workflow — builder, executor, engine."""

import time

import pytest

from aetheros_integrations.models import WorkflowDefinition, WorkflowStep
from aetheros_integrations.workflow import WorkflowBuilder, WorkflowEngine


@pytest.fixture
def manager(tmp_path):
    from aetheros_integrations.config import IntegrationsSettings
    from aetheros_integrations.manager import IntegrationManager

    settings = IntegrationsSettings(data_dir="integrations")
    mgr = IntegrationManager(settings, dirpath=tmp_path)
    return mgr


@pytest.fixture
def engine(tmp_path, manager):
    eng = WorkflowEngine(manager, dirpath=tmp_path)
    yield eng
    eng.close()


class TestWorkflowBuilder:
    def test_build_definition(self):
        wf = (
            WorkflowBuilder(name="Daily digest", description="test")
            .trigger("daily.digest", trigger_type="event")
            .variables({"email": "ops@example.com"})
            .step("notify", "Send notify", provider="telegram", action="send_message", params={"channel": "ops", "message": "Digest ready for {{email}}"})
            .build()
        )
        assert wf.name == "Daily digest"
        assert wf.trigger_type == "event"
        assert wf.variables["email"] == "ops@example.com"
        assert len(wf.steps) == 1
        assert wf.steps[0].id == "send_notify"

    def test_unique_step_ids(self):
        wf = WorkflowBuilder().step("transform", "First").step("transform", "First").build()
        ids = [s.id for s in wf.steps]
        assert ids[0] != ids[1]


class TestWorkflowEngine:
    def test_register_and_trigger_success(self, engine):
        wf = (
            WorkflowBuilder(name="Simple", description="d")
            .trigger("manual", trigger_type="manual")
            .step("transform", "Hello", params={"expression": '"hi" == "hi"'})
            .build()
        )
        engine.register(wf)
        run = engine.trigger(wf.id, {})
        assert run.status == "success"
        assert run.step_results[0]["result"]["value"] is True

    def test_condition_false_breaks(self, engine):
        wf = (
            WorkflowBuilder(name="Cond", description="d")
            .trigger("manual", trigger_type="manual")
            .step("transform", "Set flag", params={"expression": "True"})
            .step("condition", "Gate", condition='flag == "no"')
            .build()
        )
        engine.register(wf)
        run = engine.trigger(wf.id, {"flag": "no"})
        assert run.status == "success"
        assert len(run.step_results) == 2  # stopped at the false condition

    def test_condition_passes_continues(self, engine):
        wf = (
            WorkflowBuilder(name="CondPass", description="d")
            .trigger("manual", trigger_type="manual")
            .step("condition", "Gate", condition='flag == "yes"')
            .step("transform", "After", params={"expression": "flag"})
            .build()
        )
        engine.register(wf)
        run = engine.trigger(wf.id, {"flag": "yes"})
        assert run.status == "success"
        assert len(run.step_results) == 2

    def test_approval_denied_by_default_cancels(self, engine):
        wf = (
            WorkflowBuilder(name="Approval", description="d")
            .trigger("manual", trigger_type="manual")
            .step("approval", "Approve", params={"approval_key": "risk"})
            .step("transform", "Never", params={"expression": "1"})
            .build()
        )
        engine.register(wf)
        run = engine.trigger(wf.id, {})
        assert run.status == "cancelled"
        assert len(run.step_results) == 1

    def test_approval_resolver_approves(self, engine):
        engine.set_approval_resolver(lambda run, key: key == "risk")
        wf = (
            WorkflowBuilder(name="Approval2", description="d")
            .trigger("manual", trigger_type="manual")
            .step("approval", "Approve", params={"approval_key": "risk"})
            .step("transform", "Runs", params={"expression": "1"})
            .build()
        )
        engine.register(wf)
        run = engine.trigger(wf.id, {})
        assert run.status == "success"
        assert len(run.step_results) == 2

    def test_failing_step_fails_run(self, engine):
        wf = (
            WorkflowBuilder(name="Fail", description="d")
            .trigger("manual", trigger_type="manual")
            .step("tool", "Bad", provider="nonexistent", action="x")
            .build()
        )
        engine.register(wf)
        run = engine.trigger(wf.id, {})
        assert run.status == "failed"
        assert run.error

    def test_loop_step(self, engine):
        wf = (
            WorkflowBuilder(name="Loop", description="d")
            .trigger("manual", trigger_type="manual")
            .step("loop", "Iterate", loop_over="items")
            .build()
        )
        engine.register(wf)
        run = engine.trigger(wf.id, {"items": ["a", "b", "c"]})
        assert run.status == "success"
        result = run.step_results[0]["result"]
        assert result["iterations"] == 3
        assert result["items"][1]["_loop_index"] == 1

    def test_unknown_step_type_fails(self, engine):
        wf = WorkflowDefinition(
            name="BadType",
            trigger="manual",
            trigger_type="manual",
            steps=[WorkflowStep(id="s1", type="wat", name="x")],
        )
        engine.register(wf)
        run = engine.trigger(wf.id, {})
        assert run.status == "failed"
        assert "Unknown step type" in run.error

    def test_list_and_get(self, engine):
        wf = WorkflowBuilder(name="L", description="d").trigger("manual", trigger_type="manual").build()
        engine.register(wf)
        assert len(engine.list_workflows()) == 1
        assert engine.get_workflow(wf.id).name == "L"

    def test_unregister(self, engine):
        wf = WorkflowBuilder(name="U", description="d").trigger("manual", trigger_type="manual").build()
        engine.register(wf)
        assert engine.unregister(wf.id) is True
        assert engine.unregister(wf.id) is False

    def test_emit_workflow_completed_event(self, tmp_path, manager):
        from aetheros_integrations.events import EventBus

        bus = EventBus(dirpath=tmp_path)
        eng = WorkflowEngine(manager, event_bus=bus, dirpath=tmp_path)
        received = []

        def handler(envelope):
            received.append(envelope)

        bus.subscribe("workflow.completed", handler)
        wf = WorkflowBuilder(name="Emit", description="d").trigger("manual", trigger_type="manual").build()
        eng.register(wf)
        eng.trigger(wf.id, {})
        assert len(received) == 1
        assert received[0].data["status"] == "success"
        eng.close()


class TestSanitize:
    def test_step_results_redact_secrets(self, engine):
        wf = (
            WorkflowBuilder(name="Secret", description="d")
            .trigger("manual", trigger_type="manual")
            .step("transform", "Leak", params={"expression": '"api_key=sk-testsecret1234567890"'})
            .build()
        )
        engine.register(wf)
        run = engine.trigger(wf.id, {})
        assert run.status == "success"
        rendered = run.to_dict()
        assert "sk-testsecret1234567890" not in str(rendered)
