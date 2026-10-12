"""AetherOS intelligence operating layer.

Canonical INTENT -> TASK -> PLAN -> EXECUTION -> RESULT pipeline that
consolidates (not duplicates) existing machinery:

- models: ``aetheros_automation.models.models`` (TaskStatus, AgentRole,
  RiskLevel, GraphExecutionMode, Task, ApprovalRequest) — reused directly.
- planning/orchestration: ``aetheros_automation.orchestrator`` types
  (OrchestrationPlan / OrchestrationTask) — plans built here are shaped to
  be submittable to that engine.
- tool policy: ``tools.registry`` tool metadata (risk_level, permissions,
  confirmation_required) — the guard reads it, never a parallel table.
- approvals: ``aetheros_automation.approvals`` rules — referenced, not copied.
- secrets: ``agent.redact.redact_sensitive_text`` — timelines and results
  are sanitized before they reach any UI or model context.

Security hierarchy enforced by this module::

    USER AUTHORITY > SECURITY POLICY > TASK POLICY > AGENT PERMISSIONS
    > TOOL PERMISSIONS > RESOURCE PERMISSIONS > EXECUTION

Nothing here executes tools itself; it produces guarded, verifiable
structures that the existing executors consume.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from aetheros_automation.models.models import (
    AgentRole,
    GraphExecutionMode,
    RiskLevel,
    TaskStatus,
)


# ---------------------------------------------------------------------------
# Intent model — "what the user said" vs "what the user wants done"
# ---------------------------------------------------------------------------

_DESTRUCTIVE_RE = re.compile(
    r"\b(delete|remove|destroy|wipe|drop|purge|erase|kill|terminate|shutdown|"
    r"uninstall|revoke|reset|overwrite)\b",
    re.IGNORECASE,
)
_EXTERNAL_RE = re.compile(
    r"\b(send|email|publish|post|tweet|deploy|push|share|notify|message|"
    r"upload|invite|pay|purchase|subscribe)\b",
    re.IGNORECASE,
)
_CODE_RE = re.compile(
    r"\b(code|repo|repository|test|bug|fix|refactor|implement|build|commit|"
    r"pr\b|pull request|function|class|module)\b",
    re.IGNORECASE,
)
_RESEARCH_RE = re.compile(
    r"\b(research|find|search|compare|best|options|analyze|analyse|analyse|"
    r"investigate|survey|report|summar)\b",
    re.IGNORECASE,
)
_FILE_RE = re.compile(
    r"\b(file|folder|directory|document|organize|clean ?up|rename|move|copy)\b",
    re.IGNORECASE,
)
_BROWSER_RE = re.compile(
    r"\b(website|webpage|browser|url|http|site|page|login|form|click)\b",
    re.IGNORECASE,
)
_APPROVAL_RE = re.compile(
    r"\b(approve|approval|permission|authorize|confirm|review)\b",
    re.IGNORECASE,
)


@dataclass
class Intent:
    """Structured understanding of a user request.

    `utterance` is what the user said; the remaining fields are the
    operational interpretation. No chain-of-thought is stored here.
    """

    utterance: str
    objective: str
    targets: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    risk_signals: list[str] = field(default_factory=list)
    needs_approval: bool = False
    suggested_roles: list[AgentRole] = field(default_factory=list)


def parse_intent(utterance: str) -> Intent:
    """Deterministically extract an operational intent from raw text.

    Rule-based (no model call): safe to run anywhere, fully testable, and
    never hallucinates capabilities. The deeper NL engine
    (``aetheros_automation.nlp``) remains the advanced path; this is the
    canonical baseline every surface can rely on.
    """
    text = (utterance or "").strip()
    objective = re.sub(r"\s+", " ", text).strip()
    if len(objective) > 280:
        objective = objective[:277].rstrip() + "..."

    domains: list[str] = []
    roles: list[AgentRole] = []
    risks: list[str] = []

    if _CODE_RE.search(text):
        domains.append("coding")
        roles.append(AgentRole.CODING)
    if _RESEARCH_RE.search(text):
        domains.append("research")
        roles.append(AgentRole.RESEARCH)
    if _FILE_RE.search(text):
        domains.append("files")
        roles.append(AgentRole.FILE)
    if _BROWSER_RE.search(text):
        domains.append("browser")
        roles.append(AgentRole.BROWSER)
    if _EXTERNAL_RE.search(text):
        domains.append("external")
        roles.append(AgentRole.COMMUNICATION)
    if _APPROVAL_RE.search(text):
        domains.append("approval")

    if _DESTRUCTIVE_RE.search(text):
        risks.append("destructive language detected")
    if _EXTERNAL_RE.search(text):
        risks.append("external side effects possible")
    targets = sorted(set(domains))

    needs_approval = bool(risks)
    if AgentRole.CODING in roles and AgentRole.QA not in roles:
        roles.append(AgentRole.QA)  # code changes always pair with verification
    if not roles:
        roles.append(AgentRole.COORDINATOR)

    return Intent(
        utterance=text,
        objective=objective or "(empty request)",
        targets=targets,
        domains=domains,
        constraints=["verify before reporting completion"] if roles else [],
        risk_signals=risks,
        needs_approval=needs_approval,
        suggested_roles=roles,
    )


# ---------------------------------------------------------------------------
# Agent capability model — roles map to real tools/permissions
# ---------------------------------------------------------------------------

#: Bounded, explicit capability map. Tools named here MUST exist in
#: ``tools/registry.py`` toolsets or MCP catalog; unknown names fail closed
#: at guard time (see guard_tool_call).
ROLE_CAPABILITIES: dict[AgentRole, dict[str, list[str]]] = {
    AgentRole.COORDINATOR: {
        "tools": ["delegate_task", "todo", "cronjob"],
        "permissions": ["task.delegate", "automation.manage"],
    },
    AgentRole.PLANNER: {
        "tools": ["todo", "session_search"],
        "permissions": ["task.plan"],
    },
    AgentRole.RESEARCH: {
        "tools": ["web_search", "web_extract", "session_search"],
        "permissions": ["network.read"],
    },
    AgentRole.CODING: {
        "tools": ["read_file", "patch", "terminal", "search_files"],
        "permissions": ["filesystem.read", "filesystem.write", "terminal.execute"],
    },
    AgentRole.DEVELOPER: {
        "tools": ["read_file", "patch", "terminal", "search_files"],
        "permissions": ["filesystem.read", "filesystem.write", "terminal.execute"],
    },
    AgentRole.FILE: {
        "tools": ["read_file", "search_files"],
        "permissions": ["filesystem.read"],
    },
    AgentRole.BROWSER: {
        "tools": ["browser_navigate", "web_extract"],
        "permissions": ["network.read", "browser.control"],
    },
    AgentRole.QA: {
        "tools": ["terminal", "read_file"],
        "permissions": ["filesystem.read", "terminal.execute"],
    },
    AgentRole.REVIEW: {
        "tools": ["read_file", "search_files"],
        "permissions": ["filesystem.read"],
    },
    AgentRole.SECURITY: {
        "tools": ["read_file", "search_files", "session_search"],
        "permissions": ["filesystem.read", "audit.read"],
    },
    AgentRole.MEMORY: {
        "tools": ["memory", "session_search"],
        "permissions": ["memory.read", "memory.write"],
    },
    AgentRole.WRITER: {
        "tools": ["read_file"],
        "permissions": ["filesystem.read"],
    },
    AgentRole.DATA: {
        "tools": ["read_file", "execute_code"],
        "permissions": ["filesystem.read"],
    },
    AgentRole.COMMUNICATION: {
        "tools": ["send_message"],
        "permissions": ["external.communicate"],
    },
    AgentRole.DEPLOYMENT: {
        "tools": ["terminal", "cronjob"],
        "permissions": ["terminal.execute", "external.deploy", "automation.manage"],
    },
    AgentRole.CREATIVE: {
        "tools": ["image_gen", "read_file"],
        "permissions": ["filesystem.read"],
    },
}

#: Hard bound on agents per plan — spawning is never uncontrolled.
MAX_AGENTS_PER_PLAN = 5


def select_agents(intent: Intent, max_agents: int = MAX_AGENTS_PER_PLAN) -> list[AgentRole]:
    """Choose a bounded, de-duplicated role list for an intent."""
    seen: list[AgentRole] = []
    for role in intent.suggested_roles:
        if role not in seen:
            seen.append(role)
    if AgentRole.COORDINATOR not in seen and len(seen) > 1:
        seen.insert(0, AgentRole.COORDINATOR)
    return seen[:max(max_agents, 1)]


# ---------------------------------------------------------------------------
# Planning — operational execution structure (not chain-of-thought)
# ---------------------------------------------------------------------------

_PLAN_PHASES: tuple[tuple[str, str, GraphExecutionMode], ...] = (
    ("understand", "Understand objective and constraints", GraphExecutionMode.SEQUENTIAL),
    ("context", "Gather workspace, project, and conversation context", GraphExecutionMode.SEQUENTIAL),
    ("inspect", "Inspect resources (files, sessions, memory) with read-only tools", GraphExecutionMode.PARALLEL),
    ("approve", "Request approvals for risky actions", GraphExecutionMode.HUMAN_APPROVAL),
    ("execute", "Execute the work with selected agents and tools", GraphExecutionMode.DEPENDENT),
    ("observe", "Collect tool outputs and agent summaries", GraphExecutionMode.SEQUENTIAL),
    ("verify", "Verify postconditions against success criteria", GraphExecutionMode.SEQUENTIAL),
    ("artifact", "Produce and index artifacts", GraphExecutionMode.SEQUENTIAL),
    ("report", "Report the structured result", GraphExecutionMode.SEQUENTIAL),
)


@dataclass
class PlanStep:
    id: str
    name: str
    detail: str
    agent_role: AgentRole
    tools: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    execution_mode: GraphExecutionMode = GraphExecutionMode.SEQUENTIAL
    requires_approval: bool = False
    verification: str = ""


@dataclass
class ExecutionPlan:
    id: str
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    agents: list[AgentRole] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    created_at: float = field(default_factory=time.time)

    def to_orchestrator_dict(self) -> dict[str, Any]:
        """Shape this plan for the existing orchestrator engine."""
        return {
            "goal": self.goal,
            "risk_level": self.risk_level.value,
            "subtasks": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.detail,
                    "agent_role": s.agent_role.value,
                    "tools": list(s.tools),
                    "dependencies": list(s.dependencies),
                    "execution_mode": s.execution_mode.value,
                    "requires_approval": s.requires_approval,
                }
                for s in self.steps
            ],
        }


def plan_from_intent(intent: Intent) -> ExecutionPlan:
    """Build a structured, dependency-ordered plan from an intent."""
    agents = select_agents(intent)
    primary = agents[-1] if len(agents) > 1 else agents[0]
    risk = (
        RiskLevel.HIGH
        if intent.risk_signals
        else (RiskLevel.MEDIUM if "coding" in intent.domains or "external" in intent.domains else RiskLevel.LOW)
    )

    steps: list[PlanStep] = []
    prev_id = ""
    for idx, (slug, name, mode) in enumerate(_PLAN_PHASES):
        step_id = f"step-{idx + 1}-{slug}"
        deps = [prev_id] if prev_id and mode not in (GraphExecutionMode.PARALLEL,) else ([prev_id] if prev_id else [])
        needs_approval = slug == "approve" and intent.needs_approval
        tools = list(ROLE_CAPABILITIES.get(primary, {}).get("tools", [])) if slug in ("inspect", "execute") else []
        steps.append(
            PlanStep(
                id=step_id,
                name=name,
                detail=f"{name} — {intent.objective}",
                agent_role=primary if slug in ("execute", "inspect") else AgentRole.COORDINATOR,
                tools=tools,
                dependencies=deps,
                execution_mode=mode,
                requires_approval=needs_approval,
                verification="postconditions checked before completion" if slug == "verify" else "",
            )
        )
        prev_id = step_id

    return ExecutionPlan(
        id=f"plan-{uuid.uuid4().hex[:12]}",
        goal=intent.objective,
        steps=steps,
        agents=agents,
        risk_level=risk,
        requires_approval=intent.needs_approval,
    )


# ---------------------------------------------------------------------------
# Tool execution guard — AGENT -> POLICY -> PERMISSION -> APPROVAL -> EXECUTOR
# ---------------------------------------------------------------------------

@dataclass
class ToolMeta:
    """Snapshot of registry metadata for one tool (testable without imports)."""

    name: str
    risk_level: str = "LOW_RISK"
    permissions: list[str] = field(default_factory=list)
    confirmation_required: bool = False
    exists: bool = True


@dataclass
class GuardDecision:
    allowed: bool
    requires_approval: bool
    reasons: list[str] = field(default_factory=list)

    @property
    def denied(self) -> bool:
        return not self.allowed and not self.requires_approval


_HIGH_RISK_TOKENS = ("HIGH", "CRITICAL", "DESTRUCTIVE")
_DANGEROUS_ARGS_RE = re.compile(
    r"(rm\s+-rf|;\s*rm|mkfs|dd\s+if=|:\(\)\s*\{|:;\s*\}|\.\./\.\.|/etc/passwd|"
    r"Authorization\s*:|api[_-]?key\s*=|password\s*=|BEGIN [A-Z ]*PRIVATE KEY)",
    re.IGNORECASE,
)


def guard_tool_call(
    tool_name: str,
    args: dict[str, Any] | None = None,
    *,
    tool_meta: ToolMeta | None = None,
    granted_permissions: list[str] | None = None,
    approvals_granted: list[str] | None = None,
) -> GuardDecision:
    """Central policy gate for a single tool call.

    Unknown tools fail closed. High-risk or confirmation-gated tools require
    an approval grant. Dangerous argument patterns (injection, traversal,
    secret exfiltration shapes) deny outright. Callers may pass a
    ``ToolMeta`` snapshot (tests, dry-runs); otherwise metadata is read
    live from ``tools.registry``.
    """
    args = args or {}
    granted = set(granted_permissions or [])
    approved = set(approvals_granted or [])

    meta = tool_meta
    if meta is None:
        meta = _read_tool_meta(tool_name)
    if meta is None or not meta.exists:
        return GuardDecision(
            allowed=False,
            requires_approval=False,
            reasons=[f"unknown tool '{tool_name}' — denied (fail closed)"],
        )

    if _DANGEROUS_ARGS_RE.search(str(args)):
        return GuardDecision(
            allowed=False,
            requires_approval=False,
            reasons=["dangerous argument pattern — denied without retry"],
        )

    missing = [p for p in meta.permissions if p not in granted]
    if missing:
        return GuardDecision(
            allowed=False,
            requires_approval=True,
            reasons=[f"missing permissions: {', '.join(missing)}"],
        )

    risk = (meta.risk_level or "").upper()
    if meta.confirmation_required or any(t in risk for t in _HIGH_RISK_TOKENS):
        if tool_name in approved:
            return GuardDecision(allowed=True, requires_approval=False, reasons=["approval grant present"])
        return GuardDecision(
            allowed=False,
            requires_approval=True,
            reasons=[f"tool '{tool_name}' risk={meta.risk_level} requires approval"],
        )

    return GuardDecision(allowed=True, requires_approval=False, reasons=["policy passed"])


def _read_tool_meta(tool_name: str) -> ToolMeta | None:
    try:
        from tools.registry import registry as _registry

        get = getattr(_registry, "get", None)
        entry = get(tool_name) if callable(get) else None
        if entry is None:
            tools_map = getattr(_registry, "tools", None) or getattr(_registry, "_tools", None) or {}
            entry = tools_map.get(tool_name) if isinstance(tools_map, dict) else None
        if entry is None:
            return ToolMeta(name=tool_name, exists=False)
        return ToolMeta(
            name=tool_name,
            risk_level=str(getattr(entry, "risk_level", "LOW_RISK")),
            permissions=list(getattr(entry, "permissions", None) or []),
            confirmation_required=bool(getattr(entry, "confirmation_required", False)),
            exists=True,
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Verification — completion is earned, never assumed
# ---------------------------------------------------------------------------

@dataclass
class VerificationCheck:
    id: str
    description: str
    required: bool = True
    passed: bool = False
    evidence: str = ""


@dataclass
class VerificationReport:
    passed: bool
    required_passed: int
    required_total: int
    checks: list[VerificationCheck] = field(default_factory=list)


def verify_outcome(checks: list[VerificationCheck]) -> VerificationReport:
    """Evaluate explicit postcondition checks."""
    required = [c for c in checks if c.required]
    passed = [c for c in required if c.passed]
    return VerificationReport(
        passed=bool(required) and len(passed) == len(required),
        required_passed=len(passed),
        required_total=len(required),
        checks=list(checks),
    )


def check_file_exists(path: str) -> VerificationCheck:
    """Real filesystem postcondition: the path must exist."""
    import os as _os

    exists = _os.path.exists(path)
    return VerificationCheck(
        id=f"file-exists:{path}",
        description=f"File exists: {path}",
        passed=exists,
        evidence="present on filesystem" if exists else "missing from filesystem",
    )


def check_file_contains(path: str, needle: str) -> VerificationCheck:
    """Real content postcondition: file must exist and contain `needle`."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError as exc:
        return VerificationCheck(
            id=f"file-contains:{path}",
            description=f"File contains expected content: {path}",
            evidence=f"unreadable: {exc}",
        )
    found = needle in content
    return VerificationCheck(
        id=f"file-contains:{path}",
        description=f"File contains expected content: {path}",
        passed=found,
        evidence="needle found" if found else "needle absent",
    )


