from __future__ import annotations

import re
from typing import Any


class CommandParser:
    def __init__(self):
        self._patterns: dict[str, str] = {}

    def register_pattern(self, name: str, pattern: str):
        self._patterns[name] = pattern

    async def parse(self, text: str) -> dict[str, Any]:
        lower = text.lower().strip()
        result: dict[str, Any] = {
            "raw": text,
            "intent": "",
            "entities": {},
            "confidence": 1.0,
        }

        intents = {
            "open": r"\b(open|launch|start)\s+(\w+)",
            "close": r"\b(close|quit|exit)\s+(\w+)",
            "search": r"\b(search|find|look up)\s+(.+?)$",
            "create": r"\b(create|make|new)\s+(.+?)(\s+(called|named)\s+(.+))?$",
            "navigate": r"\b(go to|navigate|open)\s+(.+?)$",
            "click": r"\b(click|tap|press)\s+(.+?)$",
            "scroll": r"\b(scroll)\s+(up|down|left|right)",
            "type": r"\b(type|enter|input)\s+(.+?)$",
            "read": r"\b(read|summarize)\s+(.+?)$",
            "volume": r"\b(volume|sound)\s+(up|down|mute|unmute|\d+)",
        }

        for intent, pattern in intents.items():
            match = re.search(pattern, lower)
            if match:
                result["intent"] = intent
                result["entities"]["raw_match"] = match.groups()
                if intent == "open":
                    result["entities"]["app"] = match.group(2)
                elif intent == "search":
                    result["entities"]["query"] = match.group(2)
                elif intent == "scroll":
                    result["entities"]["direction"] = match.group(2)
                elif intent == "type":
                    result["entities"]["text"] = match.group(2)
                break

        return result
