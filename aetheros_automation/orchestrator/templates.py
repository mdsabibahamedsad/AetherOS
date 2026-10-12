from __future__ import annotations

import logging
import time
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    TaskTemplate, TemplateCategory, PlanStep, AgentRole,
    RiskLevel, Objective, Plan,
)
from aetheros_automation.orchestrator.store import OrchestratorStore

logger = logging.getLogger(__name__)

_BUILTIN_TEMPLATES: list[TaskTemplate] = [
    TaskTemplate(
        name="Research Report",
        description="Research a topic and create a structured report",
        category=TemplateCategory.RESEARCH_REPORT,
        steps=[
            PlanStep(description="Research the topic", agent_role=AgentRole.RESEARCH,
                     tools=["web_search", "web_extract"], estimated_duration=120.0),
            PlanStep(description="Gather and organize findings", agent_role=AgentRole.DATA,
                     tools=["read_file", "write_file"], estimated_duration=60.0,
                     dependencies=["Research the topic"]),
            PlanStep(description="Generate the report", agent_role=AgentRole.CREATIVE,
                     tools=["write_file"], estimated_duration=60.0,
                     dependencies=["Gather and organize findings"]),
            PlanStep(description="Save and output the report", agent_role=AgentRole.FILE,
                     tools=["write_file"], estimated_duration=30.0,
                     dependencies=["Generate the report"]),
        ],
        required_tools=["web_search", "web_extract", "read_file", "write_file"],
        estimated_duration=300.0,
        estimated_cost=0.05,
        risk_level=RiskLevel.LOW,
        tags=["research", "report", "writing"],
        is_builtin=True,
    ),
    TaskTemplate(
        name="Software Development",
        description="Plan, code, test, and document a software project",
        category=TemplateCategory.SOFTWARE_DEV,
        steps=[
            PlanStep(description="Plan the architecture", agent_role=AgentRole.PLANNER,
                     estimated_duration=120.0),
            PlanStep(description="Implement the code", agent_role=AgentRole.CODING,
                     tools=["read_file", "write_file", "run_terminal"],
                     estimated_duration=600.0,
                     dependencies=["Plan the architecture"]),
            PlanStep(description="Test the implementation", agent_role=AgentRole.QA if hasattr(AgentRole, 'QA') else AgentRole.REVIEW,
                     tools=["run_terminal", "read_file"],
                     estimated_duration=120.0,
                     dependencies=["Implement the code"]),
            PlanStep(description="Review and document", agent_role=AgentRole.REVIEW,
                     tools=["read_file", "write_file"],
                     estimated_duration=60.0,
                     dependencies=["Test the implementation"]),
        ],
        required_tools=["read_file", "write_file", "run_terminal", "search_files"],
        required_permissions=["filesystem_write", "terminal"],
        estimated_duration=900.0,
        estimated_cost=0.15,
        risk_level=RiskLevel.MEDIUM,
        tags=["code", "development", "software"],
        is_builtin=True,
    ),
    TaskTemplate(
        name="Data Analysis",
        description="Collect, process, analyze and visualize data",
        category=TemplateCategory.DATA_ANALYSIS,
        steps=[
            PlanStep(description="Collect data", agent_role=AgentRole.RESEARCH,
                     tools=["web_search", "web_extract", "read_file"],
                     estimated_duration=120.0),
            PlanStep(description="Process and clean data", agent_role=AgentRole.DATA,
                     tools=["read_file", "write_file", "run_terminal"],
                     estimated_duration=180.0,
                     dependencies=["Collect data"]),
            PlanStep(description="Analyze the data", agent_role=AgentRole.DATA,
                     tools=["run_terminal", "read_file", "write_file"],
                     estimated_duration=180.0,
                     dependencies=["Process and clean data"]),
            PlanStep(description="Generate report", agent_role=AgentRole.CREATIVE,
                     tools=["write_file"],
                     estimated_duration=60.0,
                     dependencies=["Analyze the data"]),
        ],
        required_tools=["read_file", "write_file", "run_terminal", "web_search"],
        estimated_duration=540.0,
        estimated_cost=0.08,
        risk_level=RiskLevel.LOW,
        tags=["data", "analysis", "analytics"],
        is_builtin=True,
    ),
    TaskTemplate(
        name="Content Creation",
        description="Research, draft, and publish content",
        category=TemplateCategory.CONTENT_CREATION,
        steps=[
            PlanStep(description="Research the topic", agent_role=AgentRole.RESEARCH,
                     tools=["web_search", "web_extract"],
                     estimated_duration=120.0),
            PlanStep(description="Draft the content", agent_role=AgentRole.CREATIVE,
                     tools=["write_file"],
                     estimated_duration=180.0,
                     dependencies=["Research the topic"]),
            PlanStep(description="Review and refine", agent_role=AgentRole.REVIEW,
                     tools=["read_file", "write_file"],
                     estimated_duration=60.0,
                     dependencies=["Draft the content"]),
            PlanStep(description="Publish or save", agent_role=AgentRole.FILE,
                     tools=["write_file"],
                     estimated_duration=30.0,
                     dependencies=["Review and refine"]),
        ],
        required_tools=["web_search", "read_file", "write_file"],
        estimated_duration=390.0,
        estimated_cost=0.06,
        risk_level=RiskLevel.LOW,
        tags=["content", "writing", "creative"],
        is_builtin=True,
    ),
    TaskTemplate(
        name="Email Campaign",
        description="Plan, draft, review, and send an email campaign",
        category=TemplateCategory.EMAIL_CAMPAIGN,
        steps=[
            PlanStep(description="Plan the campaign", agent_role=AgentRole.PLANNER,
                     estimated_duration=60.0),
            PlanStep(description="Draft the email", agent_role=AgentRole.CREATIVE,
                     tools=["write_file"],
                     estimated_duration=120.0,
                     dependencies=["Plan the campaign"]),
            PlanStep(description="Review the draft", agent_role=AgentRole.REVIEW,
                     tools=["read_file"],
                     estimated_duration=30.0,
                     dependencies=["Draft the email"]),
            PlanStep(description="Send the campaign", agent_role=AgentRole.COMMUNICATION,
                     tools=["send_email"],
                     estimated_duration=30.0,
                     dependencies=["Review the draft"],
                     requires_approval=True),
        ],
        required_tools=["write_file", "read_file", "send_email"],
        required_permissions=["send_email"],
        estimated_duration=240.0,
        estimated_cost=0.04,
        risk_level=RiskLevel.MEDIUM,
        tags=["email", "campaign", "communication"],
        is_builtin=True,
    ),
    TaskTemplate(
        name="Business Automation",
        description="Automate a recurring business workflow",
        category=TemplateCategory.BUSINESS_AUTO,
        steps=[
            PlanStep(description="Analyze the workflow", agent_role=AgentRole.PLANNER,
                     estimated_duration=120.0),
            PlanStep(description="Build the automation", agent_role=AgentRole.CODING,
                     tools=["read_file", "write_file", "run_terminal"],
                     estimated_duration=600.0,
                     dependencies=["Analyze the workflow"]),
            PlanStep(description="Test the automation", agent_role=AgentRole.REVIEW,
                     tools=["run_terminal", "read_file"],
                     estimated_duration=120.0,
                     dependencies=["Build the automation"]),
            PlanStep(description="Deploy the automation", agent_role=AgentRole.COORDINATOR,
                     tools=[],
                     estimated_duration=60.0,
                     dependencies=["Test the automation"]),
        ],
        required_tools=["read_file", "write_file", "run_terminal"],
        required_permissions=["filesystem_write", "terminal"],
        estimated_duration=900.0,
        estimated_cost=0.15,
        risk_level=RiskLevel.MEDIUM,
        tags=["automation", "business", "workflow"],
        is_builtin=True,
    ),
    TaskTemplate(
        name="Personal Assistant",
        description="Handle personal tasks like scheduling, research, and comms",
        category=TemplateCategory.PERSONAL_ASSISTANT,
        steps=[
            PlanStep(description="Understand the request", agent_role=AgentRole.COORDINATOR,
                     estimated_duration=30.0),
            PlanStep(description="Gather needed information", agent_role=AgentRole.RESEARCH,
                     tools=["web_search"],
                     estimated_duration=60.0,
                     dependencies=["Understand the request"]),
            PlanStep(description="Execute the tasks", agent_role=AgentRole.COORDINATOR,
                     tools=["read_file", "write_file", "web_search"],
                     estimated_duration=180.0,
                     dependencies=["Gather needed information"]),
            PlanStep(description="Report results", agent_role=AgentRole.COMMUNICATION,
                     tools=[],
                     estimated_duration=30.0,
                     dependencies=["Execute the tasks"]),
        ],
        required_tools=["web_search", "read_file", "write_file"],
        estimated_duration=300.0,
        estimated_cost=0.05,
        risk_level=RiskLevel.LOW,
        tags=["personal", "assistant", "tasks"],
        is_builtin=True,
    ),
]


