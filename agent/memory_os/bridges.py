"""Integration bridges (P85-87): research results, computer-use patterns,
task checkpoints — all inbound content passes the same firewall."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.memory_os.manager import MemoryManager
from agent.memory_os.models import (
    Confidence,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    Sensitivity,
    SourceType,
)
from agent.memory_os.security import AccessContext


def ingest_research(
    manager: MemoryManager,
    records: List[Dict[str, Any]],
    *,
    project_id: str = "",
) -> List[str]:
    """P85 — accept records shaped like agent.research.memory_bridge outputs:
    {target, content, metadata:{source, timestamp, confidence, scope, status}}.

    Research is semi-trusted (derived): verified conclusions land ACTIVE,
    everything else CANDIDATE; provenance is mandatory.
    """
    ids: List[str] = []
    for rec in records:
        meta = dict(rec.get("metadata") or {})
        conf_raw = str(meta.get("confidence", "medium")).lower()
        try:
            confidence = Confidence(conf_raw)
        except ValueError:
            confidence = Confidence.MEDIUM
        confirmed = conf_raw in ("confirmed", "strongly_supported")
        outcome = manager.remember(
            str(rec.get("content", "")),
            type_=MemoryType.RESEARCH,
            source_type=SourceType.RESEARCH,
            source_id=str(meta.get("source", "")),
            scope=MemoryScope.PROJECT if project_id else MemoryScope.USER,
            project_id=project_id,
            confidence=confidence,
            importance=0.6 if confirmed else 0.4,
            status=MemoryStatus.ACTIVE if confirmed else MemoryStatus.CANDIDATE,
            semantic_key=f"research:{meta.get('source', '')}",
            tags=["research"],
            actor="research-bridge",
            channel="research",
            metadata={"query": meta.get("query", ""),
                      "timestamp": meta.get("timestamp")},
            ctx=AccessContext.user(),
        )
        ids.append(outcome.item.memory_id)
    manager.store.audit.append("research-ingest", "research-bridge",
                               detail={"count": len(ids)})
    return ids


def import_ui_patterns(manager: MemoryManager, *, limit: int = 64,
                       home: Optional[Path] = None) -> int:
    """P86 — pull sanitized UI-pattern hints from Master 15 pattern memory.

    Source file is already redacted/refuse-if-secret upstream. Imported as
    hint_only COMPUTER_USE/UI_PATTERN items: DATA never authority.
    """
    from aetheros_constants import get_aetheros_home

    base = home or get_aetheros_home()
    src = Path(base) / "computer_actions" / "ui_patterns.json"
    if not src.exists():
        return 0
    try:
        entries = json.loads(src.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    if isinstance(entries, dict):
        entries = entries.get("patterns") or list(entries.values())
    n = 0
    for entry in entries[:limit]:
        text = json.dumps(entry, default=str)[:600] if not isinstance(entry, str) \
            else entry[:600]
        outcome = manager.remember(
            text,
            type_=MemoryType.UI_PATTERN,
            source_type=SourceType.TOOL,
            source_id="aetheros_computer.pattern_memory",
            scope=MemoryScope.USER,
            sensitivity=Sensitivity.INTERNAL,
            importance=0.3,
            status=MemoryStatus.ACTIVE,
            hint_only=True,
            allow_agents=True,
            tags=["ui-pattern", "computer-use", "hint-only"],
            actor="computer-bridge",
            channel="computer",
            dedupe=True,
        )
        if outcome.effective_status is not MemoryStatus.QUARANTINED:
            n += 1
    return n


def task_checkpoint_ref(
    manager: MemoryManager,
    *,
    task_id: str,
    objective: str,
    checkpoint_hash: str = "",
    pending: Optional[List[str]] = None,
    decisions: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    owner: str = "default",
) -> str:
    """P9/P86 — record task memory that *references* the real checkpoint store
    (tools/checkpoint_manager.py) instead of duplicating it."""
    parts = [f"objective: {objective}"]
    if checkpoint_hash:
        parts.append(f"checkpoint: {checkpoint_hash}")
    if decisions:
        parts.append("decisions: " + "; ".join(decisions))
    if errors:
        parts.append("errors: " + "; ".join(errors))
    if pending:
        parts.append("pending: " + "; ".join(pending))
    item = manager.remember(
        "\n".join(parts),
        type_=MemoryType.TASK,
        source_type=SourceType.SYSTEM,
        source_id=f"checkpoint:{checkpoint_hash}" if checkpoint_hash else "",
        scope=MemoryScope.TASK,
        owner=owner,
        task_id=task_id,
        confidence=Confidence.HIGH,
        status=MemoryStatus.ACTIVE,
        semantic_key=f"task:{task_id}",
        tags=["task-memory"],
        actor="task-bridge",
        channel="system",
        metadata={"pending": pending or [], "decisions": decisions or []},
    )
    return item.item.memory_id


def schedule_maintenance(every: str = "1d") -> Dict[str, Any]:
    """P87 — recurring maintenance via the existing cron scheduler."""
    from cron.jobs import create_job

    return create_job(
        prompt=(
            "Run `aetheros memory-os maintenance` in the terminal and report "
            "expired/stale/consolidated memory counts."
        ),
        schedule=f"every {every}",
        name="memory-os-maintenance",
        origin="memory-os",
        repeat=True,
    )


def cancel_maintenance() -> bool:
    from cron import jobs as cron_jobs

    for job in cron_jobs.list_jobs(include_disabled=True):
        name = job.get("name", "") if isinstance(job, dict) else ""
        if name == "memory-os-maintenance":
            jid = job.get("id") if isinstance(job, dict) else None
            if jid:
                cron_jobs.remove_job(jid)
                return True
    return False
