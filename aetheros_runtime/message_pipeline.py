"""Message Pipeline — user message through pre-processing, memory, context, reasoning, provider, streaming, tools, post-processing, storage.

The full message lifecycle in one pipeline.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aetheros_runtime.pipeline")


class PipelineStage(enum.Enum):
    PRE_PROCESSING = "pre_processing"
    MEMORY_LOOKUP = "memory_lookup"
    CONTEXT_BUILDING = "context_building"
    REASONING = "reasoning"
    PROVIDER_CALL = "provider_call"
    STREAMING = "streaming"
    TOOL_CALLING = "tool_calling"
    POST_PROCESSING = "post_processing"
    CONVERSATION_STORAGE = "conversation_storage"


@dataclass
class MessageContext:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_message: str = ""
    processed_message: str = ""
    system_prompt: str = ""
    memory_context: str = ""
    full_context: str = ""
    provider: str = ""
    model: str = ""
    response: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    streaming: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    latency_ms: float = 0.0

    @property
    def elapsed(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return (time.time() - self.started_at) * 1000


StageHandler = Callable[[MessageContext], MessageContext]


class MessagePipeline:
    """Orchestrates the full message lifecycle through every stage.

    User Message → Pre-processing → Memory Lookup → Context Building →
    Reasoning → Provider → Streaming → Tool Calling → Post-processing → Storage

    Each stage is an independent handler that can be overridden or extended.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._handlers: Dict[PipelineStage, List[StageHandler]] = {}
        self._history: List[MessageContext] = []
        self._max_history: int = 100
        self._hook_fns: Dict[str, List[Callable]] = {}

        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        self._default_handlers: Dict[PipelineStage, StageHandler] = {
            PipelineStage.PRE_PROCESSING: self._default_pre_process,
            PipelineStage.MEMORY_LOOKUP: self._default_memory_lookup,
            PipelineStage.CONTEXT_BUILDING: self._default_context_building,
            PipelineStage.REASONING: self._default_reasoning,
            PipelineStage.POST_PROCESSING: self._default_post_process,
            PipelineStage.CONVERSATION_STORAGE: self._default_store,
        }
        for stage, handler in self._default_handlers.items():
            self.register_handler(stage, handler)

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handler(self, stage: PipelineStage, handler: StageHandler) -> None:
        with self._lock:
            self._handlers.setdefault(stage, []).append(handler)

    def clear_handlers(self, stage: Optional[PipelineStage] = None) -> None:
        with self._lock:
            if stage:
                self._handlers[stage] = []
            else:
                self._handlers.clear()
            self._restore_default_handlers(stage)

    def _restore_default_handlers(self, stage: Optional[PipelineStage] = None) -> None:
        """Re-register built-in default handlers after a clear so the pipeline
        keeps functioning (custom handlers are dropped, defaults stay)."""
        defaults = getattr(self, "_default_handlers", {})
        if stage is not None:
            handler = defaults.get(stage)
            if handler:
                self._handlers[stage].append(handler)
        else:
            for stage_key, handler in defaults.items():
                self._handlers.setdefault(stage_key, []).append(handler)

    def register_hook(self, name: str, fn: Callable) -> None:
        with self._lock:
            self._hook_fns.setdefault(name, []).append(fn)

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------

    def run(
        self,
        user_message: str,
        provider: str = "",
        model: str = "",
        system_prompt: str = "",
        streaming: bool = True,
        **kw: Any,
    ) -> MessageContext:
        ctx = MessageContext(
            user_message=user_message,
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            streaming=streaming,
            metadata=kw,
        )

        self._run_hooks("pipeline_start", ctx)

        stages = [
            PipelineStage.PRE_PROCESSING,
            PipelineStage.MEMORY_LOOKUP,
            PipelineStage.CONTEXT_BUILDING,
            PipelineStage.REASONING,
            PipelineStage.PROVIDER_CALL,
            PipelineStage.STREAMING,
            PipelineStage.TOOL_CALLING,
            PipelineStage.POST_PROCESSING,
            PipelineStage.CONVERSATION_STORAGE,
        ]

        for stage in stages:
            if self._is_stage_skipped(stage, ctx):
                continue
            ctx = self._execute_stage(stage, ctx)
            if ctx.error:
                logger.error("Pipeline failed at %s: %s", stage.value, ctx.error)
                break

        ctx.completed_at = time.time()
        ctx.latency_ms = (ctx.completed_at - ctx.started_at) * 1000

        with self._lock:
            self._history.append(ctx)
            if len(self._history) > self._max_history:
                self._history.pop(0)

        self._run_hooks("pipeline_complete", ctx)
        return ctx

    def _execute_stage(self, stage: PipelineStage, ctx: MessageContext) -> MessageContext:
        with self._lock:
            handlers = list(self._handlers.get(stage, []))

        for handler in handlers:
            try:
                ctx = handler(ctx)
            except Exception as exc:
                ctx.error = f"{stage.value}: {exc}"
                logger.exception("Stage %s handler failed", stage.value)
                break

        return ctx

    @staticmethod
    def _is_stage_skipped(stage: PipelineStage, ctx: MessageContext) -> bool:
        if stage in (PipelineStage.PROVIDER_CALL, PipelineStage.STREAMING):
            return not ctx.provider
        if stage == PipelineStage.TOOL_CALLING:
            return not ctx.tool_calls
        return False

    # ------------------------------------------------------------------
    # Default handlers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_pre_process(ctx: MessageContext) -> MessageContext:
        ctx.processed_message = ctx.user_message.strip()
        if not ctx.processed_message:
            ctx.error = "Empty message after pre-processing"
        return ctx

    @staticmethod
    def _default_memory_lookup(ctx: MessageContext) -> MessageContext:
        ctx.memory_context = "[Memory context would be loaded here]"
        return ctx

    @staticmethod
    def _default_context_building(ctx: MessageContext) -> MessageContext:
        parts = []
        if ctx.system_prompt:
            parts.append(ctx.system_prompt)
        if ctx.memory_context:
            parts.append(ctx.memory_context)
        parts.append(ctx.processed_message or ctx.user_message)
        ctx.full_context = "\n\n".join(parts)
        return ctx

    @staticmethod
    def _default_reasoning(ctx: MessageContext) -> MessageContext:
        return ctx

    @staticmethod
    def _default_post_process(ctx: MessageContext) -> MessageContext:
        return ctx

    @staticmethod
    def _default_store(ctx: MessageContext) -> MessageContext:
        return ctx

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def _run_hooks(self, name: str, ctx: MessageContext) -> None:
        with self._lock:
            fns = list(self._hook_fns.get(name, []))
        for fn in fns:
            try:
                fn(ctx)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, limit: int = 10) -> List[MessageContext]:
        with self._lock:
            return list(self._history[-limit:])

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    def get_recent_contexts(self, count: int = 5) -> List[MessageContext]:
        with self._lock:
            return list(self._history[-count:])

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_max_history(self, count: int) -> None:
        with self._lock:
            self._max_history = count

    def summary(self) -> str:
        with self._lock:
            total = len(self._history)
            errors = sum(1 for h in self._history if h.error)
        return f"Message Pipeline: {total} messages processed, {errors} errors"