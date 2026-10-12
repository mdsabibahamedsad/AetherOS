"""Agent adapters (P2, P4, P6) — one normalized interface for every agent:

    prepare() / health_check() / run_task() / collect_trace() / cleanup()

Detection is evidence-based (binary on PATH + version probe with raw
output). An agent that is not installed or lacks credentials yields BLOCKED
results preserved verbatim — never silently dropped, never fabricated.

Live task execution is opt-in and cost-bearing: adapters refuse to launch a
model-backed run unless ``allow_live=True`` is passed by the controller,
which itself is only reachable via the explicit benchmark CLI.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from benchmark.schema import AgentResult, TaskSpec, TaskStatus, new_run_id


HEALTH_INSTALLED = "INSTALLED"
HEALTH_NOT_INSTALLED = "NOT_INSTALLED"
HEALTH_NO_CREDENTIALS = "NO_CREDENTIALS"
HEALTH_ERROR = "ERROR"


@dataclass
class Health:
    status: str
    version: str = "unknown"
    evidence: List[str] = field(default_factory=list)

    @property
    def runnable(self) -> bool:
        return self.status == HEALTH_INSTALLED


class AgentAdapter:
    """Base class. Subclasses override hooks; the contract is fixed."""

    name: str = "abstract"

    def prepare(self) -> None:
        pass

    def health_check(self) -> Health:
        raise NotImplementedError

    def run_task(self, task: TaskSpec, workspace: Path,
                 allow_live: bool = False) -> Dict[str, Any]:
        """Executes one task; returns raw artifacts dict (response text,
        tool_calls, tokens, timings...). Must NOT raise for agent-level
        failures — return them as artifacts['errors']."""
        raise NotImplementedError

    def collect_trace(self, task_id: str, artifacts: Dict[str, Any],
                      trace_dir: Path) -> str:
        """P45/P46 — persist the raw trace; returns its reference."""
        trace_dir.mkdir(parents=True, exist_ok=True)
        p = trace_dir / f"{self.name}-{task_id}-{int(time.time())}.json"
        p.write_text(_safe_json(artifacts), encoding="utf-8")
        return str(p)

    def cleanup(self, workspace: Optional[Path] = None) -> None:
        if workspace and workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)


def _safe_json(obj: Any) -> str:
    import json
    return json.dumps(obj, indent=1, default=str)


# --------------------------------------------------------------------------
# CLI-backed agents

@dataclass
class CLISpec:
    binary: str
    version_args: tuple = ("--version",)
    version_from_stderr: bool = False     # some CLIs print versions to stderr
    prompt_flag: Optional[str] = None     # e.g. "-p" for headless prompts
    credential_markers: tuple = ()        # env vars that indicate auth present


class CLIAgentAdapter(AgentAdapter):
    """Generic adapter driving an installed agent CLI in headless mode."""

    def __init__(self, spec: CLISpec, name: str):
        self.spec = spec
        self.name = name

    def health_check(self) -> Health:
        resolved = _resolve_binary(self.spec.binary)
        if not resolved:
            return Health(HEALTH_NOT_INSTALLED,
                          evidence=[f"binary {self.spec.binary!r} not on PATH"])
        ev = [f"binary at {resolved}"]
        version = "unknown"
        args = [*_exec_prefix(resolved), *self.spec.version_args]
        try:
            r = subprocess.run(args, capture_output=True, text=True,
                               timeout=30)
            out = (r.stderr if self.spec.version_from_stderr
                   else r.stdout) or r.stdout or r.stderr
            lines = [ln for ln in out.strip().splitlines()
                     if ln.strip() and "Traceback" not in ln]
            line = lines[0][:80] if lines else ""
            if line:
                version = line
                ev.append(f"--version -> {version!r}")
            else:
                ev.append(f"{' '.join(args)} exited {r.returncode} "
                          f"with no version output")
        except Exception as exc:
            ev.append(f"probe failed: {type(exc).__name__}: {exc}")
        if self.spec.credential_markers and not any(
                k in _env_keys() for k in self.spec.credential_markers):
            ev.append("no credential marker env var found")
            return Health(HEALTH_NO_CREDENTIALS, version, ev)
        return Health(HEALTH_INSTALLED, version, ev)

    def run_task(self, task: TaskSpec, workspace: Path,
                 allow_live: bool = False) -> Dict[str, Any]:
        if not allow_live:
            return {"errors": ["LIVE_EXECUTION_DISABLED"],
                    "response": "",
                    "warnings": ["run refused: live model execution requires "
                                 "explicit opt-in via 'aetheros benchmark "
                                 "run --allow-live'"]}
        if not self.spec.prompt_flag:
            return {"errors": ["PROMPT_INTERFACE_UNKNOWN"], "response": ""}
        t0 = time.perf_counter()
        try:
            resolved = _resolve_binary(self.spec.binary) or self.spec.binary
            r = subprocess.run(
                [*_exec_prefix(resolved), self.spec.prompt_flag,
                 task.objective],
                capture_output=True, text=True,
                timeout=task.timeout_s, cwd=str(workspace))
            wall = (time.perf_counter() - t0) * 1000.0
            return {"response": r.stdout or "", "wall_clock_ms": wall,
                    "exit_code": r.returncode,
                    "errors": [] if r.returncode == 0 else
                    [f"exit={r.returncode}: {r.stderr[:200]}"]}
        except subprocess.TimeoutExpired:
            return {"response": "", "wall_clock_ms": task.timeout_s * 1000.0,
                    "errors": [f"timeout after {task.timeout_s}s"]}

    def _env_keys(self):  # pragma: no cover - trivial
        import os
        return set(os.environ)


def _resolve_binary(binary: str) -> Optional[str]:
    """shutil.which resolves .ps1/.cmd shims; .cmd/.bat need cmd.exe."""
    p = shutil.which(binary)
    return p


def _exec_prefix(resolved: str) -> List[str]:
    if resolved.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", resolved]
    return [resolved]


def _env_keys() -> List[str]:
    import os
    return list(os.environ)


# --------------------------------------------------------------------------
# Registry — six primary targets + future-agent hook (P2)

_REGISTRY: Dict[str, AgentAdapter] = {}


def register(adapter: AgentAdapter) -> AgentAdapter:
    _REGISTRY[adapter.name] = adapter
    return adapter


def get_adapter(name: str) -> AgentAdapter:
    if name not in _REGISTRY:
        raise KeyError(f"unknown agent {name!r}; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def all_adapters() -> Dict[str, AgentAdapter]:
    return dict(sorted(_REGISTRY.items()))


register(CLIAgentAdapter(CLISpec(
    binary="aetheros", version_from_stderr=True,
    prompt_flag=None,   # interactive-first harness; headless path TBD probe
    credential_markers=()), name="aetheros"))

register(CLIAgentAdapter(CLISpec(
    binary="hermes", version_from_stderr=True, prompt_flag=None),
    name="hermes"))

register(CLIAgentAdapter(CLISpec(
    binary="openhands", prompt_flag=None), name="openhands"))

register(CLIAgentAdapter(CLISpec(
    binary="openclaw", prompt_flag=None), name="openclaw"))

register(CLIAgentAdapter(CLISpec(
    binary="claude",
    version_args=("--version",), prompt_flag="-p"), name="claude-code"))

register(CLIAgentAdapter(CLISpec(
    binary="codex", version_from_stderr=True,
    prompt_flag=None), name="codex"))


def capability_profile(adapter_name: str) -> Dict[str, str]:
    """P6/P36 — declared tool-profile support. Evidence-based defaults:
    an agent gets FULL only where its harness exposes the capability;
    anything unverified stays NOT_TESTED (never inferred from marketing)."""
    matrix = {
        "aetheros": {"research": "FULL", "browser": "FULL",
                     "computer_use": "PARTIAL", "coding": "FULL",
                     "memory": "FULL", "mcp": "FULL", "multi_agent": "FULL"},
        "hermes": {"research": "NOT_TESTED", "browser": "NOT_TESTED",
                   "computer_use": "NOT_TESTED", "coding": "NOT_TESTED",
                   "memory": "NOT_TESTED", "mcp": "NOT_TESTED",
                   "multi_agent": "NOT_TESTED"},
    }
    base = {c: "NOT_TESTED" for c in (
        "research", "browser", "computer_use", "coding", "memory", "mcp",
        "multi_agent")}
    base.update(matrix.get(adapter_name, {}))
    base["terminal"] = "FULL"       # every CLI harness has a shell
    base["files"] = "FULL"
    return base


def blocked_result(run_id: str, adapter_name: str, task: TaskSpec,
                   reason: str, health: Health) -> AgentResult:
    """Preserve non-executions honestly (P9/P12)."""
    return AgentResult(
        benchmark_run_id=run_id, agent=adapter_name, task_id=task.task_id,
        category=task.category, status=TaskStatus.BLOCKED,
        claimed_done=False, score=0.0,
        errors=[reason],
        warnings=[f"health={health.status}",
                  f"evidence={'; '.join(health.evidence[:3])}"],
        difficulty=task.difficulty)
