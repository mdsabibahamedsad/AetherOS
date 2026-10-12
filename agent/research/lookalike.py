"""Lookalike-domain intelligence: homoglyph and typosquat detection.

(P17/P19/P97) A trusted-looking initial URL says nothing about the final
destination, and a plausible domain NAME says nothing about the publisher.
This module flags domains that are visually confusable with well-known
registrable domains (or with other domains already admitted to the task):

- HOMOGLYPH: same skeleton after unicode-confusable folding but different
  raw host -> treated as near-certain spoofing.
- TYPOSQUAT: small edit distance / classic typo patterns -> flagged as
  elevated risk, not blocked (could be legitimate).

Pure functions; no network. The confusable table covers common Latin/
Cyrillic/Greek collisions plus fullwidth forms via NFKC.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

# Common cross-script homoglyphs folded to their Latin lookalikes.
_CONFUSABLE_MAP: Dict[str, str] = {
    # Cyrillic
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y",
    "х": "x", "і": "i", "ѕ": "s", "ј": "j", "һ": "h", "ԁ": "d", "ɡ": "g",
    # Greek
    "ο": "o", "α": "a", "ε": "e", "ι": "i", "κ": "k", "ρ": "p",
    "τ": "t", "υ": "u", "ν": "v", "χ": "x",
    # Latin fullwidth / mathematical forms handled by NFKC above.
    # Digits are deliberately NOT folded: real domains legitimately use them.
}

# Classic ASCII confusion pairs used in typosquats (checked positionally).
_ASCII_PAIRS = (("rn", "m"), ("vv", "w"), ("cl", "d"), ("ii", "n"), ("nn", "u"))

_POPULAR_DOMAINS = (
    "google.com", "youtube.com", "facebook.com", "instagram.com",
    "twitter.com", "x.com", "github.com", "gitlab.com", "apple.com",
    "microsoft.com", "amazon.com", "paypal.com", "netflix.com",
    "linkedin.com", "openai.com", "anthropic.com", "binance.com",
    "coinbase.com", "whatsapp.com", "wikipedia.org", "reddit.com",
    "arxiv.org", "python.org", "npmjs.com", "docker.com", "kubernetes.io",
)


def _fold(text: str) -> str:
    import unicodedata

    lowered = text.lower()
    normalized = unicodedata.normalize("NFKC", lowered)
    out = []
    for ch in normalized:
        if ch in _CONFUSABLE_MAP and ch != _CONFUSABLE_MAP[ch]:
            out.append(_CONFUSABLE_MAP[ch])
        else:
            out.append(ch)
    return unicodedata.normalize("NFKC", "".join(out))


def skeleton(host_or_url: str) -> str:
    """Registration-independent visual skeleton of a hostname."""
    from agent.research.urlnorm import registrable_domain

    host = registrable_domain(host_or_url)
    folded = _fold(host)
    return re.sub(r"[^a-z0-9.]", "", folded)


def _ascii_variants(label: str) -> str:
    """Collapse classic ASCII confusion pairs for comparison."""
    out = label
    for pair, single in _ASCII_PAIRS:
        out = out.replace(pair, single)
    return out


def _levenshtein(a: str, b: str, cap: int = 3) -> int:
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
        if min(prev) > cap:
            return cap + 1
    return prev[-1]


@dataclass(frozen=True)
class LookalikeVerdict:
    kind: str  # none | homoglyph | typosquat | skeleton_match
    lookalike_of: str = ""
    similarity: float = 0.0


def assess_domain(candidate_host_or_url: str,
                  extra_references: Iterable[str] = ()) -> LookalikeVerdict:
    """Compare a candidate against popular domains + caller references."""
    from agent.research.urlnorm import registrable_domain

    candidate = registrable_domain(candidate_host_or_url)
    cand_skeleton = skeleton(candidate)
    cand_label = cand_skeleton.split(".")[0]
    cand_folded_raw = _fold(candidate)

    references = list(_POPULAR_DOMAINS) + [
        registrable_domain(r) for r in extra_references or []
    ]

    best: Optional[Tuple[str, str]] = None  # (kind, reference)

    for reference in references:
        ref_skeleton = skeleton(reference)
        ref_label = ref_skeleton.split(".")[0]
        if not cand_label or cand_skeleton == ref_skeleton:
            if candidate == reference:
                continue
            if cand_skeleton == ref_skeleton:
                # Same visual skeleton, different raw registration.
                return LookalikeVerdict("homoglyph", reference, 1.0)
            continue
        cand_tld = "." + ".".join(cand_skeleton.split(".")[1:])
        ref_tld = "." + ".".join(ref_skeleton.split(".")[1:])
        # Fuzzy rules below need a meaningful brand label; short labels
        # ('x', 'go') would false-positive on any containing word.
        if len(ref_label) < 5:
            continue
        # Brand embedding: popular label embedded into a longer one
        # (mybank-secure vs mybank). Length-delta guard keeps legitimate
        # long labels like githubusercontent out of scope.
        if ref_label in cand_label and cand_label != ref_label:
            delta = len(cand_label) - len(ref_label)
            hyphenated = "-" in candidate
            if 1 <= delta <= 7 and (hyphenated or cand_tld != ref_tld or delta >= 4):
                return LookalikeVerdict("typosquat", reference, 0.9)
        # Classic ASCII confusion collapse on whole label.
        if _ascii_variants(cand_label) == _ascii_variants(ref_label):
            if cand_tld != ref_tld:
                return LookalikeVerdict("typosquat", reference, 0.95)
            if cand_folded_raw != _fold(reference):
                return LookalikeVerdict("skeleton_match", reference, 0.99)
        distance = _levenshtein(cand_label, ref_label, cap=2)
        if distance in (1, 2) and len(ref_label) >= 6:
            similarity = 1.0 - distance / max(len(cand_label), len(ref_label))
            if similarity >= 0.8 and best is None:
                best = ("typosquat", reference)

    if best is not None:
        return LookalikeVerdict(best[0], best[1], 0.85)
    return LookalikeVerdict("none")


def risk_bump(verdict: LookalikeVerdict) -> float:
    """Risk delta applied by the engine at source admission."""
    return {"none": 0.0, "typosquat": 0.25, "skeleton_match": 0.4}.get(
        verdict.kind, 0.6
    )
