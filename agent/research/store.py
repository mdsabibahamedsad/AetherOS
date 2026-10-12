"""SQLite persistence for research tasks, transitions, sources, claims.

Profile-safe via ``get_aetheros_home()``. Enables checkpoint/resume and
idempotent re-research: seen pages and fetched-content hashes are unique
per task, so interrupted or repeated research reuses prior work.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from aetheros_constants import get_aetheros_home
from agent.research.models import (
    Claim,
    ClaimStatus,
    Contradiction,
    Evidence,
    ResearchSource,
    ResearchTask,
    TaskStatus,
)
from agent.research.state import TERMINAL_STATES, StateTransition
from agent.research.urlnorm import dedup_key, normalize_url

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    research_id TEXT PRIMARY KEY,
    user_query TEXT NOT NULL,
    status TEXT NOT NULL,
    depth TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    final_report TEXT NOT NULL DEFAULT '',
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    timestamp REAL NOT NULL,
    detail TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_transitions_task ON transitions(task_id);
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    page_key TEXT NOT NULL,
    domain TEXT NOT NULL,
    content_hash TEXT NOT NULL DEFAULT '',
    retrieved_at REAL NOT NULL,
    quarantined INTEGER NOT NULL DEFAULT 0,
    quality_score REAL NOT NULL DEFAULT -1,
    data TEXT NOT NULL,
    UNIQUE (task_id, page_key)
);
CREATE INDEX IF NOT EXISTS idx_sources_task ON sources(task_id);
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at REAL NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_claims_task ON claims(task_id);
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_claim ON evidence(claim_id);
CREATE TABLE IF NOT EXISTS contradictions (
    contradiction_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    claim_a_id TEXT NOT NULL,
    claim_b_id TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id);
CREATE TABLE IF NOT EXISTS kg_graphs (
    task_id TEXT PRIMARY KEY,
    updated_at REAL NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS domain_stats (
    registrable TEXT PRIMARY KEY,
    fetches INTEGER NOT NULL DEFAULT 0,
    quarantined INTEGER NOT NULL DEFAULT 0,
    blocked INTEGER NOT NULL DEFAULT 0,
    duplicates INTEGER NOT NULL DEFAULT 0,
    last_seen REAL NOT NULL DEFAULT 0
);
"""


def default_db_path() -> Path:
    return Path(get_aetheros_home()) / "research" / "research.db"


