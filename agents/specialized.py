"""
Specialized Agent Implementations for AetherOS Intelligence Engine.

Defines the 13 specialized agent roles with their capabilities,
default configurations, and coordination interfaces.

Agents:
    - Planner: Task planning and goal decomposition
    - Researcher: Multi-source research and synthesis
    - Coder: Code generation and implementation
    - Reviewer: Code review and quality assurance
    - Debugger: Debugging and issue resolution
    - Tester: Test generation and execution
    - Writer: Technical writing and documentation
    - Browser: Web browsing and automation
    - Automation Agent: Workflow automation
    - Security Agent: Security monitoring and audits
    - Knowledge Agent: Knowledge management and search
    - Voice Agent: Voice interaction and processing
    - Coordinator: Agent orchestration and coordination
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SpecializedAgentRole(str, Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    DEBUGGER = "debugger"
    TESTER = "tester"
    WRITER = "writer"
    BROWSER = "browser"
    AUTOMATION = "automation"
    SECURITY = "security"
    KNOWLEDGE = "knowledge"
    VOICE = "voice"
    COORDINATOR = "coordinator"


SPECIALIZED_AGENT_DEFINITIONS = {
    SpecializedAgentRole.PLANNER: {
        "name": "Planner",
        "description": "Task planning and goal decomposition specialist",
        "icon": "\U0001f9e9",
        "color": "#818cf8",
        "capabilities": [
            "Hierarchical goal decomposition",
            "Task dependency analysis",
            "Long-term plan management",
            "Priority assignment",
            "Effort estimation",
            "Plan refinement",
        ],
        "toolsets": ["planning", "reasoning", "memory"],
        "recommended_model": "gpt-4o",
    },
    SpecializedAgentRole.RESEARCHER: {
        "name": "Researcher",
        "description": "Multi-source research and synthesis specialist",
        "icon": "\U0001f50d",
        "color": "#34d399",
        "capabilities": [
            "Web search and extraction",
            "Documentation analysis",
            "GitHub exploration",
            "Knowledge base queries",
            "Research report synthesis",
            "Deep recursive research",
        ],
        "toolsets": ["search", "web", "knowledge", "files"],
        "recommended_model": "claude-3.5-sonnet",
    },
    SpecializedAgentRole.CODER: {
        "name": "Coder",
        "description": "Code generation and implementation specialist",
        "icon": "\U0001f4bb",
        "color": "#60a5fa",
        "capabilities": [
            "Code generation across languages",
            "Implementation from specifications",
            "API integration",
            "Refactoring",
            "Cross-file changes",
            "Code optimization",
        ],
        "toolsets": ["code_execution", "file", "terminal"],
        "recommended_model": "codestral",
    },
    SpecializedAgentRole.REVIEWER: {
        "name": "Reviewer",
        "description": "Code review and quality assurance specialist",
        "icon": "\u2705",
        "color": "#fbbf24",
        "capabilities": [
            "Code quality analysis",
            "Security vulnerability detection",
            "Performance issue identification",
            "Style compliance checking",
            "Architecture review",
            "Best practice enforcement",
        ],
        "toolsets": ["debugging", "file", "search"],
        "recommended_model": "gpt-4o",
    },
    SpecializedAgentRole.DEBUGGER: {
        "name": "Debugger",
        "description": "Debugging and issue resolution specialist",
        "icon": "\U0001f41b",
        "color": "#f87171",
        "capabilities": [
            "Root cause analysis",
            "Stack trace interpretation",
            "Log analysis",
            "Reproduction steps",
            "Fix implementation",
            "Regression testing",
        ],
        "toolsets": ["debugging", "terminal", "code_execution"],
        "recommended_model": "deepseek-reasoner",
    },
    SpecializedAgentRole.TESTER: {
        "name": "Tester",
        "description": "Test generation and execution specialist",
        "icon": "\U0001f9ea",
        "color": "#a78bfa",
        "capabilities": [
            "Test case generation",
            "Unit test creation",
            "Integration test design",
            "Test coverage analysis",
            "Test execution",
            "Regression test suites",
        ],
        "toolsets": ["code_execution", "file", "terminal"],
        "recommended_model": "gpt-4o-mini",
    },
    SpecializedAgentRole.WRITER: {
        "name": "Writer",
        "description": "Technical writing and documentation specialist",
        "icon": "\U0001f4dd",
        "color": "#f472b6",
        "capabilities": [
            "Documentation generation",
            "API documentation",
            "README and guides",
            "Release notes",
            "Technical blog posts",
            "Code comments",
        ],
        "toolsets": ["file", "search", "web"],
        "recommended_model": "claude-3.5-sonnet",
    },
    SpecializedAgentRole.BROWSER: {
        "name": "Browser",
        "description": "Web browsing and automation specialist",
        "icon": "\U0001f310",
        "color": "#2dd4bf",
        "capabilities": [
            "Web navigation",
            "Form filling",
            "Data extraction",
            "Web scraping",
            "Session management",
            "Screenshot capture",
        ],
        "toolsets": ["browser", "web", "search"],
        "recommended_model": "gpt-4o",
    },
    SpecializedAgentRole.AUTOMATION: {
        "name": "Automation Agent",
        "description": "Workflow automation specialist",
        "icon": "\u2699\ufe0f",
        "color": "#fb923c",
        "capabilities": [
            "Workflow optimization",
            "Repetitive task automation",
            "Pipeline creation",
            "Scheduled job management",
            "Integration setup",
            "Monitoring configuration",
        ],
        "toolsets": ["cronjob", "terminal", "file"],
        "recommended_model": "gpt-4o-mini",
    },
    SpecializedAgentRole.SECURITY: {
        "name": "Security Agent",
        "description": "Security monitoring and audits specialist",
        "icon": "\U0001f6e1\ufe0f",
        "color": "#dc2626",
        "capabilities": [
            "Vulnerability scanning",
            "Security audit",
            "Dependency checking",
            "Secret detection",
            "Access control review",
            "Compliance checking",
        ],
        "toolsets": ["debugging", "search", "terminal"],
        "recommended_model": "gpt-4o",
    },
    SpecializedAgentRole.KNOWLEDGE: {
        "name": "Knowledge Agent",
        "description": "Knowledge management and search specialist",
        "icon": "\U0001f4da",
        "color": "#a855f7",
        "capabilities": [
            "Knowledge graph queries",
            "Semantic search",
            "Document organization",
            "Entity linking",
            "Knowledge synthesis",
            "Information retrieval",
        ],
        "toolsets": ["knowledge", "search", "memory", "file"],
        "recommended_model": "claude-3-haiku",
    },
    SpecializedAgentRole.VOICE: {
        "name": "Voice Agent",
        "description": "Voice interaction and processing specialist",
        "icon": "\U0001f399\ufe0f",
        "color": "#38bdf8",
        "capabilities": [
            "Speech-to-text",
            "Text-to-speech",
            "Voice command processing",
            "Natural conversation",
            "Interrupt handling",
            "Multi-turn dialogue",
        ],
        "toolsets": ["tts", "search", "memory"],
        "recommended_model": "gpt-4o-mini",
    },
    SpecializedAgentRole.COORDINATOR: {
        "name": "Coordinator",
        "description": "Agent orchestration and coordination specialist",
        "icon": "\U0001f916",
        "color": "#e879f9",
        "capabilities": [
            "Agent selection and routing",
            "Execution ordering",
            "Parallel task coordination",
            "Retry strategy management",
            "Fallback planning",
            "Cost optimization across agents",
        ],
        "toolsets": ["delegation", "memory", "search"],
        "recommended_model": "gpt-4o",
    },
}


def get_specialized_agent_def(role: str) -> Optional[Dict[str, Any]]:
    """Get the definition for a specialized agent role."""
    try:
        return SPECIALIZED_AGENT_DEFINITIONS.get(SpecializedAgentRole(role))
    except (ValueError, KeyError):
        return None


def list_specialized_agents() -> List[Dict[str, Any]]:
    """List all available specialized agent definitions."""
    return [
        {
            "role": role.value,
            "name": defn["name"],
            "description": defn["description"],
            "icon": defn["icon"],
            "color": defn["color"],
            "capabilities": defn["capabilities"],
            "recommended_model": defn["recommended_model"],
        }
        for role, defn in SPECIALIZED_AGENT_DEFINITIONS.items()
    ]


# ---------------------------------------------------------------------------
# Coordinator - decides which agent runs, execution order, etc.
# ---------------------------------------------------------------------------

@dataclass
class AgentTaskAssignment:
    agent_role: str
    task_description: str
    priority: int = 0
    parallel_with: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2
    fallback_agent: str = ""
    estimated_cost: float = 0.0
    status: str = "pending"


class Coordinator:
    """Intelligence coordinator that decides agent execution strategy.

    Determines:
    - Which agent(s) to run for a given task
    - Execution order (serial vs parallel)
    - Retry and fallback strategies
    - Cost optimization across agents

    Usage::

        coord = Coordinator()
        plan = coord.plan_execution("Fix the login bug")
        # plan.agent_assignments contains the ordered task list
    """

    def __init__(self) -> None:
        self._history: List[Dict[str, Any]] = []

    def plan_execution(self, goal: str,
                       context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Plan which agents should execute a given goal.

        Analyzes the goal and creates an execution plan with
        assigned agents, ordering, and strategies.
        """
        goal_lower = goal.lower()
        assignments = []

        domain_agents = self._map_goal_to_agents(goal_lower)

        for i, (role, task_desc) in enumerate(domain_agents):
            assignment = AgentTaskAssignment(
                agent_role=role,
                task_description=task_desc,
                priority=i,
                max_retries=2,
            )
            if i > 0:
                assignment.depends_on = [domain_agents[i - 1][0]]
            assignments.append(assignment)

        plan = self._build_execution_plan(assignments, goal)
        self._history.append({
            "goal": goal[:100],
            "agent_count": len(assignments),
            "timestamp": __import__("time").time(),
        })

        return plan

    def _map_goal_to_agents(self, goal: str) -> List[tuple]:
        """Map a goal to the appropriate agent roles."""
        agent_map = [
            (SpecializedAgentRole.PLANNER, "plan the task and decompose the goal"),
            (SpecializedAgentRole.RESEARCHER, "research the topic and gather information"),
            (SpecializedAgentRole.CODER, "implement the solution"),
            (SpecializedAgentRole.TESTER, "write and run tests"),
            (SpecializedAgentRole.REVIEWER, "review the implementation for quality"),
            (SpecializedAgentRole.DEBUGGER, "debug any issues found"),
            (SpecializedAgentRole.WRITER, "document the implementation"),
        ]

        role_keywords = {
            SpecializedAgentRole.PLANNER: ["plan", "organize", "strategy", "roadmap"],
            SpecializedAgentRole.RESEARCHER: ["research", "investigate", "find", "learn", "search"],
            SpecializedAgentRole.CODER: ["implement", "code", "build", "create", "write", "develop"],
            SpecializedAgentRole.REVIEWER: ["review", "audit", "check", "inspect"],
            SpecializedAgentRole.DEBUGGER: ["debug", "fix", "repair", "bug", "issue", "error"],
            SpecializedAgentRole.TESTER: ["test", "verify", "validate", "assert"],
            SpecializedAgentRole.WRITER: ["document", "write", "explain", "describe"],
            SpecializedAgentRole.BROWSER: ["browse", "web", "website", "url", "http"],
            SpecializedAgentRole.AUTOMATION: ["automate", "pipeline", "workflow", "schedule"],
            SpecializedAgentRole.SECURITY: ["secure", "security", "vulnerability", "protect"],
            SpecializedAgentRole.KNOWLEDGE: ["knowledge", "learn", "memory", "recall"],
            SpecializedAgentRole.COORDINATOR: ["coordinate", "orchestrate", "manage"],
        }

        matched = []
        for role, keywords in role_keywords.items():
            if any(kw in goal for kw in keywords):
                task = " and ".join([
                    k for k in SPECIALIZED_AGENT_DEFINITIONS[role]["capabilities"]
                    if any(kw in k.lower() for kw in keywords)
                ]) or agent_map[0][1]
                matched.append((role.value, task))

        if not matched:
            return [(role.value, desc) for role, desc in agent_map[:3]]

        return matched

    def _build_execution_plan(self, assignments: List[AgentTaskAssignment],
                              goal: str) -> Dict[str, Any]:
        """Build a structured execution plan from assignments."""
        parallel_groups = []
        current_group = []

        for i, assignment in enumerate(assignments):
            current_group.append({
                "agent_role": assignment.agent_role,
                "task": assignment.task_description,
                "priority": assignment.priority,
                "max_retries": assignment.max_retries,
                "fallback_agent": assignment.fallback_agent,
            })
            if (i + 1) % 2 == 0 or i == len(assignments) - 1:
                parallel_groups.append(current_group)
                current_group = []

        if current_group:
            parallel_groups.append(current_group)

        return {
            "goal": goal[:200],
            "agent_count": len(assignments),
            "execution_plan": [
                {
                    "group_id": gid,
                    "agents": group,
                    "execution": "parallel" if len(group) > 1 else "serial",
                }
                for gid, group in enumerate(parallel_groups)
            ],
            "total_groups": len(parallel_groups),
            "strategy": {
                "retry": "exponential_backoff",
                "max_retries": 2,
                "fallback": "next_available_agent",
                "cost_optimization": True,
            },
        }

    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution plans."""
        return list(reversed(self._history[-limit:]))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_executions": len(self._history),
            "total_agent_roles": len(SPECIALIZED_AGENT_DEFINITIONS),
            "agents": [r.value for r in SpecializedAgentRole],
        }
