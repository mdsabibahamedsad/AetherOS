from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ExtractedTask:
    description: str
    assignee: str = ""
    deadline: str = ""
    priority: str = "medium"
    source_message: str = ""
    confidence: float = 0.5


@dataclass
class ExtractedDecision:
    description: str
    rationale: str = ""
    made_by: str = ""
    date: str = ""
    alternatives: list[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class ConversationInsight:
    type: str
    content: str
    confidence: float = 0.0
    source_text: str = ""


class ConversationIntelligence:
    def __init__(self):
        self._task_patterns = [
            (r"(?:we|i|you)\s+(?:need to|must|should|have to|will)\s+([^.!?]+)", 0.6),
            (r"(?:can you|could you|please)\s+([^.!?]+)", 0.5),
            (r"(?:todo|to-do|to do|action item|action-item):\s*([^.!?]+)", 0.9),
            (r"(?:remember to|don't forget to|make sure to)\s+([^.!?]+)", 0.7),
            (r"(?:assigned|assign|owner):\s*([^.!?]+)", 0.8),
        ]
        self._deadline_patterns = [
            r"(?:by|before|due|deadline)\s+(?:next\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|today|tomorrow|end of|eod)",
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"(?:by|before|due)\s+(?:the\s+)?\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*",
        ]
        self._decision_patterns = [
            r"(?:we|i)\s+(?:decided|agreed|chose|selected|opted for|went with)\s+([^.!?]+)",
            r"(?:decision|conclusion|resolution):\s*([^.!?]+)",
            r"(?:final|agreed|settled)\s+(?:on|upon)\s+([^.!?]+)",
        ]
        self._question_patterns = [
            r"(?:what|when|where|why|how|who)\s+(?:is|are|was|were|will|would|could|should|does|do)\s+[^?]+\?",
            r"(?:can|could|will|would|do|does|is|are)\s+[^?]+\?",
        ]

    def extract_tasks(self, conversation: list[dict]) -> list[ExtractedTask]:
        tasks = []
        for msg in conversation:
            content = msg.get("content", msg.get("text", ""))
            sender = msg.get("sender_name", msg.get("sender", msg.get("author", "")))
            for pattern, confidence in self._task_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    desc = match.strip()
                    if len(desc) < 5 or len(desc) > 300:
                        continue
                    deadline = self._extract_deadline(content)
                    tasks.append(ExtractedTask(
                        description=desc,
                        assignee=sender if sender else "",
                        deadline=deadline,
                        source_message=content[:200],
                        confidence=confidence,
                    ))
        return tasks

    def _extract_deadline(self, text: str) -> str:
        for pattern in self._deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return ""

    def extract_decisions(self, conversation: list[dict]) -> list[ExtractedDecision]:
        decisions = []
        for msg in conversation:
            content = msg.get("content", msg.get("text", ""))
            sender = msg.get("sender_name", msg.get("sender", msg.get("author", "")))
            for pattern, confidence_base in [(p, 0.6) for p in self._decision_patterns]:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    desc = match.strip()
                    if len(desc) < 5:
                        continue
                    decisions.append(ExtractedDecision(
                        description=desc,
                        made_by=sender if sender else "",
                        date=datetime.now().isoformat(),
                        confidence=confidence_base,
                    ))
        return decisions

    def extract_questions(self, conversation: list[dict]) -> list[ConversationInsight]:
        questions = []
        for msg in conversation:
            content = msg.get("content", msg.get("text", ""))
            for pattern in self._question_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    questions.append(ConversationInsight(
                        type="question",
                        content=match.strip(),
                        confidence=0.8,
                        source_text=content[:200],
                    ))
        return questions

    def extract_people(self, conversation: list[dict]) -> list[str]:
        people = set()
        for msg in conversation:
            sender = msg.get("sender_name", msg.get("sender", msg.get("author", "")))
            if sender:
                people.add(sender)
            content = msg.get("content", msg.get("text", ""))
            mentions = re.findall(r"@(\w+)", content)
            for mention in mentions:
                people.add(mention)
        return sorted(people)

    def extract_topics(self, conversation: list[dict]) -> list[str]:
        from collections import Counter
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "has", "have",
                     "had", "do", "does", "did", "will", "would", "could", "should",
                     "may", "might", "i", "you", "he", "she", "it", "we", "they",
                     "this", "that", "these", "those", "am", "to", "of", "in", "for",
                     "on", "with", "at", "by", "from", "as", "into", "through", "and",
                     "but", "or", "nor", "not", "so", "if", "then", "than", "too",
                     "very", "just", "also", "now", "how", "what", "when", "where",
                     "why", "who", "which", "all", "each", "every", "some", "any",
                     "no", "only", "own", "same", "more", "most", "other", "about",
                     "up", "down", "out", "off", "over", "under", "again", "further",
                     "once", "here", "there", "because", "well", "both"}
        words = []
        for msg in conversation:
            content = msg.get("content", msg.get("text", ""))
            words.extend(re.findall(r"[a-zA-Z]{5,}", content.lower()))
        words = [w for w in words if w not in stopwords]
        counter = Counter(words)
        return [word for word, _ in counter.most_common(10)]

    def analyze(self, conversation: list[dict]) -> dict:
        tasks = self.extract_tasks(conversation)
        decisions = self.extract_decisions(conversation)
        questions = self.extract_questions(conversation)
        people = self.extract_people(conversation)
        topics = self.extract_topics(conversation)
        return {
            "tasks": [{"description": t.description, "assignee": t.assignee, "deadline": t.deadline, "confidence": t.confidence} for t in tasks],
            "decisions": [{"description": d.description, "made_by": d.made_by, "confidence": d.confidence} for d in decisions],
            "questions": [{"content": q.content} for q in questions],
            "people": people,
            "topics": topics,
            "task_count": len(tasks),
            "decision_count": len(decisions),
            "participant_count": len(people),
        }