def completion_allowed(status: TaskStatus, report: VerificationReport) -> bool:
    """A task may complete only with required verification passing.

    Stopped-model, HTTP-200, or exit-code-0 alone never qualifies — the
    caller must present a passing verification report.
    """
    if status in (TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.BLOCKED):
        return False
    return report.passed


# ---------------------------------------------------------------------------
# Timeline, results, events — observable, redacted operational history
# ---------------------------------------------------------------------------

@dataclass
class TimelineEvent:
    ts: float
    kind: str  # task.created|plan.generated|approval.*|agent.*|tool.*|artifact.created|verification.*|task.*
    label: str
    ref: str = ""


def _sanitize(text: str) -> str:
    try:
        from agent.redact import redact_sensitive_text as _redact

        # force=True: timelines/results are a safety boundary that must never
        # return raw secrets regardless of the user's logging preference.
        redacted = _redact(text, force=True)
        return redacted if isinstance(redacted, str) else text
    except Exception:
        return text


def build_timeline(events: list[TimelineEvent]) -> list[TimelineEvent]:
    """Order events chronologically with secrets redacted. Real events only."""
    ordered = sorted(events, key=lambda e: e.ts)
    return [TimelineEvent(ts=e.ts, kind=e.kind, label=_sanitize(e.label), ref=e.ref) for e in ordered]


