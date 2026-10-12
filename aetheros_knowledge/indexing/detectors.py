"""Language and duplicate detection."""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

LANG_PATTERNS = {
    "python": [r'\bdef \w+\(', r'\bimport \w+', r'\bclass \w+:', r'\bprint\(', r'if __name__'],
    "javascript": [r'\bfunction\b', r'\bconst \w+ =', r'\blet \w+ =', r'\bvar \w+ =', r'=>'],
    "typescript": [r': string', r': number', r': boolean', r'\binterface\b', r'\btype\b'],
    "rust": [r'\bfn \w+\(', r'\blet mut\b', r'\bimpl\b', r'\bpub \b', r'->'],
    "go": [r'\bfunc \w+\(', r'\bpackage\b', r'\bimport \(', r'\bdefer\b', r'\bgoroutine\b'],
    "java": [r'\bpublic class\b', r'\bprivate\b', r'\bvoid \w+\(', r'\bimport java\.'],
    "cpp": [r'#include', r'\bint main\(', r'\bstd::', r'\bclass \w+[\s\n]*{', r'\bcout'],
    "ruby": [r'\bdef \w+', r'\bend\b', r'\brequire\b', r'\battr_\w+', r'\bdo\b'],
    "php": [r'<\?php', r'\bfunction \w+\(', r'\$\w+', r'\becho\b', r'\bnamespace\b'],
    "swift": [r'\bfunc \w+\(', r'\bvar \w+:', r'\blet \w+ =', r'\bstruct \w+', r'\bclass \w+'],
}


def detect_language(text: str) -> str:
    for lang, patterns in LANG_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, text, re.MULTILINE))
        if score >= 3:
            return lang
    words = set(re.findall(r'\b[a-zA-Z]\w+\b', text[:2000].lower()))
    english_stopwords = {
        "the", "be", "to", "of", "and", "a", "in", "that", "have",
        "i", "it", "for", "not", "on", "with", "he", "as", "you",
        "do", "at", "this", "but", "his", "by", "from", "they",
        "we", "say", "her", "she", "or", "an", "will", "my", "one",
        "all", "would", "there", "their", "what", "so", "up", "out",
    }
    match = words & english_stopwords
    if len(match) >= 3:
        return "en"
    if any(ord(c) > 0x4E00 for c in text[:500]):
        return "zh"
    if any(ord(c) > 0x3040 and ord(c) < 0x30FF for c in text[:500]):
        return "ja"
    return "en"


def detect_duplicates(texts: list[str],
                       threshold: float = 0.95) -> list[tuple[int, int]]:
    hashes = []
    for t in texts:
        normalized = re.sub(r'\s+', ' ', t.strip().lower())
        h = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        hashes.append(h)
    duplicates = []
    seen: dict[str, int] = {}
    for i, h in enumerate(hashes):
        if h in seen:
            duplicates.append((seen[h], i))
        else:
            seen[h] = i
    return duplicates


def detect_near_duplicates(texts: list[str],
                            threshold: float = 0.8) -> list[tuple[int, int, float]]:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        if len(texts) < 2:
            return []
        vec = TfidfVectorizer(max_features=1000).fit_transform(texts)
        sim = cosine_similarity(vec)
        pairs = []
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                if sim[i][j] >= threshold:
                    pairs.append((i, j, float(sim[i][j])))
        return pairs
    except ImportError:
        return []
