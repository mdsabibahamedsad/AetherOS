"""Workflow marketplace — catalog, import/export, share, and install workflows."""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aetheros_constants import get_aetheros_home
from workflows.store import WorkflowStore
from workflows.models import WorkflowConfig, WorkflowNode, Connection, WorkflowStatus

logger = logging.getLogger(__name__)


MARKETPLACE_WORKFLOWS: list[dict] = [
    {
        "id": "wf_daily_report",
        "name": "Daily Report Generator",
        "description": "Generate a daily report with web research and AI summarization",
        "category": "reporting",
        "author": "Aetheros",
        "version": "1.0.0",
        "tags": ["report", "daily", "automation"],
        "nodes": [
            {"type": "trigger.schedule", "config": {"schedule": "0 8 * * *"}},
            {"type": "action.web_search", "config": {"num_results": 10}},
            {"type": "ai.summarize", "config": {}},
            {"type": "action.file_write", "config": {"path": "daily_report.md"}},
        ],
    },
    {
        "id": "wf_code_review",
        "name": "Code Review Pipeline",
        "description": "Automated code review with AI analysis and notifications",
        "category": "development",
        "author": "Aetheros",
        "version": "1.1.0",
        "tags": ["code", "review", "ci"],
        "nodes": [
            {"type": "trigger.github", "config": {"event": "pull_request"}},
            {"type": "ai.review_code", "config": {}},
            {"type": "action.notify", "config": {"channel": "slack"}},
        ],
    },
    {
        "id": "wf_research_assistant",
        "name": "Research Assistant",
        "description": "Deep research workflow with multi-source synthesis",
        "category": "research",
        "author": "Aetheros",
        "version": "1.0.0",
        "tags": ["research", "synthesis", "analysis"],
        "nodes": [
            {"type": "trigger.manual", "config": {}},
            {"type": "ai.research", "config": {"depth": "deep"}},
            {"type": "action.file_write", "config": {"path": "research_report.md"}},
        ],
    },
    {
        "id": "wf_bug_fix",
        "name": "Bug Fix Pipeline",
        "description": "Analyze bug reports, reproduce, fix, and verify",
        "category": "development",
        "author": "Aetheros",
        "version": "1.0.0",
        "tags": ["bug", "fix", "qa"],
        "nodes": [
            {"type": "trigger.manual", "config": {}},
            {"type": "ai.reasoning", "config": {}},
            {"type": "agent.pipeline", "config": {"agents": ["developer", "tester"]}},
            {"type": "ai.review_code", "config": {}},
        ],
    },
    {
        "id": "wf_content_writer",
        "name": "Content Writer",
        "description": "Research, draft, edit, and publish content",
        "category": "content",
        "author": "Aetheros",
        "version": "1.0.0",
        "tags": ["content", "writing", "publishing"],
        "nodes": [
            {"type": "trigger.manual", "config": {}},
            {"type": "ai.chat", "config": {}},
            {"type": "action.web_search", "config": {}},
            {"type": "ai.summarize", "config": {}},
            {"type": "action.file_write", "config": {}},
        ],
    },
    {
        "id": "wf_data_pipeline",
        "name": "Data Pipeline",
        "description": "Extract, transform, and load data from multiple sources",
        "category": "data",
        "author": "Aetheros",
        "version": "1.0.0",
        "tags": ["data", "etl", "pipeline"],
        "nodes": [
            {"type": "trigger.schedule", "config": {"schedule": "0 */6 * * *"}},
            {"type": "action.http", "config": {}},
            {"type": "action.database", "config": {}},
            {"type": "action.file_write", "config": {}},
        ],
    },
]


class WorkflowMarketplace:
    def __init__(self, store: Optional[WorkflowStore] = None):
        self.store = store or WorkflowStore()

    def get_catalog(self, category: str = None) -> list[dict]:
        if category:
            return [w for w in MARKETPLACE_WORKFLOWS if w.get("category") == category]
        return list(MARKETPLACE_WORKFLOWS)

    def get_categories(self) -> list[str]:
        cats = set()
        for w in MARKETPLACE_WORKFLOWS:
            cats.add(w.get("category", "uncategorized"))
        return sorted(cats)

    def get_workflow_info(self, marketplace_id: str) -> Optional[dict]:
        for w in MARKETPLACE_WORKFLOWS:
            if w["id"] == marketplace_id:
                return w
        return None

    def install_from_marketplace(self, marketplace_id: str,
                                 name: str = None) -> Optional[str]:
        info = self.get_workflow_info(marketplace_id)
        if not info:
            logger.error("Marketplace workflow not found: %s", marketplace_id)
            return None
        wf = WorkflowConfig(
            name=name or info["name"],
            description=info.get("description", ""),
            tags=info.get("tags", []),
            version=info.get("version", "1.0.0"),
            author=info.get("author", "Aetheros"),
            nodes=[],
            connections=[],
        )
        x, y = 100, 100
        prev_id = None
        for i, ndef in enumerate(info.get("nodes", [])):
            nid = f"{info['id']}_node_{i}"
            wf.nodes.append(WorkflowNode(
                id=nid, type=ndef["type"],
                label=ndef.get("label", ndef["type"]),
                config=ndef.get("config", {}),
                position={"x": x, "y": y},
            ))
            if prev_id:
                wf.connections.append(Connection(
                    source_id=prev_id, target_id=nid,
                    source_output="output", target_input="input",
                ))
            prev_id = nid
            x += 300
        saved = self.store.save_workflow(wf)
        logger.info("Installed marketplace workflow: %s (id=%s)", wf.name, saved.id)
        return saved.id

    def export_workflow(self, workflow_id: str, output_path: str = None) -> str:
        wf = self.store.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")
        export_data = {
            "format": "aetheros-workflow-v1",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "workflow": {
                "name": wf.name,
                "description": wf.description,
                "version": wf.version,
                "author": wf.author,
                "tags": list(wf.tags),
                "schedule": wf.schedule,
                "nodes": [n.to_dict() for n in wf.nodes],
                "connections": [c.to_dict() for c in wf.connections],
            },
        }
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            return output_path
        return json.dumps(export_data, indent=2)

    def import_workflow(self, source: str) -> Optional[str]:
        if os.path.isfile(source):
            with open(source, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json.loads(source)
        if data.get("format") != "aetheros-workflow-v1":
            raise ValueError("Unknown format")
        wd = data["workflow"]
        wf = WorkflowConfig(
            name=wd["name"],
            description=wd.get("description", ""),
            version=wd.get("version", "1.0.0"),
            author=wd.get("author", "Imported"),
            tags=wd.get("tags", []),
            schedule=wd.get("schedule", ""),
            nodes=[WorkflowNode(**n) if isinstance(n, dict)
                   else n for n in wd.get("nodes", [])],
            connections=[Connection(**c) if isinstance(c, dict)
                         else c for c in wd.get("connections", [])],
        )
        saved = self.store.save_workflow(wf)
        logger.info("Imported workflow: %s", saved.name)
        return saved.id

    def share_export(self, workflow_id: str) -> str:
        return self.export_workflow(workflow_id)

    def get_local_workflows(self) -> list[WorkflowConfig]:
        return self.store.list_workflows()
