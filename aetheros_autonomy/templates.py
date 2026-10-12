"""Automation templates (sections 59-60): 10 real definition factories.

Each template returns (AutomationDefinition, safety_card) where the card
lists permissions/tools/external/data/risk/estimates for display BEFORE
activation. Templates never auto-enable.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from aetheros_autonomy.models import (
    ActionRisk, ApprovalPolicy, AutoType, AutomationDefinition, NotifyMode,
)


def _base(name: str, desc: str, atype: AutoType,
          workflow: List[Dict[str, Any]], tools: List[str],
          risks: List[str], external: bool = False) -> Tuple[AutomationDefinition, Dict[str, Any]]:
    auto = AutomationDefinition(
        name=name, description=desc, enabled=False, trusted=False,
        auto_type=atype, workflow=workflow,
        tool_policy={"tools": tools},
        approval_policy=(ApprovalPolicy.ALWAYS_APPROVE.value if external
                         else ApprovalPolicy.PRE_APPROVED.value),
        notification_policy=NotifyMode.IMMEDIATE.value)
    card = {"name": name, "permissions": tools, "tools": tools,
            "external_communication": external, "risks": risks,
            "estimated_cost_usd": round(0.01 * len(workflow), 3),
            "estimated_duration_s": 60 * len(workflow)}
    return auto, card


def daily_research(topic: str) -> Tuple[AutomationDefinition, Dict[str, Any]]:
    return _base(
        f"Daily research: {topic}", f"Research {topic} every weekday morning.",
        AutoType.RECURRING,
        [{"action": "agent", "role": "researcher", "goal": f"research {topic}"},
         {"action": "verify", "method": "evidence"},
         {"action": "notify", "text": f"daily {topic} digest"}],
        ["web_search", "web_extract"], ["network use", "potential false positives"])


def weekly_project_report(project: str) -> Tuple[AutomationDefinition, Dict[str, Any]]:
    return _base(
        f"Weekly report: {project}", "Summarize project signals weekly.",
        AutoType.RECURRING,
        [{"action": "agent", "role": "analyst", "goal": f"summarize {project}"},
         {"action": "artifact", "kind": "report"},
         {"action": "notify", "text": "weekly report ready"}],
        ["read_file", "search_files"], ["may surface stale data"])


def repo_monitor(repo: str) -> Tuple[AutomationDefinition, Dict[str, Any]]:
    return _base(
        f"Monitor repo: {repo}", "Watch releases/commits/security.",
        AutoType.REPOSITORY_TRIGGERED,
        [{"action": "tool", "tool": "repo_check", "target": repo},
         {"action": "branch", "cond": {"op": "CHANGE_DETECTED"},
          "then": [{"action": "notify", "text": "repo changed"}],
          "else": []}],
        ["network"], ["notification volume"], external=False)


def ci_monitor(project: str) -> Tuple[AutomationDefinition, Dict[str, Any]]:
    return _base(
        f"CI monitor: {project}", "Notify on CI failure.",
        AutoType.EVENT_TRIGGERED,
        [{"action": "tool", "tool": "ci_status", "target": project},
         {"action": "branch", "cond": {"op": "EQ", "key": "ci", "value": "failed"},
          "then": [{"action": "notify", "text": "CI failed"}],
          "else": []}],
        ["network"], ["requires CI credentials via secure store"])


def folder_watcher(path: str) -> Tuple[AutomationDefinition, Dict[str, Any]]:
    return _base(
        f"Watch folder: {path}", "Summarize new PDFs.",
        AutoType.FILE_TRIGGERED,
        [{"action": "tool", "tool": "summarize_file"},
         {"action": "notify", "text": "new document summarized"}],
        ["read_file"], ["reads local files in scope only"])


def doc_summarizer(path: str) -> Tuple[AutomationDefinition, Dict[str, Any]]:
    return _base(
        f"Summarize: {path}", "One-shot document summary.",
        AutoType.MANUAL,
        [{"action": "tool", "tool": "summarize_file", "target": path},
         {"action": "artifact", "kind": "summary"}],
        ["read_file"], ["read-only"])


def website_monitor(url: str) -> Tuple[AutomationDefinition, Dict[str, Any]]:
    return _base(
        f"Watch site: {url}", "Notify on meaningful page changes.",
        AutoType.WEB_TRIGGERED,
        [{"action": "tool", "tool": "web_check", "target": url},
         {"action": "branch", "cond": {"op": "CHANGE_DETECTED"},
          "then": [{"action": "notify", "text": "site changed"}],
          "else": []}],
        ["network"], ["respect robots/rate limits"])


def dependency_monitor(project: str) -> Tuple[AutomationDefinition, Dict[str, Any]]:
    return _base(
        f"Dependencies: {project}", "Security updates for deps.",
        AutoType.RECURRING,
        [{"action": "tool", "tool": "dep_audit", "target": project},
         {"action": "notify", "text": "dependency report"}],
        ["network", "read_file"], ["advisory noise possible"])


def task_followup(task: str) -> Tuple[AutomationDefinition, Dict[str, Any]]:
    return _base(
        f"Follow up: {task}", "Nudge on stalled task.",
        AutoType.TASK_TRIGGERED,
        [{"action": "branch",
          "cond": {"op": "TASK_STATE", "task": task, "state": "blocked"},
          "then": [{"action": "notify", "text": "task blocked"}],
          "else": []}],
        [], ["notification only"])


def research_digest(topic: str) -> Tuple[AutomationDefinition, Dict[str, Any]]:
    return _base(
        f"Digest: {topic}", "Weekly topic digest.",
        AutoType.RECURRING,
        [{"action": "agent", "role": "researcher", "goal": topic},
         {"action": "agent", "role": "writer", "goal": "digest"},
         {"action": "notify", "text": "digest ready", "mode": "weekly"}],
        ["web_search"], ["network use"])


TEMPLATES: Dict[str, Callable[..., Tuple[AutomationDefinition, Dict[str, Any]]]] = {
    "daily_research": daily_research,
    "weekly_project_report": weekly_project_report,
    "repo_monitor": repo_monitor,
    "ci_monitor": ci_monitor,
    "folder_watcher": folder_watcher,
    "doc_summarizer": doc_summarizer,
    "website_monitor": website_monitor,
    "dependency_monitor": dependency_monitor,
    "task_followup": task_followup,
    "research_digest": research_digest,
}