class TemplateManager:
    def __init__(self, store: OrchestratorStore):
        self.store = store
        self._templates: dict[str, TaskTemplate] = {}
        self._load_builtins()

    def _load_builtins(self):
        for template in _BUILTIN_TEMPLATES:
            self._templates[template.id] = template

    def register_template(self, template: TaskTemplate):
        self._templates[template.id] = template
        self.store.save_template(template)
        logger.info("Registered template: %s", template.name)

    def get_template(self, template_id: str) -> Optional[TaskTemplate]:
        return self._templates.get(template_id)

    def list_templates(
        self, category: Optional[TemplateCategory] = None
    ) -> list[TaskTemplate]:
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return sorted(templates, key=lambda t: t.name)

    def list_categories(self) -> list[dict]:
        categories = []
        for cat in TemplateCategory:
            count = len([
                t for t in self._templates.values() if t.category == cat
            ])
            categories.append({
                "id": cat.value,
                "name": cat.name.replace("_", " ").title(),
                "count": count,
            })
        return categories

    def create_from_template(
        self,
        template_id: str,
        variables: Optional[dict] = None,
    ) -> Optional[Plan]:
        template = self.get_template(template_id)
        if not template:
            return None
        vars_dict = variables or {}
        steps = []
        for step in template.steps:
            resolved_step = PlanStep(
                description=step.description,
                agent_role=step.agent_role,
                tools=list(step.tools),
                dependencies=list(step.dependencies),
                estimated_duration=step.estimated_duration,
                estimated_cost=step.estimated_cost,
                risk_level=step.risk_level,
                requires_approval=step.requires_approval,
            )
            steps.append(resolved_step)
        goal = vars_dict.get("goal", template.name)
        plan = Plan(
            goal=goal,
            steps=steps,
            required_tools=list(template.required_tools),
            required_permissions=list(template.required_permissions),
            estimated_time=template.estimated_duration,
            estimated_cost=template.estimated_cost,
            risk_level=template.risk_level,
            metadata={"template_id": template.id, "template_name": template.name},
        )
        return plan

    def delete_template(self, template_id: str) -> bool:
        template = self._templates.get(template_id)
        if template and template.is_builtin:
            return False
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def increment_usage(self, template_id: str):
        template = self._templates.get(template_id)
        if template:
            template.usage_count += 1

    def get_stats(self) -> dict:
        return {
            "total_templates": len(self._templates),
            "builtin": len([t for t in self._templates.values() if t.is_builtin]),
            "custom": len([t for t in self._templates.values() if not t.is_builtin]),
            "categories": len(TemplateCategory),
        }
