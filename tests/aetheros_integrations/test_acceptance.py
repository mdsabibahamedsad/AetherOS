"""Acceptance tests for aetheros_integrations — full platform + end-to-end workflow.

Covers the IntegrationPlatform facade, a realistic cross-provider workflow
(gmail summarize -> notion save -> github issue -> telegram notify -> memory)
using locally registered fake providers, plus the webhook -> workflow bridge.
"""

import pytest

from aetheros_integrations.config import IntegrationsSettings
from aetheros_integrations.models import (
    AuthMethod,
    HealthStatus,
    IntegrationCategory,
    ProviderDefinition,
)
from aetheros_integrations.providers.base import BaseProvider, register_provider


# --- fake providers for the acceptance flow -----------------------------


class _FakeGmail(BaseProvider):
    definition = ProviderDefinition(
        key="fake_gmail",
        category=IntegrationCategory.EMAIL,
        display_name="Fake Gmail",
        auth_method=AuthMethod.OAUTH2,
        capabilities=["read_messages", "send_message"],
    )

    def ping(self) -> HealthStatus:
        return HealthStatus.HEALTHY

    def read_messages(self, **kwargs):
        return [{"id": "msg-1", "subject": "Q3 report", "body": "sk-testsecretvalue123456", "cursor": "c1"}]


class _FakeNotion(BaseProvider):
    definition = ProviderDefinition(
        key="fake_notion",
        category=IntegrationCategory.KNOWLEDGE,
        display_name="Fake Notion",
        auth_method=AuthMethod.OAUTH2,
        capabilities=["create_record", "search_documents"],
    )

    def ping(self) -> HealthStatus:
        return HealthStatus.HEALTHY

    def create_record(self, **kwargs):
        return {"id": "page-1", "title": kwargs.get("title", "")}


class _FakeGithub(BaseProvider):
    definition = ProviderDefinition(
        key="fake_github",
        category=IntegrationCategory.DEVOPS,
        display_name="Fake GitHub",
        auth_method=AuthMethod.PAT,
        capabilities=["create_issue"],
    )

    def ping(self) -> HealthStatus:
        return HealthStatus.HEALTHY

    def create_issue(self, **kwargs):
        return {"number": 42, "title": kwargs.get("title", "")}


class _FakeTelegram(BaseProvider):
    definition = ProviderDefinition(
        key="fake_telegram",
        category=IntegrationCategory.MESSAGING,
        display_name="Fake Telegram",
        auth_method=AuthMethod.BEARER,
        capabilities=["send_message"],
    )

    def ping(self) -> HealthStatus:
        return HealthStatus.HEALTHY

    def send_message(self, **kwargs):
        return {"message_id": 7, "chat": kwargs.get("channel", "")}


@pytest.fixture(autouse=True)
def _register_fakes():
    register_provider(_FakeGmail)
    register_provider(_FakeNotion)
    register_provider(_FakeGithub)
    register_provider(_FakeTelegram)


@pytest.fixture
def platform(tmp_path):
    from aetheros_integrations import IntegrationPlatform

    settings = IntegrationsSettings(data_dir="integrations", auto_enable_on_install=True)
    platform = IntegrationPlatform(settings, dirpath=tmp_path)
    yield platform
    platform.stop()


class TestPlatformFacade:
    def test_status_shape(self, platform):
        status = platform.status()
        assert status["version"]
        assert status["installed_integrations"] >= 0
        assert status["webhook_stats"]["total"] >= 0
        assert status["event_stats"]["total"] >= 0
        assert status["scheduled_jobs"] >= 0
        assert "monitor_summary" in status

    def test_install_provider_convenience(self, platform):
        inst = platform.install_provider("fake_gmail", label="my gmail")
        assert inst.provider_key == "fake_gmail"

    def test_start_stop_does_not_crash(self, platform):
        platform.start()
        platform.stop()


