"""Temporal research: dates, as-of semantics, timelines, change detection.

(P41) Reports carry an explicit as-of stamp and historical/current info is
never silently mixed — claims with dates are grouped by year in the report
layer. (P42) compares two retrieved texts structurally. (P43) builds a
chronological timeline where every event carries provenance.
"""

from __future__ import annotations

import difflib
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

_ISO_DATE_RE = re.compile(
    r"\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b"
)
_SLASH_DATE_RE = re.compile(r"\b(20\d{2})/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])\b")
_MONTHS = {
    m.lower(): i + 1
    for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"]
    )
}
_LONG_DATE_RE = re.compile(
    r"\b(" + "|".join(_MONTHS) + r")\s+(0?[1-9]|[12]\d|3[01]),?\s+(20\d{2})\b",
    re.I,
)
_YEAR_RE = re.compile(r"\b(19[89]\d|20[0-4]\d)\b")


@dataclass(frozen=True)
class ExtractedDate:
    iso: str
    kind: str


def extract_dates(text: str) -> List[ExtractedDate]:
    """Extract normalized dates; ISO > long-form > bare year (kind marks it)."""
    found: List[ExtractedDate] = []
    seen = set()

    def add(iso: str, kind: str) -> None:
        if iso not in seen:
            seen.add(iso)
            found.append(ExtractedDate(iso=iso, kind=kind))

    for match in _ISO_DATE_RE.finditer(text):
        add(match.group(0), "iso")
    for match in _SLASH_DATE_RE.finditer(text):
        y, m, d = match.groups()
        add(f"{y}-{m}-{d}", "slash")
    for match in _LONG_DATE_RE.finditer(text):
        month = _MONTHS[match.group(1).lower()]
        day = int(match.group(2))
        add(f"{match.group(3)}-{month:02d}-{day:02d}", "long_form")
    if not found:
        for match in _YEAR_RE.finditer(text):
            add(match.group(1), "year_only")
    return sorted(found, key=lambda d: d.iso)


def primary_date(text: str) -> Optional[str]:
    dates = extract_dates(text)
    return dates[0].iso if dates else None


def as_of_stamp(now: Optional[float] = None) -> str:
    """P41: every report states the moment its evidence was current."""
    return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(now or time.time()))


# ---------------------------------------------------------------------------
# P42 change detection
# ---------------------------------------------------------------------------


@dataclass
class ChangeReport:
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    changed: List[Tuple[str, str]] = field(default_factory=list)
    unchanged_ratio: float = 0.0

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)

    def summary(self) -> str:
        verb_bits = []
        if self.added:
            verb_bits.append(f"+{len(self.added)}")
        if self.removed:
            verb_bits.append(f"-{len(self.removed)}")
        if self.changed:
            verb_bits.append(f"~{len(self.changed)}")
        return ("no changes" if not verb_bits else " ".join(verb_bits)) + (
            f" (unchanged {self.unchanged_ratio:.0%})"
        )


def detect_changes(old_text: str, new_text: str, rename_threshold: float = 0.75):
    """Line-level diff classifying added/removed/changed lines."""
    old_lines = [ln.strip() for ln in (old_text or "").splitlines() if ln.strip()]
    new_lines = [ln.strip() for ln in (new_text or "").splitlines() if ln.strip()]
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    report = ChangeReport()
    matched_old = 0
    old_consumed = [False] * len(old_lines)
    new_consumed = [False] * len(new_lines)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            matched_old += i2 - i1
            for idx in range(i1, i2):
                old_consumed[idx] = True
            for idx in range(j1, j2):
                new_consumed[idx] = True
    # pair near-identical removed/added lines as "changed"
    removed_pool = [ln for i, ln in enumerate(old_lines) if not old_consumed[i]]
    for j, ln in enumerate(new_lines):
        if new_consumed[j]:
            continue
        best = None
        best_ratio = 0.0
        for candidate in removed_pool:
            ratio = difflib.SequenceMatcher(None, candidate, ln).ratio()
            if ratio > best_ratio:
                best, best_ratio = candidate, ratio
        if best is not None and best_ratio >= rename_threshold:
            report.changed.append((best, ln))
            removed_pool.remove(best)
        else:
            report.added.append(ln)
    report.removed = list(removed_pool)
    total = max(1, len(old_lines) + len(new_lines))
    report.unchanged_ratio = (2 * matched_old) / total
    return report


def classify_change_kind(change: ChangeReport) -> List[str]:
    """Map raw diff to P42 vocabulary: added/removed/changed/deprecated."""
    kinds = []
    if change.added:
        kinds.append("added")
    if change.removed:
        kinds.append("removed")
    if change.changed:
        kinds.append("changed")
    joined = " ".join(change.removed).lower()
    if any(w in joined for w in ("deprecated", "removed support", "no longer")):
        kinds.append("deprecated")
    return kinds or ["unchanged"]


# ---------------------------------------------------------------------------
# P43 fact timeline
# ---------------------------------------------------------------------------


@dataclass
class TimelineEvent:
    date_iso: str
    text: str
    source_ids: List[str] = field(default_factory=list)
    precision: str = "day"

    def to_dict(self) -> Dict:
        return dict(self.__dict__)


def build_timeline(dated_items: List[Tuple[str, str, List[str]]],
                   require_day_precision: bool = False) -> List[TimelineEvent]:
    """Chronological timeline from (text, date_or_None, source_ids) tuples.

    Events without dates are EXCLUDED rather than guessed — provenance over
    completeness. Year-only dates are flagged via precision.
    """
    events: List[TimelineEvent] = []
    for text, date_iso, source_ids in dated_items:
        if not date_iso:
            continue
        precision = "year" if re.fullmatch(r"\d{4}", date_iso) else (
            "month" if re.fullmatch(r"\d{4}-\d{2}", date_iso) else "day"
        )
        if require_day_precision and precision != "day":
            continue
        events.append(
            TimelineEvent(date_iso=date_iso, text=text,
                          source_ids=list(source_ids), precision=precision)
        )
    events.sort(key=lambda e: e.date_iso)
    return events
