"""Regression engine (P23-27): before/after classification, flaky tracking,
explicit-reason quarantine, prioritized execution order."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set, Tuple

from agent.quality.models import FailureClassification, QuarantineEntry


@dataclass
class SuiteResult:
    """Normalized before/after test results (test_id -> passed)."""

    passed: Set[str] = field(default_factory=set)
    failed: Set[str] = field(default_factory=set)

    @classmethod
    def from_lists(cls, passed: Iterable[str], failed: Iterable[str]) -> "SuiteResult":
        return cls(passed=set(passed), failed=set(failed))


def classify_regressions(before: SuiteResult,
                         after: SuiteResult,
                         *,
                         known_flaky: Set[str] = (),
                         environmental_markers: Iterable[str] = (),
                         expected_change_tests: Iterable[str] = ()) -> Dict[str, FailureClassification]:
    """P24 — classify every test that appears in either run.

    Precedence: EXPECTED_CHANGE > ENVIRONMENTAL > FLAKY > NEW/FIXED/PRE_EXISTING.
    """
    env_markers = tuple(environmental_markers)
    expected = set(expected_change_tests)
    flaky = set(known_flaky)
    out: Dict[str, FailureClassification] = {}
    all_ids = before.passed | before.failed | after.passed | after.failed
    for tid in all_ids:
        was_fail = tid in before.failed
        is_fail = tid in after.failed
        if tid in expected:
            out[tid] = FailureClassification.EXPECTED_CHANGE
        elif is_fail and any(m in tid for m in env_markers):
            out[tid] = FailureClassification.ENVIRONMENTAL
        elif tid in flaky:
            out[tid] = FailureClassification.FLAKY
        elif is_fail and not was_fail:
            out[tid] = FailureClassification.NEW_FAILURE
        elif was_fail and not is_fail:
            out[tid] = FailureClassification.FIXED_FAILURE
        elif was_fail and is_fail:
            out[tid] = FailureClassification.PRE_EXISTING_FAILURE
    return out


class FlakyTracker:
    """P25 — failure frequency across repeated runs; flaky = intermittent,
    i.e. observed in BOTH passing and failing runs."""

    def __init__(self, threshold_runs: int = 3):
        self.threshold = threshold_runs
        self.history: Dict[str, List[bool]] = {}   # test_id -> [failed?]

    def record(self, test_id: str, failed: bool) -> None:
        self.history.setdefault(test_id, []).append(failed)

    def is_flaky(self, test_id: str) -> bool:
        h = self.history.get(test_id, [])
        if len(h) < self.threshold:
            return False
        window = h[-self.threshold:]
        return any(window) and not all(window)


class QuarantineRegistry:
    """P26 — explicit-reason quarantine; entries stay VISIBLE, never hidden."""

    def __init__(self):
        self._entries: Dict[str, QuarantineEntry] = {}

    def quarantine(self, test_id: str, reason: str,
                   failure_history: Optional[List[str]] = None) -> QuarantineEntry:
        entry = QuarantineEntry(test_id=test_id, reason=reason,
                                failure_history=list(failure_history or []))
        self._entries[test_id] = entry
        return entry

    def release(self, test_id: str) -> bool:
        return self._entries.pop(test_id, None) is not None

    def is_quarantined(self, test_id: str) -> bool:
        return test_id in self._entries

    def visible_entries(self) -> List[QuarantineEntry]:
        """P26 — quarantined tests are always reportable/auditable."""
        return sorted(self._entries.values(), key=lambda e: e.test_id)


#: P27 — prioritization buckets in execution order.
PRIORITIZATION_ORDER = (
    "changed_module",
    "critical_security",
    "critical_regression",
    "golden",
    "broad_suite",
)


def prioritize(changed_modules: Iterable[str],
               test_module_map: Dict[str, str],
               security_tests: Iterable[str] = (),
               critical_regression_tests: Iterable[str] = (),
               golden_tests: Iterable[str] = ()) -> List[str]:
    """Order tests: changed-module first, then security, critical regression,
    golden, then everything else."""
    changed = set(changed_modules)
    buckets: Dict[str, List[str]] = {k: [] for k in PRIORITIZATION_ORDER}
    for tid, module in test_module_map.items():
        if module in changed:
            buckets["changed_module"].append(tid)
        elif tid in set(security_tests):
            buckets["critical_security"].append(tid)
        elif tid in set(critical_regression_tests):
            buckets["critical_regression"].append(tid)
        elif tid in set(golden_tests):
            buckets["golden"].append(tid)
        else:
            buckets["broad_suite"].append(tid)
    out: List[str] = []
    for k in PRIORITIZATION_ORDER:
        out.extend(sorted(buckets[k]))
    return out
