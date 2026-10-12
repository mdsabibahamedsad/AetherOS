"""Automatic Summarization module.

Summarizes long conversations into compressed memories while preserving
decisions, code, action items, questions, and key information.
"""

from __future__ import annotations

import json
import logging
import math
import re
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_memory.automatic_summarization")

try:
    from aetheros_memory.memory_manager import MemoryManager, MemoryCategory
except ImportError:
    MemoryManager = None
    MemoryCategory = None


class CompressionLevel(str, Enum):
    NONE = "none"
    LIGHT = "light"
    MEDIUM = "medium"
    AGGRESSIVE = "aggressive"
    EXTREME = "extreme"


_RATIO_MAP = {
    CompressionLevel.NONE: 1.0,
    CompressionLevel.LIGHT: 0.75,
    CompressionLevel.MEDIUM: 0.5,
    CompressionLevel.AGGRESSIVE: 0.3,
    CompressionLevel.EXTREME: 0.15,
}


@dataclass
class SummarizationConfig:
    default_level: CompressionLevel = CompressionLevel.MEDIUM
    min_length: int = 100
    max_summary_length: int = 2000
    enable_progressive: bool = True
    preserve_decisions: bool = True
    preserve_code: bool = True
    preserve_questions: bool = True
    preserve_action_items: bool = True
    enable_keyword_extraction: bool = True
    enable_sentiment: bool = True


@dataclass
class SummaryResult:
    original_length: int = 0
    summary: str = ""
    compression_ratio: float = 1.0
    key_points: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    code_snippets: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    entities: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_length": self.original_length,
            "summary": self.summary,
            "compression_ratio": self.compression_ratio,
            "key_points": self.key_points,
            "decisions": self.decisions,
            "action_items": self.action_items,
            "questions": self.questions,
            "code_snippets": self.code_snippets,
            "keywords": self.keywords,
            "sentiment": self.sentiment,
            "entities": self.entities,
            "created_at": self.created_at,
        }


_DECISION_PATTERNS = re.compile(
    r"(?i)(we\s+)?(decided|chose|selected|opted|elected|resolved|concluded|"
    r"determined|agreed|settled|voted|ruled|committed|picked)\s+(?:to|on|for|that)",
)

_ACTION_PATTERNS = re.compile(
    r"(?i)(need\s+to|must|should|will|have\s+to|gotta|next\s+step|"
    r"action\s+item|todo|to-do|follow.up|action\s+required|"
    r"assignee|owner:|responsible:)"
)

_QUESTION_PATTERNS = re.compile(r"\?$", re.MULTILINE)

_QUESTION_WORD_PATTERNS = re.compile(
    r"(?i)^\s*(what|who|where|when|why|how|which|whom|whose|"
    r"does|do|did|is|are|was|were|can|could|will|would|shall|should|"
    r"has|have|had|if)\b"
)

_CODE_BLOCK_PATTERN = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
_INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")

_ENTITY_PATTERN = re.compile(
    r"(?<![A-Za-z])[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?![a-z])"
)

_NEGATIVE_WORDS: Set[str] = {
    "bad", "terrible", "awful", "horrible", "worst", "hate", "hated",
    "dislike", "disliked", "ugly", "broken", "failure", "failed",
    "error", "wrong", "incorrect", "problem", "issue", "bug",
    "crash", "critical", "slow", "painful", "frustrating", "annoying",
    "disappointing", "poor", "mediocre", "inferior", "damaged",
    "failed", "losing", "lost", "negative", "unfortunately",
    "cannot", "can't", "won't", "wouldn't", "shouldn't",
}

_POSITIVE_WORDS: Set[str] = {
    "good", "great", "excellent", "amazing", "awesome", "wonderful",
    "fantastic", "brilliant", "perfect", "beautiful", "love", "loved",
    "happy", "pleased", "satisfied", "impressive", "outstanding",
    "superb", "remarkable", "exceptional", "delightful", "pleasant",
    "success", "successful", "succeeded", "win", "won", "winning",
    "positive", "fortunate", "beneficial", "helpful", "useful",
    "efficient", "fast", "reliable", "robust", "elegant", "clean",
    "solved", "fixed", "resolved", "improved", "optimized",
}

