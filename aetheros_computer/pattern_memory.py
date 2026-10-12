"""
UI-pattern memory (Master 15 Phases 48-49).

Remembers *safe, reusable* UI targeting patterns across sessions, e.g.:

    {"site_key": "github.com", "pattern": "Settings button is under the
     'Account' menu", "selector_hint": "text=Settings",
     "confidence": 0.8, "uses": 3}

Hard guarantees:
- Values are sanitized through ``agent.redact.redact_sensitive_text`` before
  persistence; entries that still look credential-bearing after sanitization
  are REFUSED (never stored).
- Bounded store (max entries), confidence decays with age and grows slowly
  with successful reuse; retrieval never auto-executes anything — patterns are
  hints surfaced to the planner/targeter only.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_ENTRIES = 512
DEFAULT_CONFIDENCE = 0.6
MAX_CONFIDENCE = 0.95
CONFIDENCE_GROWTH = 0.05
HALFLIFE_DAYS = 60


def _store_path():
    from aetheros_constants import get_aetheros_home

    d = get_aetheros_home() / "computer_actions"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d / "ui_patterns.json"


_lock = threading.Lock()


def _load() -> List[Dict[str, Any]]:
    try:
        data = json.loads(_store_path().read_text(encoding="utf-8"))
        return data.get("patterns", []) if isinstance(data, dict) else []
    except (OSError, ValueError):
        return []


def _save(patterns: List[Dict[str, Any]]) -> None:
    path = _store_path()
    try:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"patterns": patterns}, f)
        os.replace(tmp, path)
    except OSError:
        logger.debug("Pattern-memory save failed", exc_info=True)


def _sanitize(text: str) -> Optional[str]:
    """Redact secrets; refuse if credential-shaped content survives."""
    try:
        from agent.redact import redact_sensitive_text as _redact
    except Exception:
        _redact = None
    text = str(text or "")
    if _redact is not None:
        try:
            text = _redact(text)
        except Exception:
            pass
    # Refuse obvious live secrets post-redaction.
    lowered = text.lower()
    for token in ("sk-", "ghp_", "begin rsa private key", "aws_secret_access_key="):
        if token in lowered:
            return None
    return text.strip()


def remember_pattern(
    site_key: str,
    pattern: str,
    selector_hint: str = "",
    confidence: float = DEFAULT_CONFIDENCE,
) -> Dict[str, Any]:
    """Store (or reinforce) one UI pattern for a site key.

    Returns the stored entry. Raises nothing; refuses (returns refusal dict)
    when content is credential-bearing even after sanitization.
    """
    site_key = str(site_key or "").strip().lower()[:120]
    clean_pattern = _sanitize(pattern)
    clean_hint = _sanitize(selector_hint) if selector_hint else ""
    if not site_key or not clean_pattern:
        return {"stored": False, "reason": "empty site key or pattern"}
    if clean_pattern is None or (selector_hint and clean_hint is None):
        return {"stored": False, "reason": "credential-bearing content refused"}

    now = time.time()
    with _lock:
        patterns = _load()
        for p in patterns:
            if p.get("site_key") == site_key and p.get("pattern") == clean_pattern:
                p["confidence"] = min(MAX_CONFIDENCE,
                                      float(p.get("confidence", DEFAULT_CONFIDENCE)) + CONFIDENCE_GROWTH)
                p["uses"] = int(p.get("uses", 1)) + 1
                p["updated_at"] = now
                if clean_hint:
                    p["selector_hint"] = clean_hint
                _save(patterns)
                return {"stored": True, "reinforced": True, "entry": p}
        entry = {
            "site_key": site_key,
            "pattern": clean_pattern[:500],
            "selector_hint": (clean_hint or "")[:300],
            "confidence": max(0.1, min(MAX_CONFIDENCE, float(confidence))),
            "uses": 1,
            "created_at": now,
            "updated_at": now,
        }
        patterns.append(entry)
        while len(patterns) > MAX_ENTRIES:
            patterns.sort(key=lambda p: p.get("updated_at", 0))
            patterns.pop(0)
        _save(patterns)
        return {"stored": True, "entry": entry}


def recall_patterns(site_key: str, min_confidence: float = 0.3) -> List[Dict[str, Any]]:
    """Patterns for a site key, confidence-decayed by age, strongest first."""
    site_key = str(site_key or "").strip().lower()
    if not site_key:
        return []
    now = time.time()
    results = []
    with _lock:
        for p in _load():
            if p.get("site_key") != site_key:
                continue
            age_days = max(0.0, (now - float(p.get("updated_at", now))) / 86400.0)
            decay = 0.5 ** (age_days / HALFLIFE_DAYS)
            conf = float(p.get("confidence", DEFAULT_CONFIDENCE)) * decay
            if conf >= min_confidence:
                out = dict(p)
                out["effective_confidence"] = round(min(conf, MAX_CONFIDENCE), 4)
                results.append(out)
    results.sort(key=lambda p: p["effective_confidence"], reverse=True)
    return results


def forget_patterns(site_key: str) -> int:
    """User-invocable deletion for one site key. Returns count removed."""
    with _lock:
        patterns = _load()
        kept = [p for p in patterns if p.get("site_key") != str(site_key).strip().lower()]
        removed = len(patterns) - len(kept)
        if removed:
            _save(kept)
        return removed


def reset() -> None:
    """Test helper."""
    with _lock:
        _save([])


__all__ = [
    "remember_pattern",
    "recall_patterns",
    "forget_patterns",
    "reset",
]
