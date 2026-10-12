"""Entity extraction — extract structured entities from text."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class EntityExtractor:
    ENTITY_PATTERNS: dict[str, list[str]] = {
        "person": [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
            r'(?:Dr|Mr|Ms|Mrs|Prof)\. [A-Z][a-z]+\b',
        ],
        "email": [
            r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b',
        ],
        "url": [
            r'https?://[^\s<>"]+|www\.[^\s<>"]+\.[^\s<>"]+',
        ],
        "date": [
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b\d{2}/\d{2}/\d{4}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',
        ],
        "version": [
            r'\bv?\d+\.\d+\.\d+(?:[-.][a-zA-Z0-9]+)?\b',
            r'\bv?\d+\.\d+(?:[-.][a-zA-Z0-9]+)?\b',
        ],
        "file_path": [
            r'[/\\][\w.]+[/\\][\w./\\]+',
            r'\b[\w./-]+\.[a-zA-Z]{2,4}\b',
        ],
        "code_identifier": [
            r'\b[A-Z][A-Z0-9_]{2,}\b',
            r'\b[a-z][a-z0-9_]{2,}(?:\s*=\s*|\s*\(|\s*:)'  ,
        ],
        "api_key": [
            r'\b(?:sk|pk|api)[-_]?[a-zA-Z0-9]{16,}\b',
            r'(?:key|token|secret)\s*[:=]\s*["\'][a-zA-Z0-9_\-]{8,}["\']',
        ],
        "language": [
            r'\b(?:Python|JavaScript|TypeScript|Rust|Go|Java|Kotlin|Ruby|PHP|C\+\+|C#|Swift)\b',
        ],
        "framework": [
            r'\b(?:React|Vue|Angular|Django|Flask|FastAPI|Spring|Rails|Laravel|Next\.js|Nuxt)\b',
        ],
        "tool": [
            r'\b(?:Docker|Kubernetes|Terraform|Ansible|Jenkins|Git|Node\.?js|npm|yarn|pnpm)\b',
        ],
    }

    def __init__(self):
        self._compiled: dict[str, list[re.Pattern]] = {}
        for etype, patterns in self.ENTITY_PATTERNS.items():
            self._compiled[etype] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def extract(self, text: str, types: list[str] = None) -> list[dict]:
        entities = []
        seen = set()
        target_types = types or list(self._compiled.keys())
        for etype in target_types:
            patterns = self._compiled.get(etype, [])
            for pattern in patterns:
                for match in pattern.finditer(text):
                    value = match.group(0).strip()
                    if value.lower() not in seen:
                        seen.add(value.lower())
                        entities.append({
                            "type": etype,
                            "value": value,
                            "start": match.start(),
                            "end": match.end(),
                            "confidence": 0.8 if etype != "api_key" else 0.5,
                        })
        return entities

    def extract_with_context(self, text: str,
                              types: list[str] = None) -> list[dict]:
        entities = self.extract(text, types)
        for ent in entities:
            start = max(0, ent["start"] - 40)
            end = min(len(text), ent["end"] + 40)
            ent["context"] = text[start:end]
        return entities

    def classify_entity_type(self, value: str) -> str:
        for etype, patterns in self._compiled.items():
            for p in patterns:
                if p.fullmatch(value):
                    return etype
        return "unknown"

    def add_custom_pattern(self, entity_type: str, pattern: str):
        self.ENTITY_PATTERNS.setdefault(entity_type, [])
        self.ENTITY_PATTERNS[entity_type].append(pattern)
        self._compiled.setdefault(entity_type, [])
        self._compiled[entity_type].append(re.compile(pattern, re.IGNORECASE))

    def extract_entities_batch(self, texts: list[str]) -> list[list[dict]]:
        return [self.extract(t) for t in texts]

    def get_supported_types(self) -> list[str]:
        return list(self.ENTITY_PATTERNS.keys())
