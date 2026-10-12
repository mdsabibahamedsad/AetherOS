"""
MASTER 14 knowledge integration for computer-use (Master 15 Phase 89 + 90).

Bridges retrieval into targeting as **DATA, never AUTHORITY**:

- Sources: local UI-pattern memory (always) and, when available, the
  ``aetheros_memory_intelligence`` fabric (guarded import — optional).
- Every hint carries: text, confidence, provenance, created/updated stamps,
  and a computed ``stale`` flag (age > max_age_days).
- Injection-safety: hint text containing instruction-shaped content is
  DOWNGRADED to an inert marker before it ever reaches the planner/targeter
  (Phase 90-of-prompt / knowledge-poisoning defense). Hints can therefore
  never carry permissions, commands-to-run, or approval overrides — they are
  consumed only as *candidate search strings*.
- Retrieval is optional: callers that ask with ``require=False`` get an empty
  result instead of a failure, so tasks that need no knowledge pay nothing.

Credential safety reuses pattern_memory's redact-then-refuse sanitizer; any
hint whose sanitized form still contains secret-shaped content is dropped.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MAX_AGE_DAYS = 45.0

# Instruction-shaped fragments that make a hint INERT for planning purposes.
_INJECTION_MARKERS = re.compile(
    r"(ignore\s+(all\s+|any\s+)?(previous|prior)\s+instructions?"
    r"|disregard\s+(all\s+)?(previous|prior|your)\s+"
    r"|you\s+are\s+now\s+"
    r"|system\s*:\s*"
    r"|\bsudo\b|\brm\s+-rf\b|\bmkfs\b|curl\s+[^|]*\|\s*(sh|bash))"
    , re.IGNORECASE)

_INERT_REPLACEMENT = "[knowledge entry withheld: instruction-shaped content]"


@dataclass
class KnowledgeHint:
    """A single retrieval hint. DATA ONLY."""
    text: str
    confidence: float
    source: str                      # "ui_pattern_memory" | "memory_fabric:<id>"
    provenance: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0
    stale: bool = False
    inert: bool = False              # True → use ONLY as opaque string, no semantics

    def as_search_hint(self) -> str:
        """Safe form for the targeter: inert hints collapse to their marker."""
        if self.inert:
            return _INERT_REPLACEMENT
        return self.text


def _sanitize_hint_text(text: str) -> Optional[str]:
    """Drop secrets; None ⇒ unusable hint."""
    try:
        from agent.redact import redact_sensitive_text as _redact
    except Exception:
        _redact = None
    cleaned = str(text or "")
    if _redact is not None:
        try:
            cleaned = _redact(cleaned)
        except Exception:
            pass
    lowered = cleaned.lower()
    for token in ("sk-", "ghp_", "begin rsa private key", "aws_secret_access_key="):
        if token in lowered:
            return None
    return cleaned.strip()


def _mark_inert_if_instruction_shaped(text: str) -> str:
    if _INJECTION_MARKERS.search(text or ""):
        return _INERT_REPLACEMENT
    return text


def _age_stale(updated_at: float, max_age_days: float) -> bool:
    if not updated_at:
        return True
    return (time.time() - updated_at) > max_age_days * 86400.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def retrieve_hints(
    site_key: str,
    query: str = "",
    *,
    max_age_days: float = DEFAULT_MAX_AGE_DAYS,
    include_patterns_memory: bool = True,
    fabric_query_fn: Optional[Any] = None,
    limit: int = 5,
) -> List[KnowledgeHint]:
    """Collect candidate hints. Never raises; empty list is a valid answer.

    ``fabric_query_fn`` is an OPTIONAL injectable callable wired by hosts that
    run MASTER 14 (signature: fn(query:str) -> iterable of objects/dicts with
    .content/.text, .confidence/.trust, .id, .updated_at). Aetheros core does
    not force one — Phase 89 requirement #12 (retrieval not mandatory).
    """
    hints: List[KnowledgeHint] = []

    if include_patterns_memory:
        try:
            from aetheros_computer.pattern_memory import recall_patterns

            for p in recall_patterns(site_key, min_confidence=0.2):
                text = p.get("pattern", "")
                safe = _sanitize_hint_text(text)
                if not safe:
                    continue
                updated = float(p.get("updated_at") or 0)
                hints.append(KnowledgeHint(
                    text=_mark_inert_if_instruction_shaped(safe),
                    confidence=float(p.get("effective_confidence",
                                           p.get("confidence", 0.5))),
                    source="ui_pattern_memory",
                    provenance={"site_key": site_key,
                                "selector_hint": p.get("selector_hint", ""),
                                "uses": p.get("uses", 1)},
                    created_at=float(p.get("created_at") or 0),
                    updated_at=updated,
                    stale=_age_stale(updated, max_age_days),
                ))
        except Exception:
            logger.debug("pattern-memory recall failed", exc_info=True)

    if fabric_query_fn is not None:
        try:
            for row in (fabric_query_fn(query or site_key) or [])[:limit]:
                get = (lambda k, d="": (row.get(k, d) if isinstance(row, dict)
                                        else getattr(row, k, d)))
                raw_text = str(get("content", get("text", "")))
                safe = _sanitize_hint_text(raw_text)
                if not safe:
                    continue
                trust = get("trust", get("confidence", 0.4))
                try:
                    conf = 0.4 + 0.1 * float(trust)   # VERIFIED≈0.5+
                except (TypeError, ValueError):
                    conf = 0.4
                updated = float(get("updated_at", 0) or 0)
                hints.append(KnowledgeHint(
                    text=_mark_inert_if_instruction_shaped(safe),
                    confidence=conf,
                    source=f"memory_fabric:{get('id', '')}",
                    provenance={"boundary": "user"},
                    created_at=updated,
                    updated_at=updated,
                    stale=_age_stale(updated, max_age_days),
                ))
        except Exception:
            logger.debug("fabric retrieval failed (optional)", exc_info=True)

    # Stale hints keep visibility but are demoted below fresh ones.
    hints.sort(key=lambda h: (h.stale, -h.confidence))
    return hints[:limit]


def hints_to_targeter_inputs(hints: List[KnowledgeHint]) -> List[str]:
    """Extract safe candidate strings for VisualTargeter (Phase 3 wiring).

    Inert entries become their opaque marker so a poisoned record can never
    steer a click; selector_hints from pattern memory pass through only when
    the entry is non-inert AND carries one explicitly stored at write time.
    """
    out: List[str] = []
    for h in hints:
        out.append(h.as_search_hint())
        if not h.inert:
            sel = str(h.provenance.get("selector_hint", "")).strip()
            if sel:
                out.append(sel)
    return [s for s in out if s]


__all__ = [
    "KnowledgeHint",
    "retrieve_hints",
    "hints_to_targeter_inputs",
]
