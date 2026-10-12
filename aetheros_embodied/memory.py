"""Physical memory (§61-63, §117, §175-179): TTL'd object/device
memory, trajectory records, embodied skills with environment-scoped
generalization, experience decay, knowledge-graph hooks."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEntry:
    key: str
    value: Any = None
    at: float = field(default_factory=time.time)
    ttl_s: float = 3600.0
    confidence: float = 0.8
    environment: str = ""
    provenance: str = "observation"  # observation|experience|human|manual

    def alive(self, at: Optional[float] = None) -> bool:
        return (at or time.time()) - self.at <= self.ttl_s


@dataclass
class EmbodiedSkill:
    name: str
    preconditions: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    trajectory: List[str] = field(default_factory=list)
    required_devices: List[str] = field(default_factory=list)
    safety: str = "LOW"
    verification: str = "state_change"
    success_criteria: str = ""
    failure_modes: List[str] = field(default_factory=list)
    validated_in: List[str] = field(default_factory=list)  # environments
    version: str = "v1"


class PhysicalMemory:
    def __init__(self) -> None:
        self.entries: Dict[str, MemoryEntry] = {}
        self.skills: Dict[str, EmbodiedSkill] = {}
        self.successes: List[Dict[str, Any]] = []
        self.failures: List[Dict[str, Any]] = []

    def remember(self, key: str, value: Any, ttl_s: float = 3600.0,
                 environment: str = "",
                 provenance: str = "observation") -> None:
        self.entries[key] = MemoryEntry(key, value, time.time(), ttl_s,
                                        environment=environment,
                                        provenance=provenance)

    def recall(self, key: str, environment: str = "") -> Optional[Any]:
        e = self.entries.get(key)
        if e is None or not e.alive():
            self.entries.pop(key, None)
            return None
        # §122: environment-scoped — different env needs revalidation
        if environment and e.environment and e.environment != environment:
            return {"value": e.value, "stale_environment": True,
                    "note": "learned elsewhere — validate before use"}
        return e.value

    def purge_expired(self) -> int:
        dead = [k for k, e in self.entries.items() if not e.alive()]
        for k in dead:
            del self.entries[k]
        return len(dead)

    def add_skill(self, skill: EmbodiedSkill) -> None:
        self.skills[skill.name] = skill

    def skill_for(self, name: str, environment: str) -> Optional[Dict[str, Any]]:
        s = self.skills.get(name)
        if s is None:
            return None
        if environment not in s.validated_in:
            return {"skill": s.name,
                    "blocked": True,
                    "reason": f"not validated in {environment} (§122)"}
        return {"skill": s.name, "blocked": False,
                "trajectory": s.trajectory}

    def record_run(self, skill: str, ok: bool, environment: str,
                   note: str = "") -> None:
        (self.successes if ok else self.failures).append(
            {"skill": skill, "environment": environment, "note": note,
             "at": time.time()})

    # knowledge-graph hooks (§179)
    def graph_triples(self) -> List[Dict[str, str]]:
        triples = []
        for k, e in self.entries.items():
            if k.startswith("located:"):
                triples.append({"src": k.split(":", 1)[1],
                                "rel": "LOCATED_IN", "dst": e.environment or "?"})
        return triples
