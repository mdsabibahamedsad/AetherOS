from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    AgentRole, AgentDefinition, AgentInstance, AgentLimits,
)

logger = logging.getLogger(__name__)


ROLE_DEFINITIONS: dict[AgentRole, AgentDefinition] = {
    AgentRole.RESEARCH: AgentDefinition(
        role=AgentRole.RESEARCH,
        name="Research Agent",
        description="Searches for and gathers information from various sources",
        tools=["web_search", "web_extract", "read_file", "search_files"],
        permissions=["network"],
        instructions="Find accurate, up-to-date information. Cite sources and verify facts.",
        personality="Thorough, curious, detail-oriented",
        temperature=0.4,
    ),
    AgentRole.CODING: AgentDefinition(
        role=AgentRole.CODING,
        name="Coding Agent",
        description="Writes, debugs, and improves code across languages",
        tools=["read_file", "write_file", "run_terminal", "search_files", "patch", "execute_code"],
        permissions=["filesystem_read", "filesystem_write", "terminal"],
        instructions="Write clean, efficient, well-structured code. Follow best practices.",
        personality="Precise, logical, methodical",
        temperature=0.3,
    ),
    AgentRole.BROWSER: AgentDefinition(
        role=AgentRole.BROWSER,
        name="Browser Agent",
        description="Navigates web pages and extracts information",
        tools=["browser_navigate", "browser_click", "browser_extract", "browser_screenshot", "web_search"],
        permissions=["browser", "network"],
        instructions="Navigate the web efficiently. Extract relevant data.",
        personality="Fast, efficient, focused",
        temperature=0.5,
    ),
    AgentRole.FILE: AgentDefinition(
        role=AgentRole.FILE,
        name="File Agent",
        description="Manages files, directories, and data storage",
        tools=["read_file", "write_file", "file_operations", "search_files"],
        permissions=["filesystem_read", "filesystem_write"],
        instructions="Handle files carefully. Do not overwrite existing data without confirmation.",
        personality="Organized, careful, systematic",
        temperature=0.3,
    ),
    AgentRole.DATA: AgentDefinition(
        role=AgentRole.DATA,
        name="Data Agent",
        description="Processes, analyzes, and transforms data",
        tools=["read_file", "write_file", "run_terminal", "search_files", "execute_code"],
        permissions=["filesystem_read", "filesystem_write", "terminal"],
        instructions="Process data accurately. Validate results.",
        personality="Analytical, precise, thorough",
        temperature=0.3,
    ),
    AgentRole.COMMUNICATION: AgentDefinition(
        role=AgentRole.COMMUNICATION,
        name="Communication Agent",
        description="Sends messages, emails, and notifications",
        tools=["send_message", "send_email"],
        permissions=["network"],
        instructions="Communicate professionally and clearly. Respect privacy.",
        personality="Professional, clear, courteous",
        temperature=0.6,
    ),
    AgentRole.PLANNER: AgentDefinition(
        role=AgentRole.PLANNER,
        name="Planning Agent",
        description="Creates and organizes execution plans",
        tools=[],
        permissions=[],
        instructions="Break down complex goals into clear, actionable steps.",
        personality="Strategic, organized, foresightful",
        temperature=0.5,
    ),
    AgentRole.REVIEW: AgentDefinition(
        role=AgentRole.REVIEW,
        name="Review Agent",
        description="Reviews code, documents, and results quality",
        tools=["read_file", "search_files", "run_terminal"],
        permissions=["filesystem_read"],
        instructions="Review thoroughly. Check for errors, security issues, and quality.",
        personality="Critical, thorough, balanced",
        temperature=0.3,
    ),
    AgentRole.SECURITY: AgentDefinition(
        role=AgentRole.SECURITY,
        name="Security Agent",
        description="Audits security, validates permissions, ensures safety",
        tools=["read_file", "search_files", "run_terminal"],
        permissions=["filesystem_read", "security"],
        instructions="Identify security risks. Validate permissions. Do not bypass security.",
        personality="Vigilant, cautious, principled",
        temperature=0.2,
    ),
    AgentRole.CREATIVE: AgentDefinition(
        role=AgentRole.CREATIVE,
        name="Creative Agent",
        description="Generates creative content, designs, and ideas",
        tools=["read_file", "write_file", "image_generation"],
        permissions=["filesystem_write"],
        instructions="Be creative while meeting requirements. Think outside the box.",
        personality="Creative, imaginative, expressive",
        temperature=0.8,
    ),
    AgentRole.COORDINATOR: AgentDefinition(
        role=AgentRole.COORDINATOR,
        name="Coordinator Agent",
        description="Coordinates other agents and manages workflows",
        tools=["delegate_task"],
        permissions=["filesystem_read", "network"],
        instructions="Coordinate effectively. Delegate tasks appropriately.",
        personality="Organized, communicative, decisive",
        temperature=0.5,
    ),
    AgentRole.COORDINATOR: AgentDefinition(
        role=AgentRole.COORDINATOR,
        name="General Agent",
        description="Versatile agent capable of handling various tasks",
        tools=["read_file", "write_file", "run_terminal", "web_search", "search_files"],
        permissions=["filesystem_read", "filesystem_write", "network"],
        instructions="Handle tasks efficiently and accurately.",
        personality="Adaptable, capable, reliable",
        temperature=0.5,
    ),
}


