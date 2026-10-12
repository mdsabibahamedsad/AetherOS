"""Starter workflow templates — pre-built DAGs for common automation patterns."""

from __future__ import annotations

from typing import Optional

from workflows.models import WorkflowNode, Connection

TEMPLATES: list[dict] = [
    {
        "id": "daily_report",
        "name": "Daily Report",
        "description": "Generate a daily report with web research and AI summarization",
        "schedule": "0 8 * * *",
        "nodes": [
            WorkflowNode(id="t1", type="trigger.cron", label="Morning Trigger",
                         config={"cron": "0 8 * * *"},
                         position={"x": 50, "y": 200}),
            WorkflowNode(id="n1", type="action.web_search", label="Search News",
                         config={"num_results": 8},
                         position={"x": 400, "y": 200}),
            WorkflowNode(id="n2", type="ai.summarize", label="Summarize",
                         config={"max_length": 1000},
                         position={"x": 750, "y": 200}),
            WorkflowNode(id="n3", type="action.file_write", label="Save Report",
                         config={"path": "reports/daily_report.md"},
                         position={"x": 1100, "y": 200}),
        ],
        "connections": [
            Connection(source_id="t1", target_id="n1",
                       source_output="output", target_input="input"),
            Connection(source_id="n1", target_id="n2",
                       source_output="output", target_input="input"),
            Connection(source_id="n2", target_id="n3",
                       source_output="output", target_input="input"),
        ],
    },
    {
        "id": "research_assistant",
        "name": "Research Assistant",
        "description": "Deep research workflow with multi-source synthesis",
        "nodes": [
            WorkflowNode(id="t1", type="trigger.manual", label="Start Research",
                         config={}, position={"x": 50, "y": 200}),
            WorkflowNode(id="n1", type="ai.research", label="Research Topic",
                         config={"depth": "deep"},
                         position={"x": 350, "y": 200}),
            WorkflowNode(id="n2", type="ai.chat", label="Draft Report",
                         config={"system_prompt": "Write a comprehensive research report"},
                         position={"x": 700, "y": 200}),
            WorkflowNode(id="n3", type="action.file_write", label="Save",
                         config={"path": "research/output.md"},
                         position={"x": 1050, "y": 200}),
        ],
        "connections": [
            Connection(source_id="t1", target_id="n1"),
            Connection(source_id="n1", target_id="n2"),
            Connection(source_id="n2", target_id="n3"),
        ],
    },
    {
        "id": "code_review",
        "name": "Code Review Pipeline",
        "description": "Automated code review with AI analysis",
        "nodes": [
            WorkflowNode(id="t1", type="trigger.github", label="PR Trigger",
                         config={"event": "pull_request"},
                         position={"x": 50, "y": 200}),
            WorkflowNode(id="n1", type="ai.review_code", label="Review Code",
                         config={}, position={"x": 350, "y": 200}),
            WorkflowNode(id="n2", type="action.notify", label="Notify Team",
                         config={"channel": "slack"},
                         position={"x": 700, "y": 200}),
            WorkflowNode(id="n3", type="action.file_write", label="Save Review",
                         config={"path": "reviews/{timestamp}.md"},
                         position={"x": 700, "y": 400}),
        ],
        "connections": [
            Connection(source_id="t1", target_id="n1"),
            Connection(source_id="n1", target_id="n2"),
            Connection(source_id="n1", target_id="n3"),
        ],
    },
    {
        "id": "bug_fix",
        "name": "Bug Fix Pipeline",
        "description": "Analyze, fix, and verify bug reports",
        "nodes": [
            WorkflowNode(id="t1", type="trigger.manual", label="Bug Report",
                         config={}, position={"x": 50, "y": 200}),
            WorkflowNode(id="n1", type="ai.reasoning", label="Analyze Bug",
                         config={}, position={"x": 350, "y": 200}),
            WorkflowNode(id="n2", type="agent.delegate", label="Fix Bug",
                         config={"agent_name": "developer", "goal": "Fix the reported bug"},
                         position={"x": 700, "y": 200}),
            WorkflowNode(id="n3", type="ai.review_code", label="Verify Fix",
                         config={}, position={"x": 1050, "y": 200}),
            WorkflowNode(id="n4", type="action.notify", label="Report Status",
                         config={"channel": "email"},
                         position={"x": 1400, "y": 200}),
        ],
        "connections": [
            Connection(source_id="t1", target_id="n1"),
            Connection(source_id="n1", target_id="n2"),
            Connection(source_id="n2", target_id="n3"),
            Connection(source_id="n3", target_id="n4"),
        ],
    },
    {
        "id": "content_writer",
        "name": "Content Writer",
        "description": "Research, draft, edit, and publish content",
        "nodes": [
            WorkflowNode(id="t1", type="trigger.manual", label="New Content",
                         config={}, position={"x": 50, "y": 200}),
            WorkflowNode(id="n1", type="action.web_search", label="Research",
                         config={"num_results": 5},
                         position={"x": 350, "y": 200}),
            WorkflowNode(id="n2", type="ai.chat", label="Draft",
                         config={"system_prompt": "Write engaging content based on research"},
                         position={"x": 700, "y": 200}),
            WorkflowNode(id="n3", type="ai.summarize", label="Edit",
                         config={}, position={"x": 1050, "y": 200}),
            WorkflowNode(id="n4", type="action.file_write", label="Publish",
                         config={"path": "content/{title}.md"},
                         position={"x": 1400, "y": 200}),
        ],
        "connections": [
            Connection(source_id="t1", target_id="n1"),
            Connection(source_id="n1", target_id="n2"),
            Connection(source_id="n2", target_id="n3"),
            Connection(source_id="n3", target_id="n4"),
        ],
    },
    {
        "id": "data_pipeline",
        "name": "Data Pipeline",
        "description": "Extract, transform, and load data",
        "schedule": "0 */6 * * *",
        "nodes": [
            WorkflowNode(id="t1", type="trigger.schedule", label="6-Hour Cycle",
                         config={"schedule": "0 */6 * * *"},
                         position={"x": 50, "y": 200}),
            WorkflowNode(id="n1", type="action.http", label="Fetch API",
                         config={"url": "https://api.example.com/data",
                                  "method": "GET"},
                         position={"x": 350, "y": 200}),
            WorkflowNode(id="n2", type="action.file_write", label="Save Raw",
                         config={"path": "data/raw/{timestamp}.json"},
                         position={"x": 700, "y": 200}),
            WorkflowNode(id="n3", type="action.database", label="Store DB",
                         config={"query": "INSERT INTO data VALUES (?)"},
                         position={"x": 700, "y": 400}),
        ],
        "connections": [
            Connection(source_id="t1", target_id="n1"),
            Connection(source_id="n1", target_id="n2"),
            Connection(source_id="n1", target_id="n3"),
        ],
    },
    {
        "id": "multi_agent_pipeline",
        "name": "Multi-Agent Pipeline",
        "description": "Sequential multi-agent pipeline with delegation",
        "nodes": [
            WorkflowNode(id="t1", type="trigger.manual", label="Start",
                         config={}, position={"x": 50, "y": 200}),
            WorkflowNode(id="n1", type="agent.delegate", label="Research Agent",
                         config={"agent_name": "researcher"},
                         position={"x": 350, "y": 200}),
            WorkflowNode(id="n2", type="logic.if", label="Quality Check",
                         config={"condition": "len(str(value)) > 100"},
                         position={"x": 700, "y": 200}),
            WorkflowNode(id="n3", type="agent.review", label="Peer Review",
                         config={"reviewer_id": "senior", "criteria": "quality"},
                         position={"x": 1050, "y": 100}),
            WorkflowNode(id="n4", type="action.file_write", label="Final Output",
                         config={"path": "output/final.md"},
                         position={"x": 1050, "y": 400}),
        ],
        "connections": [
            Connection(source_id="t1", target_id="n1"),
            Connection(source_id="n1", target_id="n2"),
            Connection(source_id="n2", target_id="n3", source_output="true"),
            Connection(source_id="n2", target_id="n4", source_output="false"),
        ],
    },
    {
        "id": "mcp_integration",
        "name": "MCP Integration",
        "description": "Call MCP tools and process results",
        "nodes": [
            WorkflowNode(id="t1", type="trigger.manual", label="Start",
                         config={}, position={"x": 50, "y": 200}),
            WorkflowNode(id="n1", type="mcp.call_tool", label="MCP Call",
                         config={"server": "filesystem", "tool": "list_files"},
                         position={"x": 350, "y": 200}),
            WorkflowNode(id="n2", type="ai.chat", label="Process Results",
                         config={"system_prompt": "Summarize the file listing"},
                         position={"x": 700, "y": 200}),
            WorkflowNode(id="n3", type="action.file_write", label="Save",
                         config={"path": "mcp_output.md"},
                         position={"x": 1050, "y": 200}),
        ],
        "connections": [
            Connection(source_id="t1", target_id="n1"),
            Connection(source_id="n1", target_id="n2"),
            Connection(source_id="n2", target_id="n3"),
        ],
    },
]


def get_template(template_id: str) -> Optional[dict]:
    """Get a template by ID."""
    for t in TEMPLATES:
        if t["id"] == template_id:
            return t
    return None


def list_templates() -> list[dict]:
    """Return template metadata (without full nodes/connections)."""
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t.get("description", ""),
            "schedule": t.get("schedule", ""),
            "nodes": len(t.get("nodes", [])),
        }
        for t in TEMPLATES
    ]


def create_from_template(template_id: str, name: str = None,
                         description: str = None) -> dict:
    """Create a workflow config from a template."""
    import copy
    from workflows.models import WorkflowConfig, WorkflowStatus

    template = get_template(template_id)
    if not template:
        raise ValueError(f"Template not found: {template_id}")

    wf = WorkflowConfig(
        name=name or template["name"],
        description=description or template.get("description", ""),
        schedule=template.get("schedule", ""),
        nodes=copy.deepcopy(template.get("nodes", [])),
        connections=copy.deepcopy(template.get("connections", [])),
        status=WorkflowStatus.DRAFT,
    )
    return wf