class ResearchStore:
    """Durable research-state storage (checkpoint/resume/idempotency)."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            str(self.db_path), check_same_thread=False, timeout=30.0
        )
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- tasks -------------------------------------------------------------

    def create_task(self, task: ResearchTask) -> None:
        now = time.time()
        if not task.created_at:
            task.created_at = now
        task.updated_at = now
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO tasks "
                "(research_id, user_query, status, depth, created_at, updated_at,"
                " final_report, data) VALUES (?,?,?,?,?,?,?,?)",
                (
                    task.research_id,
                    task.user_query,
                    task.status.value,
                    task.depth.value,
                    task.created_at,
                    task.updated_at,
                    task.final_report,
                    json.dumps(task.to_dict()),
                ),
            )
            self._conn.commit()

    def save_task(self, task: ResearchTask) -> None:
        task.touch()
        self.create_task(task)

    def get_task(self, research_id: str) -> Optional[ResearchTask]:
        row = self._conn.execute(
            "SELECT data FROM tasks WHERE research_id = ?", (research_id,)
        ).fetchone()
        return ResearchTask.from_dict(json.loads(row[0])) if row else None

    def find_latest_by_query(self, query: str) -> Optional[ResearchTask]:
        row = self._conn.execute(
            "SELECT data FROM tasks WHERE user_query = ? "
            "ORDER BY updated_at DESC LIMIT 1",
            (query,),
        ).fetchone()
        return ResearchTask.from_dict(json.loads(row[0])) if row else None

    def list_tasks(self, include_terminal: bool = True) -> List[ResearchTask]:
        rows = self._conn.execute(
            "SELECT data FROM tasks ORDER BY updated_at DESC"
        ).fetchall()
        tasks = [ResearchTask.from_dict(json.loads(r[0])) for r in rows]
        if include_terminal:
            return tasks
        return [t for t in tasks if t.status not in TERMINAL_STATES]

    def resumable_tasks(self) -> List[ResearchTask]:
        return [
            t
            for t in self.list_tasks(include_terminal=False)
            if t.status != TaskStatus.CREATED
        ]

    # -- transitions ---------------------------------------------------------

    def record_transition(self, event: StateTransition) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO transitions "
                "(task_id, from_status, to_status, timestamp, detail)"
                " VALUES (?,?,?,?,?)",
                (
                    event.task_id,
                    event.from_status,
                    event.to_status,
                    event.timestamp,
                    event.detail,
                ),
            )
            self._conn.commit()

    def get_transitions(self, research_id: str) -> List[StateTransition]:
        rows = self._conn.execute(
            "SELECT task_id, from_status, to_status, timestamp, detail "
            "FROM transitions WHERE task_id = ? ORDER BY id",
            (research_id,),
        ).fetchall()
        return [StateTransition(*r) for r in rows]

    # -- sources -------------------------------------------------------------

    def upsert_source(self, research_id: str, source: ResearchSource) -> bool:
        """Insert unless this exact page was already recorded for the task.

        Returns True when newly inserted. Existing records keep their
        original retrieval provenance; refreshed metadata updates in place.
        """
        canonical = normalize_url(source.url)
        page_key = dedup_key(source.url)
        with self._lock:
            existing = self._conn.execute(
                "SELECT source_id FROM sources WHERE task_id=? AND page_key=?",
                (research_id, page_key),
            ).fetchone()
            if existing:
                source.source_id = existing[0]
                self._conn.execute(
                    "UPDATE sources SET content_hash=?, quarantined=?,"
                    " quality_score=?, data=? WHERE source_id=?",
                    (
                        source.content_hash,
                        1 if source.quarantined else 0,
                        source.quality_score,
                        json.dumps(source.to_dict()),
                        existing[0],
                    ),
                )
                self._conn.commit()
                return False
            self._conn.execute(
                "INSERT INTO sources (source_id, task_id, url, canonical_url,"
                " page_key, domain, content_hash, retrieved_at, quarantined,"
                " quality_score, data) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    source.source_id,
                    research_id,
                    source.url,
                    canonical,
                    page_key,
                    source.domain,
                    source.content_hash,
                    source.retrieved_at,
                    1 if source.quarantined else 0,
                    source.quality_score,
                    json.dumps(source.to_dict()),
                ),
            )
            self._conn.commit()
            return True

    def list_sources(self, research_id: str) -> List[ResearchSource]:
        rows = self._conn.execute(
            "SELECT data FROM sources WHERE task_id=? ORDER BY retrieved_at",
            (research_id,),
        ).fetchall()
        return [ResearchSource.from_dict(json.loads(r[0])) for r in rows]

    def count_sources_with_hash(
        self, research_id: str, content_hash: str
    ) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM sources WHERE task_id=? AND content_hash=?",
            (research_id, content_hash),
        ).fetchone()
        return int(row[0]) if row else 0

    # -- claims / evidence / contradictions ----------------------------------

    def add_claim(self, research_id: str, claim: Claim) -> bool:
        """Idempotent by normalized text within the task."""
        norm = " ".join(claim.text.lower().split())
        existing = self._conn.execute(
            "SELECT claim_id, data FROM claims WHERE task_id=?", (research_id,)
        ).fetchall()
        for cid, data in existing:
            stored = json.loads(data)
            if " ".join(str(stored.get("text", "")).lower().split()) == norm:
                claim.claim_id = cid
                return False
        with self._lock:
            self._conn.execute(
                "INSERT INTO claims (claim_id, task_id, kind, status, text,"
                " created_at, data) VALUES (?,?,?,?,?,?,?)",
                (
                    claim.claim_id,
                    research_id,
                    claim.kind.value,
                    claim.status.value,
                    claim.text,
                    claim.created_at,
                    json.dumps(claim.to_dict()),
                ),
            )
            self._conn.commit()
        return True

    def update_claim(self, research_id: str, claim: Claim) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE claims SET kind=?, status=?, text=?, data=? WHERE claim_id=?",
                (
                    claim.kind.value,
                    claim.status.value,
                    claim.text,
                    json.dumps(claim.to_dict()),
                    claim.claim_id,
                ),
            )
            self._conn.commit()

    def list_claims(self, research_id: str) -> List[Claim]:
        rows = self._conn.execute(
            "SELECT data FROM claims WHERE task_id=? ORDER BY created_at",
            (research_id,),
        ).fetchall()
        return [Claim.from_dict(json.loads(r[0])) for r in rows]

    def add_evidence(self, research_id: str, evidence: Evidence) -> bool:
        with self._lock:
            dup = self._conn.execute(
                "SELECT 1 FROM evidence WHERE claim_id=? AND source_id=? AND location=?",
                (evidence.claim_id, evidence.source_id, evidence.location),
            ).fetchone()
            if dup:
                return False
            self._conn.execute(
                "INSERT INTO evidence (evidence_id, task_id, claim_id,"
                " source_id, location, created_at, data) VALUES (?,?,?,?,?,?,?)",
                (
                    evidence.evidence_id,
                    research_id,
                    evidence.claim_id,
                    evidence.source_id,
                    evidence.location,
                    evidence.retrieved_at,
                    json.dumps(evidence.to_dict()),
                ),
            )
            self._conn.commit()
        return True

    def list_evidence(self, research_id: str) -> List[Evidence]:
        rows = self._conn.execute(
            "SELECT data FROM evidence WHERE task_id=?", (research_id,)
        ).fetchall()
        return [Evidence.from_dict(json.loads(r[0])) for r in rows]

    def add_contradiction(self, research_id: str, contradiction: Contradiction) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO contradictions (contradiction_id,"
                " task_id, claim_a_id, claim_b_id, data) VALUES (?,?,?,?,?)",
                (
                    contradiction.contradiction_id,
                    research_id,
                    contradiction.claim_a_id,
                    contradiction.claim_b_id,
                    json.dumps(contradiction.to_dict()),
                ),
            )
            self._conn.commit()

    def list_contradictions(self, research_id: str) -> List[Contradiction]:
        rows = self._conn.execute(
            "SELECT data FROM contradictions WHERE task_id=?", (research_id,)
        ).fetchall()
        out = []
        for r in rows:
            d = json.loads(r[0])
            d["resolved_status"] = ClaimStatus(
                d.get("resolved_status", ClaimStatus.CONTRADICTED.value)
            )
            known = {f for f in Contradiction.__dataclass_fields__}
            out.append(Contradiction(**{k: v for k, v in d.items() if k in known}))
        return out

    # -- progress events ------------------------------------------------------

    def log_event(self, research_id: str, kind: str, detail: str = "") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO events (task_id, timestamp, kind, detail)"
                " VALUES (?,?,?,?)",
                (research_id, time.time(), kind, detail),
            )
            self._conn.commit()

    def get_events(self, research_id: str) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT timestamp, kind, detail FROM events WHERE task_id=? ORDER BY id",
            (research_id,),
        ).fetchall()
        return [
            {"timestamp": r[0], "kind": r[1], "detail": r[2]} for r in rows
        ]

    # -- budget bookkeeping ----------------------------------------------------

    def usage(self, research_id: str) -> Dict[str, float]:
        queries = self._conn.execute(
            "SELECT COUNT(DISTINCT detail) FROM events WHERE task_id=? AND kind='query'",
            (research_id,),
        ).fetchone()[0]
        pages = self._conn.execute(
            "SELECT COUNT(*) FROM sources WHERE task_id=? AND content_hash != ''",
            (research_id,),
        ).fetchone()[0]
        return {"queries": float(queries), "pages": float(pages)}

    # -- knowledge graph ------------------------------------------------------

    def save_graph(self, research_id: str, graph) -> None:
        import time as _time

        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO kg_graphs (task_id, updated_at, data)"
                " VALUES (?,?,?)",
                (research_id, _time.time(), json.dumps(graph.to_dict())),
            )
            self._conn.commit()

    def load_graph(self, research_id: str):
        from agent.research.knowledge_graph import ResearchKnowledgeGraph

        row = self._conn.execute(
            "SELECT data FROM kg_graphs WHERE task_id=?", (research_id,)
        ).fetchone()
        if not row:
            return ResearchKnowledgeGraph()
        return ResearchKnowledgeGraph.from_dict(json.loads(row[0]))

    # -- domain risk history (P19) -------------------------------------------

    def bump_domain(self, registrable: str, field: str = "fetches") -> None:
        import time as _time

        if field not in ("fetches", "quarantined", "blocked", "duplicates"):
            raise ValueError(f"unknown domain stat: {field}")
        with self._lock:
            self._conn.execute(
                "INSERT INTO domain_stats (registrable, " + field + ", last_seen)"
                " VALUES (?,?,?) ON CONFLICT(registrable) DO UPDATE SET "
                + field + " = " + field + " + 1, last_seen = ?",
                (registrable, 1, _time.time(), _time.time()),
            )
            self._conn.commit()

    def domain_risk_factor(self, registrable: str) -> float:
        """0.0 (clean/unknown) .. 1.0 (every past fetch was quarantined)."""
        row = self._conn.execute(
            "SELECT fetches, quarantined, blocked FROM domain_stats"
            " WHERE registrable=?",
            (registrable,),
        ).fetchone()
        if not row:
            return 0.0
        fetches, quarantined, blocked = row
        bad = quarantined + blocked
        if fetches <= 0:
            return min(1.0, bad / 5.0)
        return min(1.0, bad / max(1, fetches))

    def reset(self) -> None:
        """Delete all research state (test helper)."""
        with self._lock:
            for table in (
                "tasks",
                "transitions",
                "sources",
                "claims",
                "evidence",
                "contradictions",
                "events",
                "kg_graphs",
                "domain_stats",
            ):
                self._conn.execute(f"DELETE FROM {table}")
            self._conn.commit()
