"""Memory lifecycle engine — layered on the built-in MemoryStore.

This module implements the lifecycle features that keep curated memory
healthy, private, and durable:

  * confidence scoring (per-entry, on write and on demand)
  * conflict detection + resolution (attribute contradictions, polarity
    flips, near-duplicates)
  * secret security (detection, redaction, purge of credential-shaped
    content)
  * per-entry permissions (private / shared / public / agent) + scope
    gating
  * agent isolation (owner-scoped visibility)
  * controlled sharing (explicit ``shared_with`` grants)
  * optional decay (TTL expiry + access-weighted confidence decay)
  * reconsolidation / deduplication (near-dup merge, budget reclaim)
  * enhanced search ranking (token overlap + confidence + recency)
  * failure recovery (pre-image journal, corruption repair)

Design rules
------------
* **No model-tool schema lives here.** The ``memory`` tool calls into
  this module; nothing here adds per-API-call footprint (see the
  Footprint Ladder in AGENTS.md — this is rung 1, extending existing
  code).
* **One-way dependency.** This module NEVER imports ``tools.memory_tool``.
  It operates on a duck-typed store exposing the ``MemoryStore`` surface
  (``memory_entries`` / ``user_entries`` dicts keyed by scope,
  ``_entries_for`` / ``_set_entries``, ``_path_for``, ``save_to_disk``,
  ``owner``).  That keeps imports acyclic and lets the layer be tested in
  isolation.
* **Backward compatible.** Entries may be plain strings (legacy) or
  enhanced JSON ``{"text": .., "metadata": ..}``.  Both are handled by
  every reader here.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Entry format helpers (duck-typed; never import memory_tool here)
# ---------------------------------------------------------------------------


def entry_text(entry: Any) -> str:
    """Return the user-visible text of an entry (plain or enhanced JSON)."""
    if isinstance(entry, str):
        stripped = entry.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                parsed = json.loads(stripped)
            except (json.JSONDecodeError, TypeError):
                return entry
            if isinstance(parsed, dict) and "text" in parsed:
                return str(parsed["text"])
        return entry
    return str(entry)


def entry_metadata(entry: Any) -> Dict[str, Any]:
    """Return the metadata dict of an entry (empty dict for plain/legacy)."""
    if isinstance(entry, str):
        stripped = entry.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                parsed = json.loads(stripped)
            except (json.JSONDecodeError, TypeError):
                return {}
            if isinstance(parsed, dict) and "text" in parsed:
                md = parsed.get("metadata")
                return md if isinstance(md, dict) else {}
        return {}
    return {}


def make_entry(text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Serialize an entry.  Plain text when no metadata, JSON otherwise."""
    if metadata is None:
        return text
    return json.dumps({"text": text, "metadata": metadata}, ensure_ascii=False)


def _now() -> float:
    return time.time()


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

_DEFINITE_VERBS = ("is", "are", "was", "were", "will be", "has been", "have been")
_TEMPORAL_TERMS = (
    "today", "yesterday", "tomorrow", "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "sunday", "january", "february",
    "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december", "hour", "minute", "second",
    "day", "week", "month", "year",
)
_PERSONAL_INDICATORS = (
    "i am", "i'm", "my name", "i work", "i live", "i prefer", "i like",
    "i dislike", "i hate", "i love", "i enjoy", "please call me",
)
_HABITUAL_INDICATORS = ("always", "never", "usually", "often", "sometimes", "every", "each")
_EXPLICIT_SAVE = ("remember", "don't forget", "do not forget", "important note", "note that")


def score_confidence(
    content: str,
    *,
    source: str = "memory_write",
    user_content: str = "",
    assistant_content: str = "",
    baseline: float = 0.5,
) -> float:
    """Compute a 0.0–1.0 confidence score for a memory entry.

    Combines content-specificity signals with provenance signals:

    * specificity — numbers, proper nouns, definite verbs, temporal
      anchors (each raises confidence for *concrete* facts)
    * provenance — a fact present in the user's message is more reliable
      than one the assistant inferred; presence in both is strongest
    * salience — personal details and habitual statements about the user
      are treated as higher-confidence than idle observation
    * explicit save intent (``remember`` / ``don't forget``) is a strong
      signal regardless of content
    """
    content = content or ""
    score = max(0.0, min(1.0, baseline))

    cl = content.lower()
    if not content.strip():
        return 0.0

    # Explicit save intent — strongest single signal.
    if any(phrase in cl for phrase in _EXPLICIT_SAVE):
        score += 0.25

    # Specificity.
    specificity = 0.0
    if any(ch.isdigit() for ch in content):
        specificity += 0.1
    if any(word and word[0].isupper() for word in content.split()):
        specificity += 0.1
    length = len(content)
    if 10 <= length <= 120:
        specificity += 0.1
    elif length > 240:
        specificity -= 0.1  # rambling prose is less precise
    if any(v in cl for v in _DEFINITE_VERBS):
        specificity += 0.05
    if any(t in cl for t in _TEMPORAL_TERMS):
        specificity += 0.05
    score += min(specificity, 0.25)

    # Provenance.
    provenance = 0.0
    fact_lower = cl
    in_user = user_content and fact_lower in (user_content or "").lower()
    in_asst = assistant_content and fact_lower in (assistant_content or "").lower()
    if in_user and in_asst:
        provenance += 0.25
    elif in_user and not in_asst:
        provenance += 0.2
    elif in_asst and not in_user:
        provenance += 0.1
    # User-specific personal facts are inherently high-value.
    if any(ind in cl for ind in _PERSONAL_INDICATORS):
        provenance += 0.15
    if any(ind in cl for ind in _HABITUAL_INDICATORS):
        provenance += 0.1
    score += min(provenance, 0.3)

    # Source-based adjustment.
    if source in ("user_input", "user", "correction", "user_correction"):
        score += 0.1
    elif source in ("agent_inference", "assistant"):
        score -= 0.05

    return max(0.0, min(1.0, score))