class AgentManager:
    def __init__(self):
        self._definitions: dict[AgentRole, AgentDefinition] = dict(ROLE_DEFINITIONS)
        self._instances: dict[str, AgentInstance] = {}
        self._role_instances: dict[AgentRole, list[str]] = {
            role: [] for role in AgentRole
        }

    def register_definition(self, definition: AgentDefinition):
        self._definitions[definition.role] = definition
        logger.info("Registered agent definition: %s", definition.name)

    def get_definition(self, role: AgentRole) -> Optional[AgentDefinition]:
        return self._definitions.get(role)

    def list_definitions(self) -> list[AgentDefinition]:
        return list(self._definitions.values())

    def spawn_agent(
        self,
        role: AgentRole,
        task_id: str = "",
        parent_id: str = "",
        overrides: Optional[dict] = None,
    ) -> Optional[AgentInstance]:
        definition = self.get_definition(role)
        if not definition:
            logger.warning("No definition for role %s", role)
            return None
        instance = AgentInstance(
            id=f"agent_{uuid.uuid4().hex[:12]}",
            definition=definition,
            parent_id=parent_id,
            status="idle",
            current_task_id=task_id,
            started_at=time.time(),
        )
        self._instances[instance.id] = instance
        if role in self._role_instances:
            self._role_instances[role].append(instance.id)
        logger.info("Spawned agent %s (%s)", instance.id, definition.name)
        return instance

    def get_agent(self, agent_id: str) -> Optional[AgentInstance]:
        return self._instances.get(agent_id)

    def get_agent_for_role(self, role: AgentRole) -> Optional[AgentInstance]:
        instance_ids = self._role_instances.get(role, [])
        for aid in instance_ids:
            inst = self._instances.get(aid)
            if inst and inst.status == "idle":
                return inst
        return None

    def update_agent_status(self, agent_id: str, status: str):
        agent = self._instances.get(agent_id)
        if agent:
            agent.status = status
            if status in ("completed", "failed", "terminated"):
                agent.completed_at = time.time()

    def terminate_agent(self, agent_id: str) -> bool:
        agent = self._instances.get(agent_id)
        if agent:
            agent.status = "terminated"
            agent.completed_at = time.time()
            role_list = self._role_instances.get(agent.definition.role, [])
            if agent_id in role_list:
                role_list.remove(agent_id)
            return True
        return False

    def list_active_agents(self) -> list[AgentInstance]:
        return [
            a for a in self._instances.values()
            if a.status in ("idle", "running", "busy")
        ]

    def list_agents_by_role(self, role: AgentRole) -> list[AgentInstance]:
        return [
            self._instances[aid] for aid in self._role_instances.get(role, [])
            if aid in self._instances
        ]

    def get_agent_stats(self) -> dict:
        total = len(self._instances)
        active = len(self.list_active_agents())
        by_role: dict[str, int] = {}
        for a in self._instances.values():
            role = a.definition.role.value if hasattr(a.definition.role, 'value') else str(a.definition.role)
            by_role[role] = by_role.get(role, 0) + 1
        return {
            "total": total,
            "active": active,
            "by_role": by_role,
        }
