"""Cache-safe context assembly for the memory fabric.

Assembles retrieved memory into a context block for prompt injection.  The
KEY cache-safety property: this block is produced per-turn and injected at
API-call time (mirroring conversation_loop's ephemeral prefetch injection) —
it is NEVER baked into the system prompt or persisted mid-conversation, so
per-conversation prompt caching is preserved.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from aetheros_memory_intelligence.grounding import CONTEXT_FRAME, GroundingEngine
from aetheros_memory_intelligence.retrieval import RetrievedMemory


@dataclass
class AssembledContext:
    text: str = ""
    memory_ids: List[str] = field(default_factory=list)
    used_tokens: int = 0
    budget_tokens: int = 0
    truncated: bool = False
    dropped: int = 0

def to_dict(self) -> dict:
    return {
        "text": self.text,
        "memory_ids": self.memory_ids,
        "used_tokens": self.used_tokens,
        "budget_tokens": self.budget_tokens,
        "truncated": self.truncated,
        "dropped": self.dropped,
    }


def estimate_tokens(text: str) -> int:
    """Rough token estimate (chars/4).  Good enough for budgeting."""
    return max(0, int(len(text) / 4))


class ContextAssembler:
    """Packs grounded memories into a budgeted, framed context block.

    Priority order: higher confidence/trust first, then higher score.
    The budget is the master constraint; entries are dropped (not truncated
    mid-entry) so the frame + citations always fit.
    """

    def __init__(
        self,
        *,
        budget_tokens: int = 2400,
        grounding: Optional[GroundingEngine] = None,
        frame: str = CONTEXT_FRAME,
    ) -> None:
        self.budget_tokens = budget_tokens
        self._grounding = grounding or GroundingEngine()
        self.frame = frame

    def assemble(self, memories: List[RetrievedMemory]) -> AssembledContext:
        grounded = self._grounding.ground(memories)
        reserved = estimate_tokens(self.frame) + 20  # citations etc.
        budget = self.budget_tokens - reserved
        if budget <= 0:
            return AssembledContext(
                text=self.frame, memory_ids=[], used_tokens=0,
                budget_tokens=self.budget_tokens, truncated=True, dropped=len(memories),
            )

        # Sort by confidence desc (primary), score desc (secondary).
        ordered = sorted(
            memories,
            key=lambda rm: (rm.confidence, rm.score),
            reverse=True,
        )
        used = 0
        used_ids: List[str] = []
        dropped = 0
        for rm in ordered:
            tokens = estimate_tokens(rm.text)
            if used + tokens > budget:
                dropped += 1
                continue
            used += tokens
            used_ids.append(rm.id)

        selected = [rm for rm in memories if rm.id in used_ids]
        text_parts = [self.frame]
        for rm in selected:
            text_parts.append(rm.text)
        body = "\n".join(text_parts)

        return AssembledContext(
            text=body,
            memory_ids=used_ids,
            used_tokens=used,
            budget_tokens=self.budget_tokens,
            truncated=dropped > 0,
            dropped=dropped,
        )