@dataclass
class TaskResult:
    status: str
    summary: str
    actions: list[str] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    agents_used: list[str] = field(default_factory=list)
    verification: str = ""
    artifacts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)


def build_result(
    *,
    status: str,
    summary: str,
    report: VerificationReport | None = None,
    timeline: list[TimelineEvent] | None = None,
    files_changed: list[str] | None = None,
    artifacts: list[str] | None = None,
    warnings: list[str] | None = None,
    next_actions: list[str] | None = None,
) -> TaskResult:
    """Assemble the concise user-facing result from real execution records."""
    timeline = timeline or []
    tools_used = sorted({e.ref for e in timeline if e.kind.startswith("tool.") and e.ref})
    agents_used = sorted({e.ref for e in timeline if e.kind.startswith("agent.") and e.ref})
    actions = [_sanitize(e.label) for e in timeline if e.kind in ("tool.completed", "agent.completed", "artifact.created")]
    verification = (
        f"{report.required_passed}/{report.required_total} required checks passed"
        if report
        else "no verification recorded"
    )
    return TaskResult(
        status=status,
        summary=_sanitize(summary),
        actions=actions,
        files_changed=list(files_changed or []),
        tools_used=tools_used,
        agents_used=agents_used,
        verification=verification,
        artifacts=list(artifacts or []),
        warnings=[_sanitize(w) for w in (warnings or [])],
        next_actions=list(next_actions or []),
    )


