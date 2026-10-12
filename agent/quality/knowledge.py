"""Regression knowledge base + known-issues database (P80-81).

Seeded from the documented Master 17-19 pre-existing failure clusters so the
regression engine can classify them PRE_EXISTING instead of NEW.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from agent.quality.models import KnownIssue, KnowledgeEntry


class RegressionKnowledgeBase:
    def __init__(self):
        self._entries: Dict[str, KnowledgeEntry] = {}

    def add(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        self._entries[entry.entry_id] = entry
        return entry

    def lookup_by_component(self, component: str) -> List[KnowledgeEntry]:
        return [e for e in self._entries.values()
                if e.component.lower() == component.lower()]

    def lookup_by_failure(self, substring: str) -> List[KnowledgeEntry]:
        return [e for e in self._entries.values()
                if substring.lower() in e.failure.lower()]

    def all(self) -> List[KnowledgeEntry]:
        return sorted(self._entries.values(), key=lambda e: e.entry_id)


class KnownIssuesDatabase:
    def __init__(self):
        self._issues: Dict[str, KnownIssue] = {}

    def register(self, issue: KnownIssue) -> KnownIssue:
        self._issues[issue.issue_id] = issue
        return issue

    def get(self, issue_id: str) -> Optional[KnownIssue]:
        return self._issues.get(issue_id)

    def open_issues(self, severity: str = "") -> List[KnownIssue]:
        return [i for i in self._issues.values()
                if i.status == "open"
                and (not severity or i.severity == severity)]

    def close(self, issue_id: str, *, status: str = "fixed") -> bool:
        issue = self._issues.get(issue_id)
        if issue is None:
            return False
        issue.status = status
        return True

    def all(self) -> List[KnownIssue]:
        return sorted(self._issues.values(), key=lambda i: i.issue_id)


def seed_documented_issues(db: KnownIssuesDatabase) -> None:
    """Seed with the pre-existing clusters documented in M17-M19 reports.
    These are environment/platform drift, not Master 20 regressions."""
    documented = [
        ("KI-WINDOWS-PTY", "Windows PTY/setup/update suite failures",
         "high", "run POSIX CI shard for authoritative results"),
        ("KI-DISPLAY-STRINGS", "display string drift ('tasks' vs 'task(s)')",
         "low", "update display tests alongside copy changes"),
        ("KI-NOUS-IMPORTS", "nous credits tests import removed private symbol",
         "medium", "refresh tests against current nous_account API"),
        ("KI-MEMINTEL-FABRIC", "memory-intelligence fabric test failures (62)",
         "medium", "pre-M18 baseline; tracked separately"),
        ("KI-MULTIMODAL", "multimodal security/performance cluster",
         "medium", "pre-existing; tracked separately"),
        ("KI-KANBAN-STRESS", "kanban stress scripts: stale attr + dangling run",
         "low", "opt-in scripts; kanban-domain follow-up"),
    ]
    for iid, title, sev, workaround in documented:
        db.register(KnownIssue(
            issue_id=iid, title=title, severity=sev,
            workaround=workaround, status="open", owner="platform",
            affected_versions=["pre-M17"],
        ))
