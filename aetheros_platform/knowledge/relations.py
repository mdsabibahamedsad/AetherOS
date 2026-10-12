"""Relation mapping — infer and manage relationships between entities."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


RELATION_PATTERNS: dict[str, list[tuple[str, str, float]]] = {
    "works_at": [
        (r'\b(works?|employed|job|role)\s+(?:at|for|with)\s+', "person", 0.8),
        (r'\b(?:at|@)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s|\.|,|$)', "person", 0.6),
    ],
    "uses": [
        (r'\b(?:uses?|utilize|runs?|deployed)\s+(?:with|on|using)\s+', None, 0.7),
        (r'\b(written|built|coded|developed)\s+(?:in|with|using)\s+', None, 0.7),
    ],
    "depends_on": [
        (r'\b(?:depends?|requires?|needs?|imports?)\s+', None, 0.8),
        (r'\b(?:based\s+on|built\s+on\s+top\s+of)\s+', None, 0.7),
    ],
    "located_at": [
        (r'\b(?:located|hosted|deployed|running)\s+(?:at|on|in)\s+', None, 0.7),
        (r'\b(?:server|host|endpoint)\s*[:=]\s*', None, 0.5),
    ],
    "created_by": [
        (r'\b(?:created|authored|built|developed|wrote)\s+by\s+', None, 0.9),
        (r'\b(?:copyright|©)\s+\d{4}\s+', None, 0.5),
    ],
    "communicates_with": [
        (r'\b(?:calls?|invokes|sends?|receives?|communicates)\s+(?:with|to)\s+', None, 0.7),
        (r'\b(?:API|endpoint|webhook)\s+(?:call|request|response)\s+', None, 0.6),
    ],
    "deployed_on": [
        (r'\b(?:deployed|hosted|running|released)\s+(?:on|to)\s+', None, 0.8),
        (r'\b(?:production|staging|dev|test)\s+(?:server|env|instance)\s+', None, 0.5),
    ],
    "version_of": [
        (r'\bv?(\d+\.\d+\.\d+)\b', None, 0.9),
        (r'\bversion\s+(\d+\.\d+(?:\.\d+)?)\b', None, 0.95),
    ],
}


COMMON_RELATION_TYPES = [
    "works_at", "uses", "depends_on", "located_at", "created_by",
    "communicates_with", "deployed_on", "version_of", "related_to",
    "contains", "part_of", "precedes", "follows", "recommends",
    "implements", "extends", "configures", "monitors", "authenticates_with",
]


class RelationMapper:
    def __init__(self):
        self._compiled: dict[str, list[tuple[re.Pattern, Optional[str], float]]] = {}
        for rel_type, patterns in RELATION_PATTERNS.items():
            self._compiled[rel_type] = [
                (re.compile(p, re.IGNORECASE), target_type, weight)
                for p, target_type, weight in patterns
            ]

    def infer_from_text(self, text: str,
                         known_entities: list[dict]) -> list[dict]:
        relations = []
        for ent in known_entities:
            for rel_type, patterns in self._compiled.items():
                for pattern, target_type, weight in patterns:
                    for match in pattern.finditer(text):
                        start = match.start()
                        end = match.end()
                        window_start = max(0, start - 60)
                        window_end = min(len(text), end + 60)
                        context = text[window_start:window_end]
                        for other in known_entities:
                            if other["id"] == ent["id"]:
                                continue
                            if other["id"] in context or other["value"] in context:
                                relations.append({
                                    "type": rel_type,
                                    "source_id": ent["id"],
                                    "source_value": ent["value"],
                                    "target_id": other["id"],
                                    "target_value": other["value"],
                                    "weight": weight * ent.get("confidence", 0.8),
                                    "context": context,
                                })
        return self._deduplicate(relations)

    def score_relation(self, source: dict, target: dict,
                        relation_type: str) -> float:
        base_weight = {
            "works_at": 1.0, "created_by": 1.0, "depends_on": 0.9,
            "uses": 0.8, "contains": 0.8, "part_of": 0.9,
            "communicates_with": 0.7, "implements": 0.9,
            "version_of": 1.0, "related_to": 0.5,
        }.get(relation_type, 0.5)
        confidence = (source.get("confidence", 0.8) *
                       target.get("confidence", 0.8))
        return round(base_weight * confidence, 2)

    def suggest_relation_type(self, source_type: str,
                               target_type: str) -> str:
        suggestions = {
            ("person", "organization"): "works_at",
            ("person", "software"): "uses",
            ("software", "software"): "depends_on",
            ("organization", "software"): "created_by",
            ("software", "version"): "version_of",
            ("software", "platform"): "deployed_on",
            ("person", "person"): "related_to",
            ("tool", "tool"): "depends_on",
        }
        return suggestions.get((source_type, target_type), "related_to")

    def _deduplicate(self, relations: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for r in sorted(relations, key=lambda x: -x["weight"]):
            key = (r["type"], r["source_id"], r["target_id"])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

    def get_relation_types(self) -> list[str]:
        return COMMON_RELATION_TYPES