_STOP_WORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "as", "is", "was", "are",
    "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "can", "could", "shall", "should", "may",
    "might", "must", "it", "its", "this", "that", "these", "those",
    "i", "you", "he", "she", "we", "they", "me", "him", "her", "us",
    "them", "my", "your", "his", "its", "our", "their", "not", "no",
    "nor", "so", "if", "then", "else", "when", "where", "why", "how",
    "which", "who", "whom", "what", "about", "into", "through", "during",
    "before", "after", "above", "below", "up", "down", "out", "off",
    "over", "under", "again", "further", "once", "here", "there",
}


def _split_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", text.strip())
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(])", text)
    return [s.strip() for s in sentences if s.strip()]


class AutomaticSummarization:
    """Compresses text into summaries while preserving key information."""

    def __init__(self, config: Optional[SummarizationConfig] = None,
                 memory_manager: Optional[Any] = None):
        self._lock = threading.RLock()
        self.config = config or SummarizationConfig()
        self._memory_manager = memory_manager

    def summarize(self, text: str,
                  level: Optional[CompressionLevel] = None,
                  max_length: Optional[int] = None) -> SummaryResult:
        level = level or self.config.default_level
        max_length = max_length or self.config.max_summary_length
        original_length = len(text)

        ratio = _RATIO_MAP.get(level, 0.5)
        compressed = self.compress(text, ratio)

        if len(compressed) > max_length:
            compressed = compressed[:max_length]
            last_period = compressed.rfind(".")
            if last_period > max_length * 0.8:
                compressed = compressed[:last_period + 1]

        summary = compressed
        compression_ratio = len(summary) / max(original_length, 1)

        key_points = self.extract_key_points(text, 5)
        decisions = self.extract_decisions(text) if self.config.preserve_decisions else []
        action_items = self.extract_action_items(text) if self.config.preserve_action_items else []
        questions = self.extract_questions(text) if self.config.preserve_questions else []
        code_snippets = self.extract_code_snippets(text) if self.config.preserve_code else []
        keywords = self.extract_keywords(text, 10) if self.config.enable_keyword_extraction else []
        sentiment = self.detect_sentiment(text) if self.config.enable_sentiment else "neutral"
        entities = self.extract_entities(text)

        result = SummaryResult(
            original_length=original_length,
            summary=summary,
            compression_ratio=compression_ratio,
            key_points=key_points,
            decisions=decisions,
            action_items=action_items,
            questions=questions,
            code_snippets=code_snippets,
            keywords=keywords,
            sentiment=sentiment,
            entities=entities,
        )

        if self._memory_manager is not None:
            try:
                self._memory_manager.remember(
                    f"summary:{hash(text) % 2**32:08x}",
                    result.to_dict(),
                    memory_type="workspace",
                )
            except Exception:
                pass

        return result

    def extract_key_points(self, text: str, count: int = 5) -> List[str]:
        sentences = _split_sentences(text)
        scored: List[tuple[float, str]] = []
        for sentence in sentences:
            score = 0.0
            if any(c.isdigit() for c in sentence):
                score += 2.0
            if re.search(r"[A-Z]\w+(?:\s+[A-Z]\w+)+", sentence):
                score += 2.0
            if re.search(r"(?i)(important|critical|key|significant|essential|crucial|major|primary)", sentence):
                score += 3.0
            if re.search(r"(?i)(because|therefore|thus|hence|consequently|as a result)", sentence):
                score += 1.5
            if re.search(r"(?i)(result|conclusion|finding|outcome|summary)", sentence):
                score += 2.0
            if re.search(r"[,;:]", sentence):
                score += 1.0
            unique_words = len(set(w.lower() for w in sentence.split() if w.lower() not in _STOP_WORDS))
            score += unique_words * 0.1
            scored.append((score, sentence))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:count]]

    def extract_decisions(self, text: str) -> List[str]:
        results: List[str] = []
        sentences = _split_sentences(text)
        for sentence in sentences:
            if _DECISION_PATTERNS.search(sentence):
                cleaned = sentence.strip()
                if cleaned and cleaned not in results:
                    results.append(cleaned)
        return results

    def extract_action_items(self, text: str) -> List[str]:
        results: List[str] = []
        sentences = _split_sentences(text)
        for sentence in sentences:
            if _ACTION_PATTERNS.search(sentence):
                cleaned = sentence.strip()
                if cleaned and cleaned not in results:
                    results.append(cleaned)
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("- [ ]") or stripped.startswith("* [ ]"):
                item = re.sub(r"^[-*]\s*\[ \]\s*", "", stripped)
                if item and item not in results:
                    results.append(item)
            elif stripped.startswith("TODO") or stripped.startswith("FIXME"):
                item = re.sub(r"^(TODO|FIXME)[:\s]*", "", stripped)
                if item and item not in results:
                    results.append(item)
        return results

    def extract_questions(self, text: str) -> List[str]:
        results: List[str] = []
        sentences = _split_sentences(text)
        for sentence in sentences:
            if _QUESTION_PATTERNS.search(sentence) or _QUESTION_WORD_PATTERNS.search(sentence):
                cleaned = sentence.strip()
                if cleaned and cleaned not in results:
                    results.append(cleaned)
        return results

    def extract_code_snippets(self, text: str) -> List[str]:
        results: List[str] = []
        for match in _CODE_BLOCK_PATTERN.finditer(text):
            code = match.group(2).strip()
            if code and code not in results:
                results.append(code)
        for match in _INLINE_CODE_PATTERN.finditer(text):
            code = match.group(1).strip()
            if code and len(code) > 10 and code not in results:
                results.append(code)
        return results

    def extract_keywords(self, text: str, count: int = 10) -> List[str]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", text)
        filtered = [w.lower() for w in words if w.lower() not in _STOP_WORDS and len(w) > 2]
        freq = Counter(filtered)
        capitalized = [w for w in words if w[0].isupper() and w.lower() not in _STOP_WORDS]
        for w in capitalized:
            freq[w.lower()] += 1
        most_common = freq.most_common(count)
        return [w for w, _ in most_common]

    def detect_sentiment(self, text: str) -> str:
        words = re.findall(r"[A-Za-z']+", text.lower())
        pos_count = sum(1 for w in words if w in _POSITIVE_WORDS)
        neg_count = sum(1 for w in words if w in _NEGATIVE_WORDS)
        total = pos_count + neg_count
        if total == 0:
            return "neutral"
        if pos_count > neg_count * 2:
            return "positive"
        if neg_count > pos_count * 2:
            return "negative"
        if pos_count > 0 and neg_count > 0:
            return "mixed"
        if pos_count > neg_count:
            return "positive"
        if neg_count > pos_count:
            return "negative"
        return "neutral"

    def extract_entities(self, text: str) -> List[str]:
        entities: List[str] = []
        seen: Set[str] = set()
        for match in _ENTITY_PATTERN.finditer(text):
            entity = match.group(0).strip()
            if entity and len(entity) > 2 and entity not in seen:
                stop_check = entity.split()[0].lower()
                if stop_check not in _STOP_WORDS or len(entity.split()) > 1:
                    entities.append(entity)
                    seen.add(entity)
        return entities

    def compress(self, text: str, ratio: float) -> str:
        if ratio >= 1.0:
            return text

        sentences = _split_sentences(text)
        if not sentences:
            return ""

        if ratio <= 0.0:
            return sentences[0] if sentences else ""

        target_len = max(int(len(text) * ratio), 1)
        scored: List[tuple[float, str, int]] = []
        for sentence in sentences:
            score = 0.0
            info_density = 0
            if re.search(r"\d", sentence):
                info_density += 2
                score += 2.0
            if re.search(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", sentence):
                info_density += 2
                score += 2.0
            if any(kw in sentence.lower() for kw in
                   ["result", "conclusion", "summary", "important", "key",
                    "critical", "decision", "fix", "solution", "change"]):
                info_density += 3
                score += 3.0
            if len(sentence) > 50:
                info_density += 1
                score += 1.0
            contains_code = bool(_INLINE_CODE_PATTERN.search(sentence))
            if contains_code:
                score += 4.0
            unique_words = len(set(w.lower() for w in sentence.split()))
            score += unique_words * 0.05
            is_first = sentence == sentences[0]
            is_last = sentence == sentences[-1]
            if is_first:
                score += 2.0
            if is_last:
                score += 1.5
            scored.append((score, sentence, len(sentence)))

        scored.sort(key=lambda x: x[0], reverse=True)

        result_parts: List[str] = []
        accumulated = 0
        for score, sentence, slen in scored:
            if accumulated + slen <= target_len or not result_parts:
                result_parts.append(sentence)
                accumulated += slen
            if accumulated >= target_len:
                break

        if not result_parts and sentences:
            result_parts.append(sentences[0])

        result_parts.sort(key=lambda s: sentences.index(s) if s in sentences else 0)

        return " ".join(result_parts)

    def progressive_summarize(self, texts: List[str]) -> SummaryResult:
        combined = " ".join(texts)
        return self.summarize(combined, CompressionLevel.AGGRESSIVE)

    def merge_summaries(self, summaries: List[SummaryResult]) -> SummaryResult:
        combined_text = " ".join(s.summary for s in summaries)
        merged = self.summarize(combined_text, CompressionLevel.MEDIUM)
        merged.key_points = []
        seen_points: Set[str] = set()
        for s in summaries:
            for point in s.key_points:
                if point not in seen_points:
                    merged.key_points.append(point)
                    seen_points.add(point)
        merged.decisions = list(dict.fromkeys(d for s in summaries for d in s.decisions))
        merged.action_items = list(dict.fromkeys(a for s in summaries for a in s.action_items))
        merged.questions = list(dict.fromkeys(q for s in summaries for q in s.questions))
        merged.code_snippets = list(dict.fromkeys(c for s in summaries for c in s.code_snippets))
        all_keywords: List[str] = []
        for s in summaries:
            all_keywords.extend(s.keywords)
        merged.keywords = list(dict.fromkeys(all_keywords))[:20]
        merged.entities = list(dict.fromkeys(e for s in summaries for e in s.entities))
        sentiments = [s.sentiment for s in summaries]
        if "positive" in sentiments and "negative" in sentiments:
            merged.sentiment = "mixed"
        elif "positive" in sentiments:
            merged.sentiment = "positive"
        elif "negative" in sentiments:
            merged.sentiment = "negative"
        else:
            merged.sentiment = "neutral"
        return merged

    def export_json(self, filepath: Optional[str] = None) -> str:
        data = {"config": {
            "default_level": self.config.default_level.value,
            "min_length": self.config.min_length,
            "max_summary_length": self.config.max_summary_length,
            "enable_progressive": self.config.enable_progressive,
            "preserve_decisions": self.config.preserve_decisions,
            "preserve_code": self.config.preserve_code,
            "preserve_questions": self.config.preserve_questions,
            "preserve_action_items": self.config.preserve_action_items,
            "enable_keyword_extraction": self.config.enable_keyword_extraction,
            "enable_sentiment": self.config.enable_sentiment,
        }}
        json_str = json.dumps(data, indent=2, default=str)
        if filepath:
            Path(filepath).write_text(json_str, encoding="utf-8")
        return json_str