def confidence_label(conf: float) -> str:
    """Map a confidence score to a coarse label for display/decay logic."""
    if conf >= 0.75:
        return "high"
    if conf >= 0.5:
        return "medium"
    if conf >= 0.25:
        return "low"
    return "very_low"


def ensure_confidence(
    metadata: Dict[str, Any],
    content: str,
    **kw: Any,
) -> Dict[str, Any]:
    """Return ``metadata`` with a ``confidence`` key filled in if absent.

    Never overwrites an explicit caller-supplied confidence.
    """
    md = dict(metadata or {})
    if "confidence" not in md or md["confidence"] is None:
        md["confidence"] = score_confidence(content, **kw)
    try:
        md["confidence"] = max(0.0, min(1.0, float(md["confidence"])))
    except (TypeError, ValueError):
        md["confidence"] = score_confidence(content, **kw)
    return md


def default_metadata(
    content: str,
    *,
    action: str = "add",
    source: str = "memory_tool",
    owner: str = "",
    permission: str = "private",
    ttl: float = 0.0,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the standard provenance envelope for a tool-originated write."""
    now = time.time()
    md: Dict[str, Any] = {
        "source": source,
        "confidence": score_confidence(content, source=source),
        "timestamp": now,
        "write_origin": action,
        "permission": permission,
        "created_at": now,
        "updated_at": now,
        "accessed_at": now,
        "access_count": 0,
        "archived": False,
    }
    if owner:
        md["owner"] = owner
    if ttl and ttl > 0:
        md["ttl"] = float(ttl)
    if extra:
        for k, v in extra.items():
            if v is not None:
                md[k] = v
    return md


# ---------------------------------------------------------------------------
# Secret security
# ---------------------------------------------------------------------------

# Conservative, high-signal credential shapes.  These are anchored on
# well-known token prefixes / PEM blocks / JWT structure / quoted
# assignments — NOT on the bare words "key", "token", or "secret" — so
# legitimate prose like "API keys live in environment variables" never
# matches (see the no-false-positive tests).
_SECRET_PATTERNS: List[Tuple[str, "re.Pattern"]] = [
    ("openai_api_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("anthropic_api_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b")),
    ("github_fine_grained_token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("slack_webhook", re.compile(r"https://hooks\.slack\.com/services/[A-Z0-9]{8,}/[A-Z0-9]{8,}/[A-Za-z0-9]+")),
    ("stripe_secret_key", re.compile(r"\bsk_live_[A-Za-z0-9]{20,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("generic_key_assignment", re.compile(
        r"\b(?:api[_-]?key|token|secret|password|passwd|client[_-]?secret)"
        r"\s*[=:]\s*[\"']?[A-Za-z0-9+/=_-]{24,}[\"']?"
    )),
]

_REDACTED_RE = re.compile(r"\[REDACTED:[^\]]*\]")


def scan_secrets(content: str) -> List[Dict[str, Any]]:
    """Return a list of secret findings ``{type, start, end, sample}``.

    ``sample`` is a short prefix of the match — enough to identify the
    finding class without echoing the full credential into logs.
    """
    if not content:
        return []
    findings: List[Dict[str, Any]] = []
    seen_spans = set()
    for name, pattern in _SECRET_PATTERNS:
        for match in pattern.finditer(content):
            span = (match.start(), match.end())
            if span in seen_spans:
                continue
            seen_spans.add(span)
            findings.append({
                "type": name,
                "start": span[0],
                "end": span[1],
                "sample": content[span[0]:span[0] + 12] + ("…" if span[1] - span[0] > 12 else ""),
            })
    findings.sort(key=lambda f: f["start"])
    return findings


def redact_secrets(content: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Return ``(safe_text, findings)`` with matches replaced by placeholders."""
    findings = scan_secrets(content)
    if not findings:
        return content, findings
    out = content
    # Replace from the end so earlier offsets stay valid.
    for f in sorted(findings, key=lambda f: f["start"], reverse=True):
        out = out[:f["start"]] + f"[REDACTED:{f['type']}]" + out[f["end"]:]
    return out, findings


def secret_check_message(findings: Sequence[Dict[str, Any]]) -> str:
    """Human-readable block message for the first finding (or empty)."""
    if not findings:
        return ""
    types = ", ".join(sorted({f["type"] for f in findings}))
    return (
        f"Blocked: content contains what looks like a real secret "
        f"({types}). Storing live credentials in memory is a security risk — "
        f"they would be injected into the system prompt in future sessions. "
        f"Store the credential in the environment / secret store instead and "
        f"remember only where it lives."
    )


def secrets_report(store: Any) -> Dict[str, Any]:
    """Scan every entry in the store for secrets. Read-only."""
    report: Dict[str, Any] = {"scanned": 0, "findings": [], "by_type": {}}
    for target in ("memory", "user"):
        for scope in _store_scopes(store, target):
            for entry in store._entries_for(target, scope):
                report["scanned"] += 1
                findings = scan_secrets(entry_text(entry))
                if findings:
                    types = [f["type"] for f in findings]
                    for t in types:
                        report["by_type"][t] = report["by_type"].get(t, 0) + 1
                    report["findings"].append({
                        "target": target,
                        "scope": scope,
                        "types": types,
                        "sample": entry_text(entry)[:120],
                    })
    return report


def purge_secrets(
    store: Any,
    *,
    mode: str = "redact",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Scan the store and redact or remove entries containing secrets.

    ``mode``: ``"redact"`` (replace the credential text with a placeholder
    and flag the entry) or ``"remove"`` (drop the whole entry).  Returns a
    report.  ``dry_run=True`` reports without mutating.
    """
    if mode not in ("redact", "remove"):
        raise ValueError(f"purge_secrets: unknown mode {mode!r}")
    report: Dict[str, Any] = {
        "mode": mode,
        "scanned": 0,
        "found": 0,
        "redacted": 0,
        "removed": 0,
        "details": [],
    }
    for target in ("memory", "user"):
        for scope in _store_scopes(store, target):
            entries = store._entries_for(target, scope)
            mutated = False
            for idx in range(len(entries) - 1, -1, -1):
                entry = entries[idx]
                text = entry_text(entry)
                findings = scan_secrets(text)
                if not findings:
                    continue
                report["scanned"] += 1
                report["found"] += 1
                if dry_run:
                    report["details"].append({
                        "target": target, "scope": scope, "index": idx,
                        "types": [f["type"] for f in findings], "action": mode,
                    })
                    continue
                if mode == "redact":
                    safe, _ = redact_secrets(text)
                    md = entry_metadata(entry)
                    md["secret_redacted"] = [f["type"] for f in findings]
                    md["updated_at"] = _now()
                    entries[idx] = make_entry(safe, md)
                    report["redacted"] += 1
                else:
                    entries.pop(idx)
                    report["removed"] += 1
                report["details"].append({
                    "target": target, "scope": scope, "index": idx,
                    "types": [f["type"] for f in findings], "action": mode,
                })
                mutated = True
            if mutated and not dry_run:
                store._set_entries(target, entries, scope)
                store.save_to_disk(target, scope)
                _invalidate_index(store)
    return report


# ---------------------------------------------------------------------------
# Conflict detection & resolution
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> "frozenset[str]":
    return frozenset(re.findall(r"[a-z0-9]+", (text or "").lower()))


def token_similarity(a: str, b: str) -> float:
    """Jaccard similarity over lowercased alphanumeric tokens (0.0–1.0)."""
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


_ATTR_RE = re.compile(
    r"\b(?P<attr>name|first\s+name|last\s+name|email|phone|age|birthday|"
    r"location|city|company|role|job\s+title|team|timezone|language|gender|"
    r"pronouns|website|github|twitter|slack)\b"
    r"\s*(?:is|was|works\s+at|prefers?|likes?|dislikes?|uses?)\s*"
    r"(?P<value>[^\n.]+)"
)


def extract_attributes(text: str) -> List[Tuple[str, str]]:
    """Extract ``(attribute, value)`` pairs from ``text``.

    Matches patterns like ``"Name is Alice"`` / ``"prefers dark mode"`` /
    ``"works at Acme"``.  Values are lowercased and normalized.
    """
    out: List[Tuple[str, str]] = []
    for m in _ATTR_RE.finditer(text or ""):
        attr = re.sub(r"\s+", "_", m.group("attr")).lower().strip(":").strip()
        value = m.group("value").strip().strip(".,;")
        if attr and value and len(value) > 1:
            out.append((attr, value.lower()))
    return out


def _archive_flag(store: Any, entry: Any) -> bool:
    return bool(entry_metadata(entry).get("archived"))


def detect_conflicts(
    store: Any,
    target: str,
    content: str,
    *,
    scope: str = "default",
    near_duplicate_threshold: float = 0.78,
) -> List[Dict[str, Any]]:
    """Return candidate conflicts between ``content`` and existing entries.

    Each candidate::

        {"index", "entry", "kind", "reason", "similarity",
         "attr", "old_value", "new_value"}

    Kinds:
      * ``"attribute"`` — same attribute (name/prefers/…) with a
        *different* value in an existing entry (e.g. "Name is Alice" vs
        "Name is Bob").
      * ``"polarity"`` — same base fact but one is negated ("uses X" vs
        "does not use X").
      * ``"near_duplicate"`` — token similarity above threshold without a
        detected contradiction.
    """
    candidates: List[Dict[str, Any]] = []
    new_tokens = _tokenize(content)
    new_attrs = dict(extract_attributes(content))
    contains_negation = bool(re.search(r"\b(?:not|never|no longer|no more)\b", content or "", re.IGNORECASE))

    entries = store._entries_for(target, scope)
    for idx, entry in enumerate(entries):
        if _archive_flag(store, entry):
            continue
        text = entry_text(entry)
        if text.strip().lower() == content.strip().lower():
            continue  # exact duplicate handled elsewhere
        sim = token_similarity(text, content)
        entry_attrs = dict(extract_attributes(text))
        entry_negation = bool(re.search(r"\b(?:not|never|no longer|no more)\b", text, re.IGNORECASE))
        entry_conflicts: List[Dict[str, Any]] = []

        # Attribute contradiction.
        for attr, new_value in new_attrs.items():
            old_value = entry_attrs.get(attr)
            if old_value and old_value != new_value and sim >= 0.3:
                entry_conflicts.append({
                    "index": idx, "entry": entry, "kind": "attribute",
                    "reason": f"'{attr}' differs: '{old_value}' vs '{new_value}'",
                    "similarity": sim, "attr": attr,
                    "old_value": old_value, "new_value": new_value,
                })

        # Polarity flip: same core tokens, opposite polarity.
        if sim >= 0.55 and contains_negation != entry_negation:
            entry_conflicts.append({
                "index": idx, "entry": entry, "kind": "polarity",
                "reason": "same fact stated with opposite polarity",
                "similarity": sim, "attr": None,
                "old_value": text, "new_value": content,
            })

        # Near-duplicate (only when no harder conflict was found for this
        # entry — attribute/polarity supersede pure redundancy).
        if sim >= near_duplicate_threshold and not any(
            c["kind"] in ("attribute", "polarity") for c in entry_conflicts
        ):
            entry_conflicts.append({
                "index": idx, "entry": entry, "kind": "near_duplicate",
                "reason": f"near-duplicate (token similarity {sim:.2f})",
                "similarity": sim, "attr": None,
                "old_value": text, "new_value": content,
            })

        candidates.extend(entry_conflicts)

    return candidates


def list_conflicts(store: Any) -> Dict[str, Any]:
    """Report all current conflicts across both targets. Read-only."""
    out: Dict[str, Any] = {"conflicts": [], "count": 0}
    for target in ("memory", "user"):
        for scope in _store_scopes(store, target):
            for entry in store._entries_for(target, scope):
                if _archive_flag(store, entry):
                    continue
                text = entry_text(entry)
                found = detect_conflicts(store, target, text, scope=scope)
                for f in found:
                    if f["kind"] == "attribute" or f["kind"] == "polarity":
                        out["conflicts"].append({
                            "target": target, "scope": scope,
                            "index": f["index"], "kind": f["kind"],
                            "reason": f["reason"],
                            "a": text[:120], "b": f["new_value"][:120],
                        })
    out["count"] = len(out["conflicts"])
    return out


def resolve_conflicts(
    store: Any,
    target: str,
    *,
    scope: str = "default",
    policy: str = "keep_best",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Resolve attribute/polarity conflicts for one target.

    ``policy``:
      * ``"keep_best"`` — keep the entry with the higher confidence
        (ties: newer wins); drop the other.
      * ``"keep_newer"`` — always keep the more recently updated entry.
      * ``"keep_private"`` — keep the entry whose permission is more
        restrictive (least shared).

    Returns a report of resolved pairs.  ``dry_run=True`` reports without
    mutating.
    """
    if policy not in ("keep_best", "keep_newer", "keep_private"):
        raise ValueError(f"resolve_conflicts: unknown policy {policy!r}")
    report: Dict[str, Any] = {"resolved": 0, "removed": [], "details": []}
    entries = store._entries_for(target, scope)
    seen_pairs: Set[Tuple[int, int]] = set()
    # Scan newest-first; after a resolution the list shrinks, so restart the
    # scan from the (new) newest entry until no conflicts remain.
    idx = len(entries) - 1
    while idx >= 0:
        entry = entries[idx]
        if _archive_flag(store, entry):
            idx -= 1
            continue
        text = entry_text(entry)
        found = detect_conflicts(store, target, text, scope=scope)
        conflicts = [c for c in found if c["kind"] in ("attribute", "polarity")]
        if not conflicts:
            idx -= 1
            continue
        # The newest entry is the "incoming" fact; the older sibling is
        # the one under test.  Pick the keeper.
        resolved_here = False
        for c in conflicts:
            other_idx = c["index"]
            if other_idx == idx:
                continue
            if other_idx < 0 or other_idx >= len(entries):
                continue
            pair = tuple(sorted((idx, other_idx)))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            other = entries[other_idx]
            other_md = entry_metadata(other)
            self_md = entry_metadata(entry)
            if policy == "keep_best":
                self_conf = float(self_md.get("confidence", 0.5))
                other_conf = float(other_md.get("confidence", 0.5))
                if other_conf > self_conf:
                    keeper_idx, loser_idx = other_idx, idx
                elif other_conf < self_conf:
                    keeper_idx, loser_idx = idx, other_idx
                else:
                    # Tie → newer wins.
                    self_ts = float(self_md.get("updated_at", self_md.get("timestamp", 0)))
                    other_ts = float(other_md.get("updated_at", other_md.get("timestamp", 0)))
                    keeper_idx = idx if self_ts >= other_ts else other_idx
                    loser_idx = other_idx if keeper_idx == idx else idx
            elif policy == "keep_newer":
                self_ts = float(self_md.get("updated_at", self_md.get("timestamp", 0)))
                other_ts = float(other_md.get("updated_at", other_md.get("timestamp", 0)))
                keeper_idx = idx if self_ts >= other_ts else other_idx
                loser_idx = other_idx if keeper_idx == idx else idx
            else:  # keep_private
                self_perm = permission_level(str(self_md.get("permission", "private")))
                other_perm = permission_level(str(other_md.get("permission", "private")))
                keeper_idx = idx if self_perm <= other_perm else other_idx
                loser_idx = other_idx if keeper_idx == idx else idx

            if not dry_run:
                keeper_full = entries[keeper_idx]
                loser_text = entry_text(entries[loser_idx])
                insert_at = min(keeper_idx, loser_idx)
                entries.pop(max(keeper_idx, loser_idx))
                entries.pop(min(keeper_idx, loser_idx))
                entries.insert(insert_at, keeper_full)
                store._set_entries(target, entries, scope)
                store.save_to_disk(target, scope)
                _invalidate_index(store)
                keeper_text = entry_text(keeper_full)
            else:
                keeper_text = entry_text(entries[keeper_idx]) if entries else ""
                loser_text = entry_text(entries[loser_idx]) if entries else ""
            report["resolved"] += 1
            report["removed"].append(loser_text[:80])
            report["details"].append({
                "kind": c["kind"], "reason": c["reason"],
                "kept": keeper_text[:120],
            })
            resolved_here = True
            break  # one conflict per entry is enough for this pass
        # Restart from the newest entry so freshly-resolved pairs don't
        # leave stale indices behind; bail out only when nothing resolved.
        # (In dry-run mode nothing mutates, so a restart would loop forever.)
        if resolved_here and not dry_run:
            idx = len(entries) - 1
        else:
            idx -= 1
    return report


# ---------------------------------------------------------------------------
# Permissions, isolation & sharing
# ---------------------------------------------------------------------------

_PERMISSION_LEVELS = {"private": 0, "shared": 1, "public": 2, "agent": 3}


def permission_level(name: str) -> int:
    return _PERMISSION_LEVELS.get((name or "private").lower(), 0)


def entry_visible(
    entry: Any,
    *,
    owner: str = "",
    shared_with: Optional[Iterable[str]] = None,
) -> bool:
    """Whether ``entry`` is visible to the store/requester identified by ``owner``.

    Rules:
      * archived entries are hidden
      * legacy entries (no owner) are visible to everyone
      * an entry owned by ``owner`` is visible to it
      * an entry with ``permission`` in (``public``, ``shared``) whose
        ``shared_with`` list contains ``owner`` is visible
      * everything else (private to another owner, agent-only, not
        granted) is hidden
    """
    md = entry_metadata(entry)
    if md.get("archived"):
        return False
    entry_owner = md.get("owner", "")
    if not entry_owner:
        return True
    if owner and entry_owner == owner:
        return True
    perm = permission_level(str(md.get("permission", "private")))
    if perm >= 1 and owner:
        shared = md.get("shared_with")
        if isinstance(shared, (list, tuple, set)) and owner in shared:
            return True
        if perm >= 2:
            # "public" still requires the entry to be owned by *someone*,
            # so a public entry is only visible to explicit sharees and
            # the owner — never to anonymous readers.
            return False
    return False


def visible_entries(
    store: Any,
    target: str,
    *,
    scope: str = "default",
    owner: str = "",
    shared_with: Optional[Iterable[str]] = None,
) -> List[Any]:
    """The entries the current principal may actually read."""
    owner = owner or getattr(store, "owner", "") or ""
    shared = shared_with or getattr(store, "shared_with", None)
    return [
        e for e in store._entries_for(target, scope)
        if entry_visible(e, owner=owner, shared_with=shared)
    ]


def set_permission(
    store: Any,
    target: str,
    old_text: str,
    permission: str,
    *,
    scope: str = "default",
    with_owner: str = "",
) -> Dict[str, Any]:
    """Update the permission (and optional grant list) of an entry."""
    if permission not in _PERMISSION_LEVELS:
        return {"success": False, "error": f"Unknown permission '{permission}'."}
    entries = store._entries_for(target, scope)
    for idx, entry in enumerate(entries):
        if old_text in entry_text(entry):
            md = entry_metadata(entry)
            md["permission"] = permission
            md["updated_at"] = _now()
            if with_owner:
                md.setdefault("shared_with", [])
                if with_owner not in md["shared_with"]:
                    md["shared_with"].append(with_owner)
            entries[idx] = make_entry(entry_text(entry), md)
            store._set_entries(target, entries, scope)
            store.save_to_disk(target, scope)
            _invalidate_index(store)
            return {
                "success": True,
                "message": f"Permission set to '{permission}'.",
                "permission": permission,
                "shared_with": md.get("shared_with", []),
            }
    return {"success": False, "error": f"No entry matched '{old_text}'."}


def share_entry(
    store: Any,
    target: str,
    old_text: str,
    *,
    with_owner: str,
    permission: str = "shared",
    scope: str = "default",
) -> Dict[str, Any]:
    """Explicitly share an entry with another owner."""
    if not with_owner:
        return {"success": False, "error": "with_owner is required to share."}
    return set_permission(
        store, target, old_text, permission, scope=scope, with_owner=with_owner,
    )


def revoke_share(
    store: Any,
    target: str,
    old_text: str,
    *,
    owner: str = "",
    scope: str = "default",
) -> Dict[str, Any]:
    """Remove an owner from an entry's grant list (or drop sharing)."""
    entries = store._entries_for(target, scope)
    for idx, entry in enumerate(entries):
        if old_text in entry_text(entry):
            md = entry_metadata(entry)
            shared = md.get("shared_with", [])
            if owner:
                shared = [s for s in shared if s != owner]
                md["shared_with"] = shared
                msg = f"Revoked share for '{owner}'."
            else:
                md.pop("shared_with", None)
                md["permission"] = "private"
                msg = "Sharing removed; entry is private."
            md["updated_at"] = _now()
            entries[idx] = make_entry(entry_text(entry), md)
            store._set_entries(target, entries, scope)
            store.save_to_disk(target, scope)
            _invalidate_index(store)
            return {"success": True, "message": msg, "shared_with": md.get("shared_with", [])}
    return {"success": False, "error": f"No entry matched '{old_text}'."}


# ---------------------------------------------------------------------------
# Decay
# ---------------------------------------------------------------------------


def apply_decay(
    store: Any,
    *,
    target: Optional[str] = None,
    scope: str = "default",
    mode: str = "both",
    halflife_days: float = 90.0,
    ttl_default: float = 0.0,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Apply optional memory decay.

    ``mode``:
      * ``"ttl"`` — entries whose ``ttl`` (metadata seconds) has elapsed
        are archived (flagged, excluded from reads/snapshot).
      * ``"access"`` — confidence decays by
        ``0.5 ** (effective_age_days / halflife_days)`` where
        ``effective_age`` is time since the last access; accessed entries
        are refreshed.
      * ``"both"`` (default) — TTL expiry first, then access decay.

    Returns a report.  ``dry_run=True`` reports without mutating.
    """
    if mode not in ("ttl", "access", "both"):
        raise ValueError(f"apply_decay: unknown mode {mode!r}")
    now = _now()
    targets = ("memory", "user") if target is None else (target,)
    report: Dict[str, Any] = {
        "mode": mode, "archived": 0, "decayed": 0, "details": [],
    }

    for tgt in targets:
        entries = store._entries_for(tgt, scope)
        mutated = False
        for idx, entry in enumerate(entries):
            md = entry_metadata(entry)
            if md.get("archived") or md.get("pinned"):
                continue
            text = entry_text(entry)
            updated = float(md.get("updated_at", md.get("timestamp", now)))
            age_days = max(0.0, (now - updated) / 86400.0)
            ttl = float(md.get("ttl", 0.0) or ttl_default or 0.0)

            expiry = mode in ("ttl", "both") and ttl > 0 and age_days * 86400.0 > ttl
            if expiry:
                report["archived"] += 1
                if dry_run:
                    report["details"].append({"target": tgt, "index": idx, "action": "archive", "text": text[:80]})
                    continue
                md["archived"] = True
                md["archived_at"] = now
                md["updated_at"] = now
                entries[idx] = make_entry(text, md)
                mutated = True
                report["details"].append({"target": tgt, "index": idx, "action": "archive", "text": text[:80]})
                continue

            if mode in ("access", "both"):
                accessed = float(md.get("accessed_at", md.get("updated_at", updated)))
                eff_days = max(0.0, (now - accessed) / 86400.0)
                if halflife_days > 0 and eff_days > 0:
                    factor = 0.5 ** (eff_days / halflife_days)
                    new_conf = float(md.get("confidence", 0.5)) * factor
                    # A floor so decay never zeroes a real fact.
                    new_conf = max(new_conf, 0.05)
                    if abs(new_conf - float(md.get("confidence", 0.5))) > 1e-9:
                        report["decayed"] += 1
                        if dry_run:
                            report["details"].append({"target": tgt, "index": idx, "action": "decay", "old_confidence": md.get("confidence"), "new_confidence": round(new_conf, 4)})
                            continue
                        md["confidence"] = round(new_conf, 4)
                        entries[idx] = make_entry(text, md)
                        mutated = True
                        report["details"].append({"target": tgt, "index": idx, "action": "decay", "old_confidence": md.get("confidence"), "new_confidence": round(new_conf, 4)})

        if mutated and not dry_run:
            store._set_entries(tgt, entries, scope)
            store.save_to_disk(tgt, scope)
            _invalidate_index(store)
    return report


# ---------------------------------------------------------------------------
# Reconsolidation / deduplication
# ---------------------------------------------------------------------------


def reconsolidate(
    store: Any,
    *,
    target: Optional[str] = None,
    scope: str = "default",
    similarity: float = 0.8,
    policy: str = "keep_highest",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Merge near-duplicate entries and reclaim budget.

    Two entries are considered duplicates when token similarity exceeds
    ``similarity``.  ``policy`` selects which survives:
      * ``"keep_highest"`` — higher confidence wins (ties: longer text).
      * ``"keep_longest"`` — the more detailed entry wins.
      * ``"keep_newest"`` — the most recently updated wins.

    Also enforces the store's per-target char budget: when over budget,
    the lowest-priority (confidence × importance) entries are archived
    until the file fits.

    Returns a report of merged pairs + archived entries.
    """
    if policy not in ("keep_highest", "keep_longest", "keep_newest"):
        raise ValueError(f"reconsolidate: unknown policy {policy!r}")
    targets = ("memory", "user") if target is None else (target,)
    report: Dict[str, Any] = {"merged": 0, "archived": 0, "details": []}

    for tgt in targets:
        entries = store._entries_for(tgt, scope)
        changed = False
        idx = 0
        while idx < len(entries):
            entry = entries[idx]
            if _archive_flag(store, entry):
                idx += 1
                continue
            text = entry_text(entry)
            # Find a duplicate among the *remaining* siblings.  Skip pairs
            # that carry a real contradiction (attribute/polarity conflict) —
            # merging those would silently drop a valid fact.
            dup = -1
            for j in range(idx + 1, len(entries)):
                if _archive_flag(store, entries[j]):
                    continue
                other = entry_text(entries[j])
                if token_similarity(text, other) < similarity:
                    continue
                conflicted = any(
                    c["kind"] in ("attribute", "polarity")
                    for c in detect_conflicts(store, tgt, other, scope=scope)
                    if c["index"] == idx
                )
                if conflicted:
                    continue
                dup = j
                break
            if dup == -1:
                idx += 1
                continue

            a, b = entries[idx], entries[dup]
            a_md, b_md = entry_metadata(a), entry_metadata(b)
            if policy == "keep_highest":
                ca = float(a_md.get("confidence", 0.5))
                cb = float(b_md.get("confidence", 0.5))
                if cb > ca:
                    keeper, loser = b, a
                elif ca > cb:
                    keeper, loser = a, b
                else:
                    keeper = a if len(entry_text(a)) >= len(entry_text(b)) else b
                    loser = b if keeper is a else a
            elif policy == "keep_longest":
                keeper = a if len(entry_text(a)) >= len(entry_text(b)) else b
                loser = b if keeper is a else a
            else:  # keep_newest
                ta = float(a_md.get("updated_at", a_md.get("timestamp", 0)))
                tb = float(b_md.get("updated_at", b_md.get("timestamp", 0)))
                keeper = a if ta >= tb else b
                loser = b if keeper is a else a

            report["merged"] += 1
            report["details"].append({
                "target": tgt, "kept": entry_text(keeper)[:100],
                "dropped": entry_text(loser)[:100],
            })
            if dry_run:
                idx += 1
                continue
            # Replace the pair with the keeper (preserving its metadata).
            entries.remove(a)
            entries.remove(b)
            entries.insert(min(idx, dup), keeper)
            changed = True
            # Re-check the same slot for further duplicates.
            continue

        # Budget reclaim: archive lowest-priority entries over the limit.
        limit = store._char_limit(tgt, scope) if hasattr(store, "_char_limit") else 0
        if limit > 0:
            live = [e for e in entries if not _archive_flag(store, e)]
            live_text = [entry_text(e) for e in live]
            used = len(("\n§\n".join(live_text))) if live_text else 0
            if used > limit and not dry_run:
                ranked = sorted(
                    enumerate(live),
                    key=lambda ie: (
                        float(entry_metadata(ie[1]).get("confidence", 0.5)),
                        float(entry_metadata(ie[1]).get("importance", 0.0)),
                    ),
                )
                while used > limit and ranked:
                    _, worst = ranked.pop(0)
                    if entry_metadata(worst).get("pinned"):
                        continue
                    try:
                        wpos = entries.index(worst)
                    except ValueError:  # pragma: no cover - defensive
                        continue
                    md = entry_metadata(worst)
                    md["archived"] = True
                    md["archived_at"] = _now()
                    entries[wpos] = make_entry(entry_text(worst), md)
                    used -= len(entry_text(worst)) + 3
                    report["archived"] += 1
                    report["details"].append({"target": tgt, "action": "archive", "text": entry_text(worst)[:100]})
                    changed = True

        if changed and not dry_run:
            store._set_entries(tgt, entries, scope)
            store.save_to_disk(tgt, scope)
            _invalidate_index(store)
    return report


def deduplicate(
    store: Any,
    *,
    target: Optional[str] = None,
    scope: str = "default",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Convenience wrapper: exact + near-duplicate cleanup via reconsolidate."""
    return reconsolidate(
        store, target=target, scope=scope,
        similarity=0.8, policy="keep_highest", dry_run=dry_run,
    )


# ---------------------------------------------------------------------------
# Enhanced search ranking
# ---------------------------------------------------------------------------


def rank_search(
    store: Any,
    query: str,
    *,
    target: Optional[str] = None,
    scope: str = "default",
    limit: int = 10,
    owner: str = "",
    shared_with: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    """Rank entries against ``query``.

    Scoring:
      1. whole-query substring hit:  +6.0
      2. token overlap (fraction of query tokens present): +3.0 × ratio
      3. exact word-boundary token hit: +1.0 each (cap +3.0)
      4. tag/source metadata match: +1.0
      5. weighted by ``(0.5 + confidence)``
      6. recency: ``1 / (1 + age_days / 180)``
      7. access count: ``1 + 0.1 * log1p(access_count)``

    Returns a list of ``{"text", "score", "confidence", "created_at",
    "reason"}`` dicts sorted by descending score.  Respects visibility.
    """
    query = (query or "").strip()
    if not query:
        return []
    q = query.lower()
    q_tokens = _tokenize(query)
    now = _now()
    owner = owner or getattr(store, "owner", "") or ""
    shared = shared_with or getattr(store, "shared_with", None)

    targets = ("memory", "user") if target is None else (target,)
    results: List[Dict[str, Any]] = []

    for tgt in targets:
        for entry in visible_entries(store, tgt, scope=scope, owner=owner, shared_with=shared):
            text = entry_text(entry)
            tl = text.lower()
            md = entry_metadata(entry)
            score = 0.0
            reasons = []
            if q in tl:
                score += 6.0
                reasons.append("exact substring")
            entry_tokens = _tokenize(text)
            if q_tokens and entry_tokens:
                overlap = len(q_tokens & entry_tokens) / len(q_tokens)
                if overlap > 0:
                    score += 3.0 * overlap
                    reasons.append(f"token overlap {overlap:.0%}")
            word_hits = sum(
                1 for tok in q_tokens
                if re.search(rf"\b{re.escape(tok)}\b", tl)
            )
            score += min(3.0, word_hits)
            tags = md.get("tags") or []
            source = md.get("source", "")
            if any(q in str(t).lower() for t in tags) or q in str(source).lower():
                score += 1.0
                reasons.append("metadata match")
            if score <= 0:
                continue
            conf = float(md.get("confidence", 0.5))
            score *= (0.5 + conf)
            created = float(md.get("created_at", md.get("timestamp", now)))
            age_days = max(0.0, (now - created) / 86400.0)
            score *= (1.0 / (1.0 + age_days / 180.0))
            access_count = int(md.get("access_count", 0) or 0)
            score *= (1.0 + 0.1 * math.log1p(access_count))
            results.append({
                "target": tgt,
                "scope": scope,
                "text": text,
                "score": round(score, 4),
                "confidence": round(conf, 3),
                "created_at": created,
                "reason": ", ".join(reasons) or "keyword",
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


# ---------------------------------------------------------------------------
# Performance: cached inverted index
# ---------------------------------------------------------------------------


def build_index(store: Any, *, target: Optional[str] = None, scope: str = "default") -> Dict[str, Any]:
    """Build (and cache) a token → entry-position index for fast search.

    The cache lives on the store as ``_memory_index`` and is invalidated
    on every mutation (see ``_invalidate_index``).  Index entries are
    ``(target, scope, position)`` tuples; search uses them to short-list
    candidates instead of scanning every entry.
    """
    cached = getattr(store, "_memory_index", None)
    if cached is not None and not getattr(store, "_memory_index_dirty", True):
        return cached
    index: Dict[str, List[Tuple[str, str, int]]] = {}
    targets = ("memory", "user") if target is None else (target,)
    for tgt in targets:
        for scp in _store_scopes(store, tgt):
            for pos, entry in enumerate(store._entries_for(tgt, scp)):
                for tok in _tokenize(entry_text(entry)):
                    index.setdefault(tok, []).append((tgt, scp, pos))
    store._memory_index = index
    store._memory_index_dirty = False
    return index


def _invalidate_index(store: Any) -> None:
    if hasattr(store, "_memory_index_dirty"):
        store._memory_index_dirty = True


def _store_scopes(store: Any, target: str) -> List[str]:
    container = store.user_entries if target == "user" else store.memory_entries
    return list(container.keys()) if isinstance(container, dict) else ["default"]


# ---------------------------------------------------------------------------
# Failure recovery
# ---------------------------------------------------------------------------


def journal_path(store: Any, target: str, scope: str = "default") -> Path:
    path = store._path_for(target, scope)
    return Path(str(path) + ".journal")


def write_preimage(store: Any, target: str, scope: str = "default") -> Optional[Path]:
    """Snapshot the target file to ``<file>.journal`` before a mutation.

    Returns the journal path (or None when there is no file yet).  The
    caller MUST call ``clear_journal`` after the write commits.
    """
    path = store._path_for(target, scope)
    if not Path(path).exists():
        return None
    jp = journal_path(store, target, scope)
    try:
        Path(path).copy(jp) if hasattr(Path, "copy") else _copy_file(path, jp)
        return jp
    except (OSError, IOError) as exc:
        logger.warning("Memory journal write failed for %s: %s", path, exc)
        return None


def _copy_file(src, dst) -> None:
    with open(str(src), "rb") as fsrc, open(str(dst), "wb") as fdst:
        fdst.write(fsrc.read())


def clear_journal(store: Any, target: str, scope: str = "default") -> None:
    jp = journal_path(store, target, scope)
    try:
        if Path(jp).exists():
            Path(jp).unlink()
    except (OSError, IOError):
        pass


def recover_store(store: Any, *, dry_run: bool = False) -> Dict[str, Any]:
    """Recover from crashes using the pre-image journal.

    Invoked at load time.  For each target/scope file:

      * if the main file is missing, empty, or unreadable AND a journal
        exists with content → restore the journal over the main file.
      * if both exist and the journal differs → the journal is a stale
        pre-mutation snapshot; delete it (the main file is authoritative).
      * if only a journal exists and the main file is healthy → delete it.
    """
    report: Dict[str, Any] = {"restored": 0, "cleaned": 0, "details": []}
    for target in ("memory", "user"):
        for scope in _store_scopes(store, target):
            path = store._path_for(target, scope)
            jp = journal_path(store, target, scope)
            main_ok = Path(path).exists() and Path(path).stat().st_size > 0
            journal_ok = Path(jp).exists() and Path(jp).stat().st_size > 0
            if not journal_ok:
                continue
            if not main_ok:
                report["restored"] += 1
                if not dry_run:
                    _copy_file(jp, path)
                report["details"].append({"target": target, "scope": scope, "action": "restore"})
            else:
                report["cleaned"] += 1
                if not dry_run:
                    Path(jp).unlink()
                report["details"].append({"target": target, "scope": scope, "action": "clean"})
    return report


def repair_store(store: Any, *, dry_run: bool = False) -> Dict[str, Any]:
    """Repair corrupt/drifted memory files.

      * backs up any file that fails the round-trip parse,
      * rewrites it as a clean §-delimited entry list,
      * rebuilds the search index,
      * re-captures the frozen system-prompt snapshot.
    """
    from tools.memory_tool import ENTRY_DELIMITER  # local import to break cycle

    report: Dict[str, Any] = {"backed_up": 0, "rewritten": 0, "details": []}
    for target in ("memory", "user"):
        for scope in _store_scopes(store, target):
            path = store._path_for(target, scope)
            if not Path(path).exists():
                continue
            try:
                raw = Path(path).read_text(encoding="utf-8")
            except (OSError, IOError) as exc:
                report["details"].append({"target": target, "scope": scope, "action": "skip", "error": str(exc)})
                continue
            if not raw.strip():
                continue
            parsed = [e.strip() for e in raw.split(ENTRY_DELIMITER) if e.strip()]
            roundtrip = ENTRY_DELIMITER.join(parsed)
            if raw.strip() == roundtrip:
                continue  # tool-shaped, healthy
            if dry_run:
                report["backed_up"] += 1
                report["details"].append({"target": target, "scope": scope, "action": "would_backup"})
                continue
            ts = int(_now())
            bak = Path(str(path) + f".bak.{ts}")
            try:
                Path(path).copy(bak) if hasattr(Path, "copy") else _copy_file(path, bak)
            except (OSError, IOError) as exc:
                report["details"].append({"target": target, "scope": scope, "action": "backup_failed", "error": str(exc)})
                continue
            try:
                Path(path).write_text(roundtrip + "\n", encoding="utf-8")
            except (OSError, IOError) as exc:
                report["details"].append({"target": target, "scope": scope, "action": "rewrite_failed", "error": str(exc)})
                continue
            report["backed_up"] += 1
            report["rewritten"] += 1
            report["details"].append({"target": target, "scope": scope, "action": "rewritten", "backup": str(bak)})
    if not dry_run:
        _invalidate_index(store)
        if hasattr(store, "load_from_disk"):
            try:
                store.load_from_disk()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("repair_store: reload after rewrite failed: %s", exc)
    return report


# ---------------------------------------------------------------------------
# Aggregate maintenance
# ---------------------------------------------------------------------------


def maintain(
    store: Any,
    *,
    decay: bool = True,
    reconsolidate_mem: bool = True,
    purge: bool = True,
    repair: bool = True,
    decay_mode: str = "both",
    halflife_days: float = 90.0,
    ttl_default: float = 0.0,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Run a full lifecycle maintenance pass (CLI / scheduled / acceptance)."""
    report: Dict[str, Any] = {"dry_run": dry_run, "started": _now()}
    if repair:
        report["repair"] = repair_store(store, dry_run=dry_run)
    if purge:
        report["secrets"] = purge_secrets(store, mode="redact", dry_run=dry_run)
    # Resolve contradictions first so the merge pass can't swallow a fact.
    report["conflicts"] = {
        "resolved": 0, "removed": [], "details": [],
    }
    for tgt in ("memory", "user"):
        for scope in _store_scopes(store, tgt):
            partial = resolve_conflicts(
                store, tgt, scope=scope, policy="keep_best", dry_run=dry_run,
            )
            report["conflicts"]["resolved"] += partial["resolved"]
            report["conflicts"]["removed"].extend(partial["removed"])
            report["conflicts"]["details"].extend(partial["details"])
    if reconsolidate_mem:
        report["reconsolidate"] = reconsolidate(
            store, similarity=0.8, policy="keep_highest", dry_run=dry_run,
        )
    if decay:
        report["decay"] = apply_decay(
            store, mode=decay_mode, halflife_days=halflife_days,
            ttl_default=ttl_default, dry_run=dry_run,
        )
    report["finished"] = _now()
    return report


# ---------------------------------------------------------------------------
# Aggregate stats for the acceptance test / CLI status
# ---------------------------------------------------------------------------


def lifecycle_stats(store: Any) -> Dict[str, Any]:
    """Summarize the lifecycle-relevant state of the store."""
    stats: Dict[str, Any] = {"total": 0, "by_target": {}, "archived": 0, "pinned": 0}
    perms: Dict[str, int] = {}
    confs: List[float] = []
    secrets_found = 0
    for target in ("memory", "user"):
        count = 0
        for scope in _store_scopes(store, target):
            for entry in store._entries_for(target, scope):
                md = entry_metadata(entry)
                count += 1
                if md.get("archived"):
                    stats["archived"] += 1
                if md.get("pinned"):
                    stats["pinned"] += 1
                perm = str(md.get("permission", "private"))
                perms[perm] = perms.get(perm, 0) + 1
                confs.append(float(md.get("confidence", 0.5)))
                if scan_secrets(entry_text(entry)):
                    secrets_found += 1
        stats["by_target"][target] = count
        stats["total"] += count
    stats["by_permission"] = perms
    stats["avg_confidence"] = round(sum(confs) / len(confs), 3) if confs else 0.0
    stats["secrets_found"] = secrets_found
    return stats


__all__ = [
    "entry_text", "entry_metadata", "make_entry",
    "score_confidence", "confidence_label", "ensure_confidence", "default_metadata",
    "scan_secrets", "redact_secrets", "secret_check_message", "secrets_report", "purge_secrets",
    "token_similarity", "extract_attributes", "detect_conflicts", "list_conflicts",
    "resolve_conflicts",
    "permission_level", "entry_visible", "visible_entries", "set_permission",
    "share_entry", "revoke_share",
    "apply_decay",
    "reconsolidate", "deduplicate",
    "rank_search", "build_index",
    "journal_path", "write_preimage", "clear_journal", "recover_store", "repair_store",
    "maintain", "lifecycle_stats",
]
