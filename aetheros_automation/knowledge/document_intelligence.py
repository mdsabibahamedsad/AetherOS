from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ExtractedEntity:
    name: str
    type: str
    mentions: list[str] = field(default_factory=list)
    confidence: float = 1.0
    context: str = ""


@dataclass
class DocumentTopic:
    name: str
    score: float = 0.0
    keywords: list[str] = field(default_factory=list)


@dataclass
class DocumentReference:
    url: str = ""
    title: str = ""
    document_id: str = ""
    relationship: str = "referenced_by"


class DocumentIntelligence:
    def extract_entities(self, text: str) -> list[ExtractedEntity]:
        import re
        entities = []
        seen = set()
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        for email in re.findall(email_pattern, text):
            if email.lower() not in seen:
                seen.add(email.lower())
                entities.append(ExtractedEntity(name=email, type="email", mentions=[email]))
        url_pattern = r"https?://[^\s<>\"']+|www\.[^\s<>\"']+"
        for url in re.findall(url_pattern, text):
            trimmed = url.rstrip(".,;:!?)")
            if trimmed.lower() not in seen:
                seen.add(trimmed.lower())
                entities.append(ExtractedEntity(name=trimmed, type="url", mentions=[trimmed], confidence=0.9))
        person_pattern = r"(?:Mr\.|Ms\.|Mrs\.|Dr\.|Prof\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*"
        for person in re.findall(person_pattern, text):
            if person not in seen:
                seen.add(person)
                entities.append(ExtractedEntity(name=person, type="person", mentions=[person], confidence=0.7))
        date_pattern = r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},?\s*\d{4}\b"
        for date in re.findall(date_pattern, text):
            if date not in seen:
                seen.add(date)
                entities.append(ExtractedEntity(name=date, type="date", mentions=[date], confidence=1.0))
        return entities

    def extract_topics(self, text: str, max_topics: int = 5) -> list[DocumentTopic]:
        import re
        from collections import Counter
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "has", "have", "had", "do", "does", "did", "will", "would",
                     "could", "should", "may", "might", "shall", "can", "need",
                     "i", "you", "he", "she", "it", "we", "they", "this", "that",
                     "these", "those", "am", "to", "of", "in", "for", "on", "with",
                     "at", "by", "from", "as", "into", "through", "during", "before",
                     "after", "above", "below", "between", "out", "off", "over", "under",
                     "again", "then", "once", "here", "there", "and", "but", "or",
                     "nor", "not", "so", "about", "up", "down", "some", "any", "each",
                     "every", "all", "both", "few", "more", "most", "other", "no",
                     "only", "own", "same", "very", "just", "also", "now", "how",
                     "what", "which", "who", "whom"}
        words = re.findall(r"[a-zA-Z]{4,}", text.lower())
        words = [w for w in words if w not in stopwords]
        bigrams = [" ".join(words[i:i+2]) for i in range(len(words)-1)]
        word_freq = Counter(words)
        bigram_freq = Counter(bigrams)
        combined = {}
        for word, count in word_freq.most_common(20):
            combined[word] = count / max(word_freq.values(), 1)
        for bigram, count in bigram_freq.most_common(10):
            combined[bigram] = count / max(bigram_freq.values(), 1) * 1.2
        sorted_items = sorted(combined.items(), key=lambda x: x[1], reverse=True)
        topics = []
        for name, score in sorted_items[:max_topics]:
            kw = name.split()
            topics.append(DocumentTopic(name=name.title(), score=score, keywords=kw))
        return topics

    def extract_references(self, text: str) -> list[DocumentReference]:
        import re
        references = []
        url_pattern = r"https?://[^\s<>\"']+|www\.[^\s<>\"']+"
        for url in re.findall(url_pattern, text):
            trimmed = url.rstrip(".,;:!?)")
            references.append(DocumentReference(url=trimmed, title=trimmed))
        return references

    def extract_dates(self, text: str) -> list[str]:
        import re
        dates = set()
        patterns = [
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},?\s*\d{4}\b",
        ]
        for pattern in patterns:
            for match in re.findall(pattern, text):
                dates.add(match)
        return sorted(dates)

    def analyze(self, text: str, title: str = "") -> dict:
        entities = self.extract_entities(text)
        topics = self.extract_topics(text)
        references = self.extract_references(text)
        dates = self.extract_dates(text)
        word_count = len(text.split())
        return {
            "title": title,
            "word_count": word_count,
            "entities": [{"name": e.name, "type": e.type, "confidence": e.confidence} for e in entities],
            "topics": [{"name": t.name, "score": t.score, "keywords": t.keywords} for t in topics],
            "references": [{"url": r.url, "title": r.title} for r in references],
            "dates": dates,
            "entity_count": len(entities),
            "topic_count": len(topics),
        }