class TestAcceptanceFlow:
    def test_gmail_to_github_to_telegram_to_memory(self, platform):
        # 1. Install + enable the four providers.
        gmail = platform.manager.install("fake_gmail", label="gmail")
        notion = platform.manager.install("fake_notion", label="notion")
        github = platform.manager.install("fake_github", label="github")
        telegram = platform.manager.install("fake_telegram", label="telegram")

        # 2. Define the workflow: read email -> summarize (transform) ->
        #    save to notion -> create github issue -> notify telegram -> memory.
        from aetheros_integrations.workflow import WorkflowBuilder

        wf = (
            WorkflowBuilder(name="Email digest pipeline", description="acceptance")
            .trigger("email.received", trigger_type="event")
            .variables({"channel": "ops"})
            .step("tool", "Read email", provider="fake_gmail", action="read_messages", params={"integration_id": gmail.id})
            .step("transform", "Summarize", params={"expression": '"summary: " + "Q3 report"'})
            .step("tool", "Save to notion", provider="fake_notion", action="create_record", params={"integration_id": notion.id, "args": {"title": "Q3 summary"}})
            .step("tool", "Create issue", provider="fake_github", action="create_issue", params={"integration_id": github.id, "args": {"title": "Review Q3 report"}})
            .step("notify", "Notify team", params={"integration_id": telegram.id, "channel": "{{channel}}", "message": "Pipeline done for {{channel}}"})
            .step("memory", "Remember", params={"key": "last_digest", "content": "digest ran"})
            .build()
        )
        platform.workflow_engine.register(wf)

        # 3. Trigger via the event bus (the workflow subscribes to email.received).
        platform.event_bus.publish("email.received", {"from": "billing@corp.example"}, dedup_key="acc-email-1")
        run = platform.workflow_engine.list_runs(wf.id)[0]
        assert run.status == "success"

        results = {r["step"]: r["result"] for r in run.step_results}
        assert results["read_email"][0]["subject"] == "Q3 report"
        assert results["save_to_notion"]["id"] == "page-1"
        assert results["create_issue"]["number"] == 42
        assert results["notify_team"]["message_id"] == 7

        # 4. Step results must not leak the secret in the email body.
        rendered = str(run.to_dict())
        assert "sk-testsecretvalue123456" not in rendered

        # 5. Memory step persisted.
        from aetheros_integrations.context import IntegrationMemory

        mem = IntegrationMemory(dirpath=platform._dir)
        assert mem.get("last_digest")["content"] == "digest ran"

        # 6. Monitor recorded workflow completion.
        summary = platform.monitor.summary(wf.id)
        assert summary["samples"] >= 1

    def test_approval_gate_denies(self, platform):
        from aetheros_integrations.workflow import WorkflowBuilder

        telegram = platform.manager.install("fake_telegram", label="tg")
        wf = (
            WorkflowBuilder(name="Needs approval", description="d")
            .trigger("manual", trigger_type="manual")
            .step("approval", "Confirm", params={"approval_key": "broadcast"})
            .step("notify", "Broadcast", params={"integration_id": telegram.id, "channel": "all", "message": "hello everyone"})
            .build()
        )
        platform.workflow_engine.register(wf)
        run = platform.workflow_engine.trigger(wf.id, {})
        assert run.status == "cancelled"

    def test_webhook_bridges_to_workflow(self, platform):
        from aetheros_integrations.workflow import WorkflowBuilder

        wf = (
            WorkflowBuilder(name="Webhook handler", description="d")
            .trigger("manual", trigger_type="manual")
            .step("transform", "Echo", params={"expression": '_webhook.kind == "ping"'})
            .build()
        )
        platform.workflow_engine.register(wf)
        platform.on_webhook("https://hooks.example.in/ingest", wf.id)

        import json

        from aetheros_integrations.webhooks import sign_payload

        body = json.dumps({"kind": "ping"}).encode()
        sig = sign_payload(platform.webhooks.secret, body)
        platform.webhooks.handle_incoming(body, signature=sig, event="webhook.ping")

        runs = platform.workflow_engine.list_runs(wf.id)
        assert len(runs) == 1
        assert runs[0].status == "success"

    def test_scheduler_workflow_executor(self, platform):
        from aetheros_integrations.workflow import WorkflowBuilder

        wf = (
            WorkflowBuilder(name="Scheduled job", description="d")
            .trigger("manual", trigger_type="manual")
            .step("transform", "Run", params={"expression": "1"})
            .build()
        )
        platform.workflow_engine.register(wf)
        job = platform.scheduler.create("daily digest job", f"workflow:{wf.id}", schedule_type="daily")
        result = platform.scheduler.run_now(job.id)
        assert result.status == "success"
