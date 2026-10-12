"""Research memory bridge (P48-49).

Optionally writes durable research artifacts (conclusions, sources,
queries, failures) into the agent's memory store with MANDATORY provenance:
source, timestamp, confidence, scope. Opt-in only — research never mutates
user memory silently.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from agent.research.models import (
    Claim,
    ClaimStatus,
    ResearchTask,
)


MemoryWriteFn = Callable[..., object]


def default_memory_write_fn() -> Optional[MemoryWriteFn]:
    """Resolve tools.memory_tool.memory lazily; None when unavailable."""
    try:
        from tools.memory_tool import memory
    except Exception:
        return None
    return memory


@dataclass
class MemoryWriteRecord:
    target: str
    content: str
    metadata: Dict


def build_memory_records(
    task: ResearchTask,
    claims: List[Claim],
    max_items: int = 5,
) -> List[MemoryWriteRecord]:
    """Compose provenance-complete records from the strongest findings."""
    records: List[MemoryWriteRecord] = []
    strong = [
        c
        for c in claims
        if c.status in (ClaimStatus.CONFIRMED, ClaimStatus.STRONGLY_SUPPORTED)
    ]
    for claim in strong[:max_items]:
        source_refs = ",".join(claim.source_ids[:3]) or "no-source"
        records.append(
            MemoryWriteRecord(
                target="MEMORY",
                content=f"[research:{task.research_id}] {claim.text}",
                metadata={
                    "source": f"research:{task.research_id}",
                    "timestamp": str(time.time()),
                    "confidence": str(claim.confidence),
                    "scope": "default",
                    "status": claim.status.value,
                    "query": task.user_query[:200],
                },
            )
        )
    if not records:
        records.append(
            MemoryWriteRecord(
                target="MEMORY",
                content=(
                    f"[research:{task.research_id}] No corroborated findings "
                    f"for query: {task.user_query}"
                ),
                metadata={
                    "source": f"research:{task.research_id}",
                    "timestamp": str(time.time()),
                    "confidence": "0.0",
                    "scope": "default",
                },
            )
        )
    return records


def remember_research(
    task: ResearchTask,
    claims: List[Claim],
    write_fn: Optional[MemoryWriteFn] = None,
    max_items: int = 5,
) -> List[Dict]:
    """Opt-in memory persistence. Returns per-record outcome dicts."""
    if write_fn is None:
        write_fn = default_memory_write_fn()
    outcomes: List[Dict] = []
    for record in build_memory_records(task, claims, max_items=max_items):
        if write_fn is None:
            outcomes.append({"target": record.target, "written": False,
                             "reason": "memory_tool_unavailable"})
            continue
        try:
            result = write_fn(
                action="add",
                target=record.target,
                content=record.content,
                metadata=record.metadata,
            )
            outcomes.append({"target": record.target, "written": True,
                             "result": str(result)[:200]})
        except Exception as exc:
            outcomes.append({"target": record.target, "written": False,
                             "reason": str(exc)[:200]})
    return outcomes
