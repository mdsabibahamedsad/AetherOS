"""Dataset loader (P54-59): versioned, integrity-hashed, category-balanced,
hidden-set aware, benchmark-version stamped."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from benchmark.schema import Difficulty, TaskSpec

_DATASETS_DIR = Path(__file__).parent / "datasets"
DATASET_VERSION = "v1"


class DatasetError(Exception):
    pass


def load_tasks(version: str = DATASET_VERSION,
               path: Optional[Path] = None) -> List[TaskSpec]:
    p = path or (_DATASETS_DIR / f"tasks_{version}.json")
    if not p.exists():
        raise DatasetError(f"dataset file missing: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    rows = []
    for row in raw:
        if isinstance(row.get("difficulty"), str):
            row["difficulty"] = Difficulty(row["difficulty"])
        rows.append(TaskSpec(**row))
    return rows


def content_hash(tasks: List[TaskSpec]) -> str:
    payload = json.dumps(
        [t.__dict__ for t in tasks], sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def category_balance(tasks: List[TaskSpec]) -> Dict[str, int]:
    return dict(sorted(Counter(t.category for t in tasks).items()))


def difficulty_balance(tasks: List[TaskSpec]) -> Dict[str, int]:
    return dict(sorted(Counter(t.difficulty.value for t in tasks).items()))


def split_public_hidden(tasks: List[TaskSpec],
                        hidden_fraction: float = 0.15) -> Tuple[
        List[TaskSpec], List[TaskSpec]]:
    """P57 — deterministic split; the hidden slice is excluded from public
    listings and its answers never shipped in reports."""
    hidden: List[TaskSpec] = []
    public: List[TaskSpec] = []
    for t in tasks:
        digest = hashlib.sha256(t.task_id.encode()).hexdigest()
        bucket = int(digest[:8], 16) / 0xFFFFFFFF
        (hidden if bucket < hidden_fraction else public).append(t)
    return public, hidden


def verify_dataset(version: str = DATASET_VERSION) -> Dict[str, object]:
    """P81 quality control: schema validity + balance + integrity report."""
    tasks = load_tasks(version)
    problems: List[str] = []
    seen = set()
    for t in tasks:
        if t.task_id in seen:
            problems.append(f"duplicate task_id {t.task_id}")
        seen.add(t.task_id)
        if not t.objective.strip():
            problems.append(f"{t.task_id}: empty objective")
        if t.validator.get("type") not in _KNOWN_VALIDATORS():
            problems.append(f"{t.task_id}: unknown validator "
                            f"{t.validator.get('type')!r}")
        if not t.sandbox:
            problems.append(f"{t.task_id}: destructive task outside sandbox")
    cats = category_balance(tasks)
    missing_cats = [c for c in _EXPECTED_CATEGORIES if c not in cats]
    if missing_cats:
        problems.append(f"categories missing: {missing_cats}")
    return {
        "version": version,
        "tasks": len(tasks),
        "content_hash": content_hash(tasks),
        "category_balance": cats,
        "difficulty_balance": difficulty_balance(tasks),
        "problems": problems,
        "ok": not problems,
    }


def _KNOWN_VALIDATORS() -> Tuple[str, ...]:
    from benchmark.validators import VALIDATOR_TYPES
    return VALIDATOR_TYPES


_EXPECTED_CATEGORIES = (
    "01_basic_response", "02_planning", "03_reasoning", "04_research",
    "05_web", "06_browser", "07_computer_use", "08_coding", "09_debugging",
    "10_testing", "11_file_operations", "12_terminal",
    "13_multi_step_automation", "14_long_horizon", "15_memory",
    "16_multi_agent", "17_mcp", "18_reliability", "19_recovery",
    "20_security", "21_performance", "22_stress", "23_cost_efficiency",
    "24_e2e_os",
)
