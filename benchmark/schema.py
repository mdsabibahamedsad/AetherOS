"""Normalized benchmark result schema (Master 21 P47, P14-16).

Status semantics:
PASS   - validator criteria met
PARTIAL- some criteria met (score fraction recorded)
FAIL   - executed but criteria unmet
BLOCKED- never executed (agent missing, capability unavailable, unsafe):
         preserved, never discarded.
FALSE_DONE is derived: agent claimed completion while validation failed.
"""

from __future__ import annotations

import dataclasses
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class Difficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EXPERT = "EXPERT"
    LONG_HORIZON = "LONG_HORIZON"


BENCHMARK_VERSION = "m21-v1"

SCHEMA_FIELDS = (
    "benchmark_run_id", "agent", "agent_version", "model", "provider",
    "task_id", "category", "difficulty", "status", "verified",
    "claimed_done", "false_done", "score", "wall_clock_ms", "ttft_ms",
    "input_tokens", "output_tokens", "total_tokens", "tool_calls",
    "successful_tool_calls", "failed_tool_calls", "redundant_tool_calls",
    "cost_usd", "errors", "warnings", "trace_reference", "environment_ref",
    "fairness_flags", "timestamp",
)


@dataclass
class TaskSpec:
    """One benchmark task (dataset row)."""

    task_id: str
    category: str                 # "01_basic_response" .. "24_e2e_os"
    difficulty: Difficulty
    objective: str                # EXACT user-facing prompt (P5)
    tools_profile: str = "standard"   # none|minimal|standard|full|research|
    timeout_s: int = 300              # browser|computer_use|memory|
    validator: Dict[str, Any] = field(default_factory=dict)  # multi_agent|mcp
    repeats: int = 1              # P29/P30 reliability repetitions
    requires_live_model: bool = True
    sandbox: bool = True          # destructive work only in sandboxes (P24)
    notes: str = ""

    def __post_init__(self):
        if isinstance(self.difficulty, str):
            self.difficulty = Difficulty(self.difficulty)
        self.validator = dict(self.validator or {"type": "non_empty_response"})


@dataclass
class AgentResult:
    """P47 normalized per-task-run record."""

    benchmark_run_id: str
    agent: str
    task_id: str
    category: str
    status: TaskStatus
    verified: bool = False
    claimed_done: bool = False
    score: float = 0.0             # 0..1 validator fraction
    wall_clock_ms: float = 0.0
    ttft_ms: Optional[float] = None
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    successful_tool_calls: int = 0
    failed_tool_calls: int = 0
    redundant_tool_calls: int = 0
    cost_usd: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    trace_reference: str = ""
    environment_ref: str = ""
    fairness_flags: List[str] = field(default_factory=list)
    agent_version: str = "unknown"
    model: str = "unknown"
    provider: str = "unknown"
    difficulty: Difficulty = Difficulty.MEDIUM
    timestamp: float = field(default_factory=time.time)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def false_done(self) -> bool:
        """P16 — claimed completion contradicted by validation."""
        return self.claimed_done and self.status is TaskStatus.FAIL

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["status"] = self.status.value
        d["difficulty"] = self.difficulty.value
        d["total_tokens"] = self.total_tokens
        d["false_done"] = self.false_done
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AgentResult":
        d = dict(d)
        d["status"] = TaskStatus(d["status"])
        d["difficulty"] = Difficulty(d.get("difficulty", "MEDIUM"))
        d.pop("total_tokens", None)
        d.pop("false_done", None)
        valid = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})


def new_run_id(prefix: str = "bm") -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:6]}"
