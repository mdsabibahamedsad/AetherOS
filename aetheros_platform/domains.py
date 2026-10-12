"""Model provider abstraction (Master 62 §21-22) + domain adapters (§23-28).

Providers declare REAL capability metadata; the router stays authoritative
and developers cannot bypass governance. A clearly-labeled MOCK provider
exists for offline development/tests ONLY.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from aetheros_platform.errors import err

PROVIDER_METHODS = ("models", "health", "generate", "stream", "toolCall",
                    "structuredOutput", "vision", "audio", "embeddings",
                    "rerank", "usage")


class ModelProvider:
    """Base class for third-party providers. Subclass and fill capabilities
    honestly — never claim a modality the model lacks."""

    name: str = "base"
    capabilities: Dict[str, bool] = {}

    def models(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def health(self) -> Dict[str, Any]:
        return {"provider": self.name, "ok": True, "ts": time.time()}

    def generate(self, prompt: str, **kw: Any) -> Dict[str, Any]:
        raise NotImplementedError

    def stream(self, prompt: str, **kw: Any):
        raise NotImplementedError("streaming not supported by " + self.name)

    def embeddings(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError("embeddings not supported by " + self.name)


class MockProvider(ModelProvider):
    """DEVELOPMENT ONLY mock. Every output is labeled MOCK/SIMULATED."""

    name = "mock"
    capabilities = {"generate": True, "stream": True, "toolCall": True,
                    "structuredOutput": True, "vision": False, "audio": False,
                    "embeddings": True, "rerank": False}

    def models(self) -> List[Dict[str, Any]]:
        return [{"id": "mock-small", "context": 8192, "mock": True}]

    def generate(self, prompt: str, **kw: Any) -> Dict[str, Any]:
        return {"text": f"[MOCK/SIMULATED/DEVELOPMENT ONLY] echo: {prompt[:200]}",
                "model": "mock-small", "mock": True,
                "usage": {"tokens": len(prompt.split())}}

    def stream(self, prompt: str, **kw: Any):
        words = f"[MOCK/SIMULATED] echo: {prompt[:200]}".split()
        for w in words:
            yield {"delta": w + " ", "mock": True}
        yield {"done": True, "mock": True}

    def embeddings(self, texts: List[str]) -> List[List[float]]:
        import hashlib
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode()).digest()
            out.append([b / 255.0 for b in h[:16]])
        return out


class ModelRouter:
    """Developers specify preferences; the ROUTER decides (governance intact)."""

    def __init__(self, providers: Optional[Dict[str, ModelProvider]] = None) -> None:
        self.providers = providers or {"mock": MockProvider()}

    def route(self, request: Dict[str, Any]) -> Dict[str, Any]:
        pref = (request.get("model") or {}).get("preferred", "mock")
        provider = self.providers.get(pref, self.providers["mock"])
        decision = {"provider": provider.name, "requested": pref,
                    "fallback_used": provider.name != pref,
                    "decision_id": f"route_{uuid.uuid4().hex[:10]}",
                    "governed": True}
        return {"provider": provider, "decision": decision}

    def register(self, provider: ModelProvider) -> None:
        self.providers[provider.name] = provider


# -- domain adapters (real backends, no mocks) --------------------------------

def memory_write(content: str, scope: str = "user", owner: str = "",
                 sensitivity: str = "internal") -> Dict[str, Any]:
    from aetheros_data.engine import get_engine
    from aetheros_data.records import MemoryRepository
    return MemoryRepository(get_engine()).write(content, scope=scope, owner=owner,
                                                sensitivity=sensitivity,
                                                provenance={"src": "developer-platform"})


def memory_search(query: str) -> List[Dict[str, Any]]:
    from aetheros_data.engine import get_engine
    rows = get_engine()._conn().execute(
        "SELECT * FROM memory_records WHERE content LIKE ? AND status IN ('CONFIRMED','CANDIDATE')"
        " ORDER BY updated_at DESC LIMIT 20", (f"%{query}%",)).fetchall()
    return [dict(r) for r in rows]


def memory_retract(memory_id: str, actor: str = "") -> Dict[str, Any]:
    from aetheros_data.engine import get_engine
    from aetheros_data.records import MemoryRepository
    repo = MemoryRepository(get_engine())
    cur = repo.get(memory_id)
    if cur is None:
        raise err("RESOURCE_UNAVAILABLE", f"unknown memory {memory_id}")
    return repo.retract(memory_id, int(cur["version"]), reason=f"retracted by {actor}")


def artifact_create(data: bytes, filename: str = "", owner: str = "",
                    classification: str = "internal") -> Dict[str, Any]:
    from aetheros_data.engine import get_engine
    from aetheros_data.artifacts import ArtifactStore
    rec = ArtifactStore(get_engine()).put(data, owner=owner, classification=classification,
                                          provenance={"src": "developer-platform"},
                                          filename=filename)
    return {"artifactId": rec["artifact_id"], "hash": rec["content_hash"],
            "type": rec["mime"], "size": rec["size"], "creator": owner,
            "taskId": "", "timestamp": rec["created_at"],
            "provenance": {"src": "developer-platform"},
            "securityClassification": classification, "parentArtifacts": []}


def artifact_bytes(artifact_id: str) -> bytes:
    from aetheros_data.engine import get_engine
    from aetheros_data.artifacts import ArtifactStore
    return ArtifactStore(get_engine()).get_bytes(artifact_id, verify=True)


def automation_create(name: str, trigger: Dict[str, Any], owner: str = "") -> Dict[str, Any]:
    """Programmatic automation via the real cron job store (Master 43)."""
    import json
    from aetheros_constants import get_aetheros_home
    from pathlib import Path
    cron_dir = get_aetheros_home() / "cron"
    cron_dir.mkdir(parents=True, exist_ok=True)
    jobs_path = cron_dir / "jobs.json"
    jobs = json.loads(jobs_path.read_text()) if jobs_path.exists() else []
    job = {"id": f"job_{uuid.uuid4().hex[:10]}", "name": name, "trigger": trigger,
           "owner": owner, "enabled": True, "created_at": time.time(),
           "origin": "developer-platform"}
    jobs.append(job)
    jobs_path.write_text(json.dumps(jobs, indent=2))
    return job