#: Canonical event kinds reused by UI timeline renderers.
EVENT_KINDS: tuple[str, ...] = (
    "task.created",
    "plan.generated",
    "approval.requested",
    "approval.resolved",
    "agent.started",
    "agent.completed",
    "tool.called",
    "tool.completed",
    "artifact.created",
    "verification.passed",
    "verification.failed",
    "task.completed",
    "task.failed",
)


def new_event(kind: str, label: str, ref: str = "") -> TimelineEvent:
    if kind not in EVENT_KINDS:
        raise ValueError(f"unknown event kind: {kind}")
    return TimelineEvent(ts=time.time(), kind=kind, label=label, ref=ref)


#: Retry policy for safe operations — dangerous operations must never
#: silently retry (caller enforces via guard decisions).
SAFE_RETRY_POLICY: dict[str, Any] = {
    "max_retries": 3,
    "backoff": "exponential",
    "retryable": ["timeout", "rate_limit", "provider_error", "tool_error"],
    "never_retry_silently": ["destructive", "external", "payment", "credential"],
}


def is_retryable(failure_type: str, risk_level: RiskLevel = RiskLevel.LOW) -> bool:
    if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        return False
    return failure_type in SAFE_RETRY_POLICY["retryable"]


ArtifactHandler = Callable[[str, bytes], str]


def store_artifact(
    *,
    task_id: str,
    name: str,
    payload: bytes,
    handler: ArtifactHandler,
) -> dict[str, Any]:
    """Persist an artifact through the caller's storage handler.

    The operating layer never invents storage: the platform passes the real
    handler (workspace/files API). Returns identity metadata for the result.
    """
    artifact_id = f"art-{uuid.uuid4().hex[:12]}"
    location = handler(name, payload)
    return {
        "id": artifact_id,
        "task_id": task_id,
        "name": name,
        "location": location,
        "size": len(payload),
        "created_at": time.time(),
    }
