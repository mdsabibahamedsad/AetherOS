"""Streaming Engine — universal streaming for OpenAI, Anthropic, Gemini, Groq, OpenRouter, Ollama, LM Studio.

Fast, cancelable, recoverable, auto-reconnect.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_runtime.streaming")


class StreamState(enum.Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    ERROR = "error"
    COMPLETED = "completed"
    RECOVERING = "recovering"


@dataclass
class StreamChunk:
    content: str = ""
    role: str = "assistant"
    finish_reason: Optional[str] = None
    token_count: int = 0
    tool_calls: Optional[List[Dict[str, Any]]] = None
    elapsed_ms: float = 0.0
    chunk_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamEvent:
    type: str
    chunk: Optional[StreamChunk] = None
    error: Optional[str] = None
    state: Optional[StreamState] = None
    timestamp: float = field(default_factory=time.time)


StreamCallback = Callable[[StreamEvent], None]


class StreamingEngine:
    """Universal streaming engine supporting all major providers.

    Features:
    - Provider-specific adapters (OpenAI, Anthropic, Gemini, Groq, OpenRouter, Ollama, LM Studio)
    - Cancelable mid-stream
    - Auto-reconnect on transient failures
    - Event-based callback system
    - Per-stream state tracking
    """

    PROVIDER_MAP: Dict[str, str] = {
        "openai": "https://api.openai.com/v1/chat/completions",
        "anthropic": "https://api.anthropic.com/v1/messages",
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        "groq": "https://api.groq.com/openai/v1/chat/completions",
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "mistral": "https://api.mistral.ai/v1/chat/completions",
        "together": "https://api.together.xyz/v1/chat/completions",
        "xai": "https://api.x.ai/v1/chat/completions",
        "ollama": "http://localhost:11434/api/chat",
        "lm_studio": "http://localhost:1234/v1/chat/completions",
        "google": "https://generativelanguage.googleapis.com/v1beta/models",
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._streams: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, List[StreamCallback]] = {}
        self._max_retries: int = 3
        self._reconnect_delay: float = 1.0

    # ------------------------------------------------------------------
    # Stream lifecycle
    # ------------------------------------------------------------------

    def start_stream(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, Any]],
        api_key: str = "",
        base_url: str = "",
        stream_id: Optional[str] = None,
        **params: Any,
    ) -> str:
        sid = stream_id or str(uuid.uuid4())
        with self._lock:
            self._streams[sid] = {
                "id": sid,
                "provider": provider,
                "model": model,
                "messages": messages,
                "api_key": api_key,
                "base_url": base_url or self.PROVIDER_MAP.get(provider, ""),
                "params": params,
                "state": StreamState.IDLE,
                "chunks": [],
                "full_content": "",
                "token_count": 0,
                "started_at": 0.0,
                "error": None,
                "cancel_requested": False,
            }
        return sid

    def get_stream(self, stream_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._streams.get(stream_id)

    def get_state(self, stream_id: str) -> Optional[StreamState]:
        with self._lock:
            s = self._streams.get(stream_id)
            return s["state"] if s else None

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, stream_id: str, callbacks: Optional[List[StreamCallback]] = None) -> str:
        if callbacks:
            with self._lock:
                self._callbacks.setdefault(stream_id, []).extend(callbacks)

        thread = threading.Thread(
            target=self._run_stream,
            args=(stream_id,),
            daemon=True,
            name=f"stream-{stream_id[:8]}",
        )
        thread.start()
        return stream_id

    def _run_stream(self, stream_id: str) -> None:
        with self._lock:
            stream = self._streams.get(stream_id)
            if not stream:
                return
            stream["state"] = StreamState.CONNECTING
            stream["started_at"] = time.time()

        self._emit(stream_id, StreamEvent(type="connecting", state=StreamState.CONNECTING))

        for attempt in range(self._max_retries + 1):
            if self._is_cancelled(stream_id):
                return

            try:
                self._do_stream(stream_id)
                with self._lock:
                    s = self._streams.get(stream_id)
                    if s:
                        s["state"] = StreamState.COMPLETED
                self._emit(stream_id, StreamEvent(type="completed", state=StreamState.COMPLETED))
                return

            except Exception as exc:
                logger.warning("Stream %s error (attempt %d/%d): %s", stream_id[:8], attempt + 1, self._max_retries, exc)
                if attempt < self._max_retries:
                    with self._lock:
                        s = self._streams.get(stream_id)
                        if s:
                            s["state"] = StreamState.RECOVERING
                    self._emit(stream_id, StreamEvent(type="recovering", error=str(exc), state=StreamState.RECOVERING))
                    time.sleep(self._reconnect_delay * (2 ** attempt))
                else:
                    with self._lock:
                        s = self._streams.get(stream_id)
                        if s:
                            s["state"] = StreamState.ERROR
                            s["error"] = str(exc)
                    self._emit(stream_id, StreamEvent(type="error", error=str(exc), state=StreamState.ERROR))

    def _do_stream(self, stream_id: str) -> None:
        with self._lock:
            stream = self._streams.get(stream_id)
            if not stream:
                return
            provider = stream["provider"]
            model = stream["model"]
            messages = stream["messages"]
            api_key = stream["api_key"]
            url = stream["base_url"]
            params = stream["params"]

        if not url:
            raise ValueError(f"No base URL for provider: {provider}")

        if provider == "anthropic":
            self._stream_anthropic(stream_id, url, model, messages, api_key, params)
        elif provider == "google":
            self._stream_google(stream_id, url, model, messages, api_key, params)
        elif provider == "ollama":
            self._stream_ollama(stream_id, url, model, messages, params)
        else:
            self._stream_openai_compat(stream_id, url, model, messages, api_key, params)

    # ------------------------------------------------------------------
    # Provider-specific streaming
    # ------------------------------------------------------------------

    def _stream_openai_compat(
        self, stream_id: str, url: str, model: str,
        messages: List[Dict[str, Any]], api_key: str, params: Dict[str, Any],
    ) -> None:
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for streaming")

        body = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": params.get("temperature", 0.7),
            "max_tokens": params.get("max_tokens", 4096),
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        with httpx.Client(timeout=None) as client:
            with client.stream("POST", url, json=body, headers=headers) as response:
                response.raise_for_status()
                chunk_index = 0
                full_content = ""

                for line in response.iter_lines():
                    if self._is_cancelled(stream_id):
                        return
                    if not line or line.startswith(":") or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        finish = data.get("choices", [{}])[0].get("finish_reason")

                        if content:
                            chunk = StreamChunk(
                                content=content,
                                finish_reason=finish,
                                chunk_index=chunk_index,
                            )
                            chunk_index += 1
                            full_content += content
                            self._store_chunk(stream_id, chunk)
                            self._emit(stream_id, StreamEvent(type="chunk", chunk=chunk))

                        if finish:
                            with self._lock:
                                s = self._streams.get(stream_id)
                                if s:
                                    s["full_content"] = full_content
                                    s["token_count"] = chunk_index
                            break

    def _stream_anthropic(
        self, stream_id: str, url: str, model: str,
        messages: List[Dict[str, Any]], api_key: str, params: Dict[str, Any],
    ) -> None:
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for streaming")

        system_msgs = [m for m in messages if m.get("role") == "system"]
        chat_msgs = [m for m in messages if m.get("role") != "system"]

        body = {
            "model": model,
            "messages": chat_msgs,
            "max_tokens": params.get("max_tokens", 4096),
            "stream": True,
        }
        if system_msgs:
            body["system"] = system_msgs[-1]["content"]

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        with httpx.Client(timeout=None) as client:
            with client.stream("POST", url, json=body, headers=headers) as response:
                response.raise_for_status()
                full_content = ""
                chunk_index = 0

                for line in response.iter_lines():
                    if self._is_cancelled(stream_id):
                        return
                    if not line or line.startswith("event:") or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            text = delta.get("text", "")
                            if text:
                                chunk = StreamChunk(content=text, chunk_index=chunk_index)
                                chunk_index += 1
                                full_content += text
                                self._store_chunk(stream_id, chunk)
                                self._emit(stream_id, StreamEvent(type="chunk", chunk=chunk))
                        elif data.get("type") == "message_delta":
                            finish = data.get("delta", {}).get("stop_reason")
                            if finish:
                                with self._lock:
                                    s = self._streams.get(stream_id)
                                    if s:
                                        s["full_content"] = full_content
                                        s["token_count"] = chunk_index

    def _stream_google(
        self, stream_id: str, url: str, model: str,
        messages: List[Dict[str, Any]], api_key: str, params: Dict[str, Any],
    ) -> None:
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for streaming")

        url = f"{url}/{model}:streamGenerateContent?alt=sse&key={api_key}"

        contents = []
        for msg in messages:
            role = "model" if msg.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

        body = {"contents": contents}

        headers = {"Content-Type": "application/json"}

        with httpx.Client(timeout=None) as client:
            with client.stream("POST", url, json=body, headers=headers) as response:
                response.raise_for_status()
                full_content = ""
                chunk_index = 0

                for line in response.iter_lines():
                    if self._is_cancelled(stream_id):
                        return
                    if not line or not line.startswith("data: "):
                        continue
                    data = json.loads(line[6:])
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text:
                            chunk = StreamChunk(content=text, chunk_index=chunk_index)
                            chunk_index += 1
                            full_content += text
                            self._store_chunk(stream_id, chunk)
                            self._emit(stream_id, StreamEvent(type="chunk", chunk=chunk))

        with self._lock:
            s = self._streams.get(stream_id)
            if s:
                s["full_content"] = full_content
                s["token_count"] = chunk_index

    def _stream_ollama(
        self, stream_id: str, url: str, model: str,
        messages: List[Dict[str, Any]], params: Dict[str, Any],
    ) -> None:
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for streaming")

        body = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        with httpx.Client(timeout=None) as client:
            with client.stream("POST", url, json=body) as response:
                response.raise_for_status()
                full_content = ""
                chunk_index = 0

                for line in response.iter_lines():
                    if self._is_cancelled(stream_id):
                        return
                    if not line:
                        continue
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    done = data.get("done", False)

                    if content:
                        chunk = StreamChunk(content=content, chunk_index=chunk_index)
                        chunk_index += 1
                        full_content += content
                        self._store_chunk(stream_id, chunk)
                        self._emit(stream_id, StreamEvent(type="chunk", chunk=chunk))

                    if done:
                        with self._lock:
                            s = self._streams.get(stream_id)
                            if s:
                                s["full_content"] = full_content
                                s["token_count"] = chunk_index
                        break

    # ------------------------------------------------------------------
    # Stream control
    # ------------------------------------------------------------------

    def cancel(self, stream_id: str) -> bool:
        with self._lock:
            stream = self._streams.get(stream_id)
            if not stream:
                return False
            stream["cancel_requested"] = True
            stream["state"] = StreamState.CANCELLED
        self._emit(stream_id, StreamEvent(type="cancelled", state=StreamState.CANCELLED))
        return True

    def cancel_all(self) -> int:
        count = 0
        terminal_states = {StreamState.CANCELLED, StreamState.COMPLETED, StreamState.ERROR}
        with self._lock:
            for sid in list(self._streams.keys()):
                s = self._streams.get(sid)
                if s and s["state"] not in terminal_states:
                    s["cancel_requested"] = True
                    s["state"] = StreamState.CANCELLED
                    count += 1
        return count

    def get_content(self, stream_id: str) -> str:
        with self._lock:
            s = self._streams.get(stream_id)
            return s["full_content"] if s else ""

    def get_active_streams(self) -> List[str]:
        with self._lock:
            return [
                sid for sid, s in self._streams.items()
                if s["state"] in (StreamState.STREAMING, StreamState.CONNECTING)
            ]

    def get_completed_streams(self) -> List[str]:
        with self._lock:
            return [sid for sid, s in self._streams.items() if s["state"] == StreamState.COMPLETED]

    def cleanup(self, max_age: float = 300.0) -> int:
        now = time.time()
        count = 0
        with self._lock:
            for sid in list(self._streams.keys()):
                s = self._streams.get(sid)
                if s and s["state"] == StreamState.COMPLETED:
                    if s.get("started_at", 0) and (now - s["started_at"]) > max_age:
                        del self._streams[sid]
                        self._callbacks.pop(sid, None)
                        count += 1
        return count

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_event(self, stream_id: str, callback: StreamCallback) -> None:
        with self._lock:
            self._callbacks.setdefault(stream_id, []).append(callback)

    def _emit(self, stream_id: str, event: StreamEvent) -> None:
        with self._lock:
            callbacks = list(self._callbacks.get(stream_id, []))
        for cb in callbacks:
            try:
                cb(event)
            except Exception:
                pass

    def _is_cancelled(self, stream_id: str) -> bool:
        with self._lock:
            s = self._streams.get(stream_id)
            return bool(s and s["cancel_requested"])

    def _store_chunk(self, stream_id: str, chunk: StreamChunk) -> None:
        with self._lock:
            s = self._streams.get(stream_id)
            if s:
                s["chunks"].append(chunk)
                s["full_content"] += chunk.content

    def summary(self) -> str:
        with self._lock:
            active = sum(1 for s in self._streams.values() if s["state"] == StreamState.STREAMING)
            completed = sum(1 for s in self._streams.values() if s["state"] == StreamState.COMPLETED)
            total = len(self._streams)
        return f"Streaming Engine: {active} active, {completed} completed, {total} total"