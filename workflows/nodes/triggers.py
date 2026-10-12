"""Trigger nodes — manual, schedule, cron, webhook, and event-based triggers."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from workflows.nodes.base import BaseNode, NodeRegistry, NodeResult
from workflows.models import WorkflowNode, WorkflowConfig

logger = logging.getLogger(__name__)


class ManualTriggerNode(BaseNode):
    type = "trigger.manual"
    category = "trigger"
    label = "Manual Trigger"
    description = "Start workflow manually from CLI or UI"
    default_config = {}
    inputs = []
    outputs = [{"id": "output", "label": "Triggered", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        return NodeResult(success=True, output={
            "trigger": "manual",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
        })


class ScheduleTriggerNode(BaseNode):
    type = "trigger.schedule"
    category = "trigger"
    label = "Schedule Trigger"
    description = "Trigger on a recurring schedule"
    default_config = {"interval": "60m"}
    inputs = []
    outputs = [{"id": "output", "label": "Triggered", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        schedule = node.config.get("schedule") or workflow.schedule or node.config.get("interval", "60m")
        return NodeResult(success=True, output={
            "trigger": "schedule",
            "schedule": schedule,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })


class CronTriggerNode(BaseNode):
    type = "trigger.cron"
    category = "trigger"
    label = "Cron Trigger"
    description = "Trigger on a cron expression"
    default_config = {"cron": "0 * * * *"}
    inputs = []
    outputs = [{"id": "output", "label": "Triggered", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        cron_expr = node.config.get("cron", "0 * * * *")
        return NodeResult(success=True, output={
            "trigger": "cron",
            "cron": cron_expr,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })


class WebhookTriggerNode(BaseNode):
    type = "trigger.webhook"
    category = "trigger"
    label = "Webhook Trigger"
    description = "Trigger via incoming webhook"
    default_config = {"path": "/webhook/workflow"}
    inputs = []
    outputs = [{"id": "output", "label": "Payload", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        payload = context.get("webhook_payload", {})
        return NodeResult(success=True, output={
            "trigger": "webhook",
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })


class FileTriggerNode(BaseNode):
    type = "trigger.file_created"
    category = "trigger"
    label = "File Created"
    description = "Trigger when a file is created or modified"
    default_config = {"path": "", "pattern": "*"}
    inputs = []
    outputs = [{"id": "output", "label": "File Info", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        file_info = context.get("file_event", {})
        return NodeResult(success=True, output={
            "trigger": "file_created",
            "file": file_info,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })


class GitHubTriggerNode(BaseNode):
    type = "trigger.github"
    category = "trigger"
    label = "GitHub Webhook"
    description = "Trigger on GitHub events (push, PR, issues)"
    default_config = {"event": "push", "repo": ""}
    inputs = []
    outputs = [{"id": "output", "label": "Event", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        event = context.get("github_event", {})
        return NodeResult(success=True, output={
            "trigger": "github",
            "event": event,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })


def register():
    NodeRegistry.register(ManualTriggerNode)
    NodeRegistry.register(ScheduleTriggerNode)
    NodeRegistry.register(CronTriggerNode)
    NodeRegistry.register(WebhookTriggerNode)
    NodeRegistry.register(FileTriggerNode)
    NodeRegistry.register(GitHubTriggerNode)


register()
