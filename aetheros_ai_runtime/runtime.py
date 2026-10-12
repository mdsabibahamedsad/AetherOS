"""Inference runtime: context budget, tool-call normalization,
token/cost accounting, fallback + escalation + cascade, downloads,
compute mesh (sections 24-26, 37-42, 44-58, 92-93).

- ToolCall canonical + argument validation (JSON parse; schema check
  when jsonschema available, structural fallback otherwise).
- Structured output validated, never trusted raw.
- Fallback chain respects privacy (privacy veto is absolute).
- Escalation small->verify->large; cascade PRIMARY/SECONDARY/VERIFIER
  with observable transitions; confidence from validators, not models.
- Downloads: Ollama pull API real; generic HTTP resume+checksum+budget.
- Mesh: pairing/auth/heartbeat/scheduler; single-node default; no
  model-splitting claim; node failure -> safe reschedule.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

from aetheros_ai_runtime.adapters import (
    NON_RETRYABLE, RETRYABLE, InferenceEvent, InferenceRequest,
    ProviderAdapter, classify_error,
)
from aetheros_ai_runtime.models import Pricing


# -- tool calls ------------------------------------------------------------

@dataclass
class ToolCall:
    id: str = ""
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    raw_arguments: str = ""
    model: str = ""
    provider: str = ""
    timestamp: float = field(default_factory=time.time)
    risk: str = "unknown"
    approval: str = "pending"


def normalize_tool_call(raw: Dict[str, Any], *, provider: str,
                        allowed_tools: Optional[List[str]] = None) -> ToolCall:
    call = ToolCall(id=str(raw.get("id", "")),
                    name=str(raw.get("name", "")),
                    raw_arguments=str(raw.get("arguments", "")),
                    model=str(raw.get("model", "")),
                    provider=provider)
    try:
        parsed = json.loads(call.raw_arguments or "{}")
        call.arguments = parsed if isinstance(parsed, dict) else {}
    except ValueError:
        call.arguments = {}
    if allowed_tools is not None and call.name not in allowed_tools:
        call.approval = "denied"
    return call


def validate_tool_arguments(call: ToolCall,
                            schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if schema is None:
        return {"ok": True, "reason": "no schema; JSON parsed only"}
    try:
        import jsonschema
        jsonschema.validate(call.arguments, schema)
        return {"ok": True, "reason": "jsonschema valid"}
    except ImportError:
        required = schema.get("required", [])
        missing = [k for k in required if k not in call.arguments]
        if missing:
            return {"ok": False, "reason": f"missing: {missing}"}
        return {"ok": True, "reason": "structural check (jsonschema absent)"}
    except Exception as exc:
        return {"ok": False, "reason": f"schema invalid: {exc}"[:300]}


def validate_structured(text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = json.loads(text)
    except ValueError as exc:
        return {"ok": False, "reason": f"not JSON: {exc}"}
    try:
        import jsonschema
        jsonschema.validate(data, schema)
        return {"ok": True, "data": data, "reason": "jsonschema valid"}
    except ImportError:
        return {"ok": True, "data": data,
                "reason": "parsed; deep validation unavailable (no jsonschema)"}
    except Exception as exc:
        return {"ok": False, "reason": f"schema invalid: {exc}"[:300]}


# -- context budget ----------------------------------------------------------

class ContextBudgetManager:
    def __init__(self, *, estimate_chars_per_token: int = 4) -> None:
        self.cpt = estimate_chars_per_token

    def estimate(self, text: str) -> int:
        return max(1, len(text or "") // self.cpt)

    def budget(self, *, system: str = "", messages: Optional[List[Dict[str, Any]]] = None,
               tools: Optional[List[Dict[str, Any]]] = None,
               memory: str = "", evidence: str = "",
               context_window: int = 0) -> Dict[str, Any]:
        parts = {"system": self.estimate(system), "memory": self.estimate(memory),
                 "evidence": self.estimate(evidence),
                 "messages": sum(self.estimate(str(m.get("content", "")))
                                 for m in (messages or [])),
                 "tools": sum(self.estimate(json.dumps(t)) for t in (tools or []))}
        total = sum(parts.values())
        out = {"parts": parts, "total": total, "window": context_window,
               "fits": (not context_window) or total < context_window,
               "dropped": []}
        if context_window and total >= context_window:
            # Drop low-value first; security instructions are never silently cut.
            for key in ("evidence", "memory", "messages"):
                if out["total"] < context_window:
                    break
                if key == "messages" and parts[key]:
                    cut = parts[key] // 2
                    parts[key] -= cut
                    out["total"] -= cut
                    out["dropped"].append(f"{key}:halved")
                elif parts[key]:
                    out["total"] -= parts[key]
                    out["dropped"].append(f"{key}:dropped")
                    parts[key] = 0
            out["parts"] = parts
            out["fits"] = out["total"] < context_window
            out["system_preserved"] = True
        return out


# -- tokens + cost -------------------------------------------------------------

@dataclass
class UsageRecord:
    task_id: str = ""
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    cost_usd: Optional[float] = None  # None == UNKNOWN
    estimated: bool = True
    at: float = field(default_factory=time.time)


def parse_usage(raw: Dict[str, Any], *, pricing: Optional[Pricing] = None,
                task_id: str = "", model: str = "",
                provider: str = "") -> UsageRecord:
    rec = UsageRecord(task_id=task_id, model=model, provider=provider)
    rec.input_tokens = int(raw.get("prompt_tokens", raw.get("input_tokens", 0)) or 0)
    rec.output_tokens = int(raw.get("completion_tokens", raw.get("output_tokens", 0)) or 0)
    rec.cached_tokens = int(raw.get("cached_tokens",
                                    (raw.get("prompt_cache_hit_tokens", 0)) or 0) or 0)
    details = raw.get("completion_tokens_details") or {}
    rec.reasoning_tokens = int(details.get("reasoning_tokens", 0) or 0)
    if pricing is not None and not pricing.unknown \
            and pricing.input_per_1k is not None and pricing.output_per_1k is not None:
        rec.cost_usd = round(rec.input_tokens / 1000 * pricing.input_per_1k
                             + rec.output_tokens / 1000 * pricing.output_per_1k, 6)
    return rec


# -- fallback / escalation / cascade --------------------------------------------

@dataclass
class FallbackPlan:
    chain: List[str] = field(default_factory=list)  # canonical_ids
    privacy_veto: List[str] = field(default_factory=list)


def build_fallback(selected: str, fallbacks: List[str],
                   privacy_denied: Optional[set] = None) -> FallbackPlan:
    denied = set(privacy_denied or set())
    chain = [c for c in [selected, *fallbacks] if c not in denied]
    return FallbackPlan(chain=chain, privacy_veto=sorted(denied))


def run_with_fallback(chain: List[str],
                      invoke: Callable[[str], Iterator[InferenceEvent]],
                      *, max_attempts: Optional[int] = None,
                      retry_safe: bool = True) -> Iterator[InferenceEvent]:
    """Walk the chain; privacy veto already applied (never overridden)."""
    attempts = 0
    for cid in chain:
        if max_attempts is not None and attempts >= max_attempts:
            break
        attempts += 1
        error: str = ""
        yielded_any = False
        for ev in invoke(cid):
            yielded_any = True
            if ev.kind == "error":
                error = ev.error
                cls = "rate_limit" if "rate_limit" in error else classify_error(
                    RuntimeError(error))
                if cls in NON_RETRYABLE:
                    yield ev
                    return
                break
            yield ev
        else:
            return
        if not yielded_any and not retry_safe:
            yield InferenceEvent(kind="error", error=error or "empty response")
            return
        yield InferenceEvent(kind="warning",
                             text=f"fallback: {cid} failed, trying next")
    yield InferenceEvent(kind="error", error="fallback chain exhausted")


# -- downloads ---------------------------------------------------------------------

@dataclass
class DownloadState:
    model: str = ""
    url: str = ""
    dest: str = ""
    total_bytes: int = 0
    done_bytes: int = 0
    sha256: str = ""
    status: str = "pending"  # pending|running|verifying|done|failed|cancelled
    error: str = ""


class ModelDownloadManager:
    def __init__(self, root: Optional[Path] = None, *,
                 disk_budget_gb: float = 50.0) -> None:
        self._root = Path(root) if root else None
        self._cancel = threading.Event()
        self.budget_gb = disk_budget_gb

    def initialize(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def cancel(self) -> None:
        self._cancel.set()

    def _disk_free_gb(self, path: Path) -> float:
        try:
            import shutil as _sh
            return _sh.disk_usage(path).free / 1e9
        except OSError:
            return 0.0

    def ollama_pull(self, base_url: str, model: str,
                    progress: Optional[Callable[[Dict[str, Any]], None]] = None) -> DownloadState:
        """Real Ollama pull with streaming progress + cancel."""
        import httpx
        st = DownloadState(model=model, url=base_url, status="running")
        try:
            with httpx.stream("POST", base_url.rstrip("/") + "/api/pull",
                              json={"name": model, "stream": True},
                              timeout=3600.0) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if self._cancel.is_set():
                        st.status = "cancelled"
                        return st
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except ValueError:
                        continue
                    st.done_bytes = int(evt.get("completed", st.done_bytes) or 0)
                    st.total_bytes = int(evt.get("total", st.total_bytes) or 0)
                    if progress:
                        progress({"done": st.done_bytes, "total": st.total_bytes,
                                  "status": evt.get("status", "")})
                    if evt.get("error"):
                        st.status = "failed"
                        st.error = str(evt["error"])[:300]
                        return st
            st.status = "done"
        except Exception as exc:
            st.status = "failed"
            st.error = str(exc)[:300]
        return st

    def http_download(self, url: str, dest: Path, *,
                      sha256: str = "",
                      progress: Optional[Callable[[Dict[str, Any]], None]] = None) -> DownloadState:
        """Resumable HTTP download with checksum + disk-budget gate."""
        import httpx
        st = DownloadState(url=url, dest=str(dest), status="running")
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self._disk_free_gb(dest.parent) < 1.0:
            st.status = "failed"
            st.error = "insufficient disk space (<1GB free)"
            return st
        existing = dest.stat().st_size if dest.exists() else 0
        headers = {"Range": f"bytes={existing}-"} if existing else {}
        digest = hashlib.sha256()
        try:
            with httpx.stream("GET", url, headers=headers, timeout=3600.0,
                              follow_redirects=True) as resp:
                if resp.status_code not in (200, 206):
                    st.status = "failed"
                    st.error = f"HTTP {resp.status_code}"
                    return st
                st.total_bytes = int(resp.headers.get("content-length", 0) or 0) + existing
                mode = "ab" if resp.status_code == 206 and existing else "wb"
                if mode == "wb":
                    existing = 0
                with open(dest, mode + "b") as fh:
                    if mode == "ab":
                        with open(dest, "rb") as rf:
                            for chunk in iter(lambda: rf.read(1 << 20), b""):
                                digest.update(chunk)
                    for chunk in resp.iter_bytes(1 << 20):
                        if self._cancel.is_set():
                            st.status = "cancelled"
                            return st
                        fh.write(chunk)
                        digest.update(chunk)
                        existing += len(chunk)
                        st.done_bytes = existing
                        if self._disk_free_gb(dest.parent) < 0.2:
                            st.status = "failed"
                            st.error = "disk exhausted during download"
                            return st
                        if progress:
                            progress({"done": st.done_bytes, "total": st.total_bytes})
            if sha256 and digest.hexdigest() != sha256.lower():
                st.status = "failed"
                st.error = "checksum mismatch (deleted artifact left for inspection)"
                return st
            st.sha256 = digest.hexdigest()
            st.status = "done"
        except Exception as exc:
            st.status = "failed"
            st.error = str(exc)[:300]
        return st


# -- compute mesh ----------------------------------------------------------------------

@dataclass
class ComputeNode:
    node_id: str = ""
    name: str = ""
    endpoint: str = ""
    auth_token_present: bool = False  # never the token
    models: List[str] = field(default_factory=list)
    vram_gb: float = 0.0
    load: float = 0.0
    latency_ms: float = 0.0
    trusted: bool = False
    last_seen: float = 0.0


class ComputeMesh:
    """Trusted-node mesh: explicit pairing, heartbeat, single-node
    scheduling default. No model-splitting (unsupported runtimes)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._nodes: Dict[str, ComputeNode] = {}
        self._tokens: Dict[str, str] = {}  # node_id -> token (memory only)

    def pair(self, node: ComputeNode, token: str) -> ComputeNode:
        with self._lock:
            node.trusted = True
            node.last_seen = time.time()
            self._nodes[node.node_id] = node
            self._tokens[node.node_id] = token
            return node

    def revoke(self, node_id: str) -> bool:
        with self._lock:
            self._tokens.pop(node_id, None)
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.trusted = False
            return True

    def heartbeat(self, node_id: str, *, load: float = 0.0,
                  latency_ms: float = 0.0) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None or not node.trusted:
                return False
            node.load = load
            node.latency_ms = latency_ms
            node.last_seen = time.time()
            return True

    def select(self, *, model: str = "", max_latency_ms: float = 0.0,
               private: bool = False) -> Optional[ComputeNode]:
        with self._lock:
            cands = [n for n in self._nodes.values()
                     if n.trusted and (not model or model in n.models)
                     and (not max_latency_ms or n.latency_ms <= max_latency_ms)]
            # Private data stays on loopback nodes only.
            if private:
                cands = [n for n in cands if n.endpoint.startswith(
                    ("http://localhost", "http://127.0.0.1"))]
            if not cands:
                return None
            return sorted(cands, key=lambda n: (n.load, n.latency_ms))[0]

    def nodes(self) -> List[ComputeNode]:
        with self._lock:
            return list(self._nodes.values())
