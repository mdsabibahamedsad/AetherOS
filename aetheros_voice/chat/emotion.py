from __future__ import annotations

import re
from typing import Any


class EmotionAwareness:
    def __init__(self):
        self._emotion: str = "neutral"
        self._confidence: float = 1.0
        self._emotion_keywords = {
            "happy": ["great", "awesome", "amazing", "wonderful", "fantastic", "excellent", "love", "perfect", "thank"],
            "sad": ["sad", "unfortunate", "sorry", "unhappy", "disappointed", "regret"],
            "angry": ["angry", "frustrated", "annoyed", "furious", "irritated", "mad"],
            "confused": ["what", "huh", "confused", "unclear", "don't understand", "confusing"],
            "urgent": ["now", "immediately", "hurry", "quick", "emergency", "asap", "critical"],
            "excited": ["wow", "exciting", "incredible", "amazing", "phenomenal", "thrilled"],
            "worried": ["worried", "concerned", "nervous", "anxious", "afraid"],
        }

    def detect(self, text: str) -> tuple[str, float]:
        lower = text.lower()
        scores: dict[str, float] = {"neutral": 0.5}
        for emotion, keywords in self._emotion_keywords.items():
            score = sum(2.0 if kw in lower else 0.0 for kw in keywords)
            if score > 0:
                scores[emotion] = score
        dominant = max(scores, key=scores.get)
        self._emotion = dominant
        self._confidence = min(scores[dominant] / max(sum(scores.values()), 1), 1.0)
        return self._emotion, self._confidence

    @property
    def emotion(self) -> str:
        return self._emotion

    def should_interrupt(self, text: str) -> bool:
        lower = text.lower()
        interrupt_phrases = ["stop", "wait", "hold on", "shut up", "quiet", "never mind", "cancel"]
        return any(p in lower for p in interrupt_phrases)

    def get_voice_tone(self) -> str:
        tones = {
            "happy": "cheerful",
            "sad": "gentle",
            "angry": "calm",
            "confused": "helpful",
            "urgent": "faster",
            "excited": "energetic",
            "worried": "reassuring",
            "neutral": "neutral",
        }
        return tones.get(self._emotion, "neutral")
