from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from aetheros_automation.models.models import AgentRole, GraphExecutionMode, RiskLevel
from aetheros_automation.orchestrator.types import OrchestrationPlan, OrchestrationTask

logger = logging.getLogger(__name__)

_TEMPLATES: dict[str, dict[str, Any]] = {
    "research_report": {
        "name": "Research Report",
        "description": "Research a topic, collect data, and generate a report",
        "category": "research",
        "default_params": {"topic": "", "depth": "comprehensive", "format": "markdown"},
        "tasks": [
            {"name": "Research Topic", "role": "research", "tools": ["web_search"], "duration": 120.0},
            {"name": "Collect Data", "role": "research", "tools": ["web_search", "file_operations"], "duration": 60.0},
            {"name": "Analyze Findings", "role": "data", "tools": ["data_analysis"], "duration": 120.0},
            {"name": "Write Report", "role": "writer", "tools": ["file_operations"], "duration": 180.0},
            {"name": "Review Report", "role": "review", "tools": [], "duration": 60.0},
        ],
    },
    "software_development": {
        "name": "Software Development",
        "description": "Plan, implement, test, and deploy software",
        "category": "development",
        "default_params": {"project_name": "", "language": "python", "description": ""},
        "tasks": [
            {"name": "Plan Architecture", "role": "planner", "tools": [], "duration": 300.0},
            {"name": "Implement Code", "role": "developer", "tools": ["code_execution", "terminal", "file_operations"], "duration": 600.0},
            {"name": "Write Tests", "role": "qa", "tools": ["code_execution", "terminal"], "duration": 300.0},
            {"name": "Review Code", "role": "review", "tools": [], "duration": 120.0},
            {"name": "Build & Deploy", "role": "deployment", "tools": ["terminal"], "duration": 180.0},
        ],
    },
    "data_analysis": {
        "name": "Data Analysis",
        "description": "Analyze data, create visualizations, and generate insights",
        "category": "data",
        "default_params": {"data_source": "", "analysis_type": "exploratory", "output_format": "report"},
        "tasks": [
            {"name": "Load Data", "role": "data", "tools": ["file_operations", "code_execution"], "duration": 60.0},
            {"name": "Clean Data", "role": "data", "tools": ["code_execution"], "duration": 120.0},
            {"name": "Analyze Data", "role": "data", "tools": ["code_execution", "data_analysis"], "duration": 300.0},
            {"name": "Create Visualizations", "role": "creative", "tools": ["code_execution"], "duration": 180.0},
            {"name": "Generate Report", "role": "writer", "tools": ["file_operations"], "duration": 120.0},
        ],
    },
    "content_creation": {
        "name": "Content Creation",
        "description": "Create content including writing, images, and formatting",
        "category": "creative",
        "default_params": {"topic": "", "content_type": "article", "format": "markdown"},
        "tasks": [
            {"name": "Research Topic", "role": "research", "tools": ["web_search"], "duration": 120.0},
            {"name": "Outline Content", "role": "planner", "tools": [], "duration": 60.0},
            {"name": "Write Content", "role": "writer", "tools": ["file_operations"], "duration": 300.0},
            {"name": "Create Visuals", "role": "creative", "tools": ["image_generation"], "duration": 180.0},
            {"name": "Review & Polish", "role": "review", "tools": [], "duration": 120.0},
        ],
    },
    "email_campaign": {
        "name": "Email Campaign",
        "description": "Plan, write, and send an email campaign",
        "category": "communication",
        "default_params": {"recipients": "", "subject": "", "message": ""},
        "tasks": [
            {"name": "Plan Campaign", "role": "planner", "tools": [], "duration": 120.0},
            {"name": "Write Email Content", "role": "writer", "tools": ["file_operations"], "duration": 180.0},
            {"name": "Review Content", "role": "review", "tools": [], "duration": 60.0},
            {"name": "Send Campaign", "role": "communication", "tools": ["send_message"], "duration": 60.0, "approval": True},
        ],
    },
    "business_automation": {
        "name": "Business Automation",
        "description": "Automate business workflows and processes",
        "category": "automation",
        "default_params": {"process": "", "schedule": "", "actions": []},
        "tasks": [
            {"name": "Analyze Process", "role": "planner", "tools": [], "duration": 180.0},
            {"name": "Design Workflow", "role": "planner", "tools": [], "duration": 300.0},
            {"name": "Implement Automation", "role": "developer", "tools": ["code_execution", "file_operations"], "duration": 600.0},
            {"name": "Test Automation", "role": "qa", "tools": ["terminal"], "duration": 180.0},
            {"name": "Deploy Automation", "role": "deployment", "tools": ["terminal"], "duration": 120.0},
        ],
    },
    "personal_assistant": {
        "name": "Personal Assistant",
        "description": "Handle personal tasks and scheduling",
        "category": "productivity",
        "default_params": {"task": "", "schedule": "", "details": ""},
        "tasks": [
            {"name": "Understand Request", "role": "coordinator", "tools": [], "duration": 30.0},
            {"name": "Gather Information", "role": "research", "tools": ["web_search"], "duration": 120.0},
            {"name": "Execute Task", "role": "coordinator", "tools": ["file_operations", "terminal"], "duration": 180.0},
            {"name": "Confirm Completion", "role": "review", "tools": [], "duration": 30.0},
        ],
    },
}


class TaskTemplateManager:
    def __init__(self):
        self._templates: dict[str, dict[str, Any]] = dict(_TEMPLATES)

    def list_templates(self) -> list[dict[str, Any]]:
        return [
            {"id": tid, "name": t["name"], "description": t["description"], "category": t["category"]}
            for tid, t in self._templates.items()
        ]

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        return self._templates.get(template_id)

    def get_templates_by_category(self, category: str) -> list[dict[str, Any]]:
        return [
            {"id": tid, **t} for tid, t in self._templates.items()
            if t.get("category") == category
        ]

    def add_template(self, template_id: str, template: dict[str, Any]):
        self._templates[template_id] = template
        logger.info("Template '%s' added", template_id)

    def remove_template(self, template_id: str):
        self._templates.pop(template_id, None)
        logger.info("Template '%s' removed", template_id)

    async def apply_template(
        self,
        template: dict[str, Any],
        params: dict[str, Any],
    ) -> OrchestrationPlan:
        plan = OrchestrationPlan(
            id=uuid.uuid4().hex[:12],
            goal=template["description"],
            created_at=time.time(),
        )

        param_topic = params.get("topic", params.get("project_name", params.get("task", "task")))

        for task_def in template.get("tasks", []):
            task = OrchestrationTask(
                id=uuid.uuid4().hex[:12],
                name=task_def["name"],
                description=f"{task_def['name']} for {param_topic}",
                agent_role=AgentRole(task_def["role"]),
                tools=list(task_def.get("tools", [])),
                estimated_duration=task_def.get("duration", 60.0),
                created_at=time.time(),
            )
            if task_def.get("approval"):
                task.requires_approval = True
            plan.subtasks.append(task)

        for i in range(1, len(plan.subtasks)):
            plan.subtasks[i].dependencies.append(plan.subtasks[i - 1].id)

        plan.estimated_time = sum(t.estimated_duration for t in plan.subtasks)
        plan.estimated_cost = len(plan.subtasks) * 0.01
        plan.risk_level = RiskLevel.LOW

        return plan

    def get_template_count(self) -> int:
        return len(self._templates)
