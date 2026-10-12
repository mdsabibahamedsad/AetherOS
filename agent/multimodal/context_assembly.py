"""Multi-Modal Context Assembly (Phase 22 of Master Prompt 10).

Assembles multimodal context for agent consumption with:
- Token budget management across modalities
- Grounding and citation injection
- Modality-aware context windowing
- Cross-modal reference resolution
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.multimodal.media_abstraction import MediaObject, MediaType
from agent.multimodal.provenance import ProvenanceTracker

logger = logging.getLogger(__name__)


@dataclass
class ContextSegment:
    """A segment of multimodal context."""

    content: str
    modality: str
    media_id: str
    token_estimate: int
    provenance: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextWindow:
    """A window of multimodal context within token budget."""

    segments: List[ContextSegment]
    total_tokens: int
    budget: int
    overflow: bool = False
    overflow_tokens: int = 0


class MultimodalContextAssembler:
    """Assembles multimodal context for agent consumption (Phase 22)."""

    def __init__(
        self,
        max_tokens: int = 8000,
        reserve_tokens: int = 1000,
        tracker: Optional["ProvenanceTracker"] = None,
    ):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.budget = max_tokens - reserve_tokens
        self.tracker = tracker
        self._segments: List = []

    def add_text(self, text: str, media_id: str, provenance: Optional[Dict] = None) -> None:
        """Add text segment to context."""
        tokens = self._estimate_tokens(text)
        self._segments.append({
            "content": text,
            "modality": "text",
            "media_id": media_id,
            "token_estimate": tokens,
            "provenance": provenance,
            "metadata": {},
        })

    def add_media_analysis(
        self,
        media: "MediaObject",
        analysis: str,
        provenance: Optional[Dict] = None,
    ) -> None:
        """Add media analysis result to context."""
        tokens = self._estimate_tokens(analysis)
        self._segments.append({
            "content": f"[{media.type.value.upper()} ANALYSIS]: {analysis}",
            "modality": media.type.value,
            "media_id": media.media_id,
            "token_estimate": tokens,
            "provenance": provenance,
            "metadata": {"source": media.source, "mime_type": media.mime_type},
        })

    def add_structured_data(
        self,
        data: Dict,
        media_id: str,
        provenance: Optional[Dict] = None,
    ) -> None:
        """Add structured data as JSON to context."""
        import json
        text = json.dumps(data, indent=2)
        tokens = self._estimate_tokens(text)
        self._segments.append({
            "content": f"[STRUCTURED DATA]: {text}",
            "modality": "structured_data",
            "media_id": media_id,
            "token_estimate": tokens,
            "provenance": provenance,
            "metadata": {},
        })

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (~4 chars per token)."""
        return max(1, len(text) // 4)

    def build(self, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Build the final context window within budget."""
        budget = max_tokens or self.budget
        total = 0
        selected = []
        overflow = False
        overflow_tokens = 0

        # Sort by modality priority: text > structured > image > audio > video
        priority = {"text": 0, "structured_data": 1, "image": 2, "screen": 3, "camera": 3, "document": 3, "audio": 4, "video": 5}
        sorted_segments = sorted(self._segments, key=lambda s: priority.get(s["modality"], 99))

        for seg in sorted_segments:
            if total + seg["token_estimate"] <= budget:
                selected.append(seg)
                total += seg["token_estimate"]
            else:
                overflow = True
                overflow_tokens += seg["token_estimate"]
                # Could truncate here, but for now we skip

        context_text = "\n\n---\n\n".join(seg["content"] for seg in selected)

        result = {
            "context": context_text,
            "segments": selected,
            "total_tokens": total,
            "budget": budget,
            "overflow": overflow,
            "overflow_tokens": overflow_tokens,
            "modality_counts": self._count_modalities(selected),
        }

        return result

    def _count_modalities(self, segments: List) -> Dict[str, int]:
        counts = {}
        for s in segments:
            counts[s["modality"]] = counts.get(s["modality"], 0) + 1
        return counts

    def clear(self) -> None:
        """Clear all segments."""
        self._segments = []


def assemble_multimodal_context(
    *medias: "MediaObject",
    analyses: Optional[Dict[str, str]] = None,
    texts: Optional[List[str]] = None,
    max_tokens: int = 8000,
    tracker=None,
) -> Dict[str, Any]:
    """Convenience function to assemble multimodal context."""
    assembler = MultimodalContextAssembler(max_tokens=max_tokens)

    for media in medias:
        if media.type.value in analyses:
            assembler.add_media_analysis(media, analyses[media.media_id])
        elif media.type.value in ("text", "structured_data"):
            content = media.metadata.get("data", "") or media.metadata.get("content", "")
            if content:
                assembler.add_text(str(content), media.media_id)

    if texts:
        for i, t in enumerate(texts):
            assembler.add_text(t, f"text_{i}")

    return assembler.build(max_tokens=max_tokens)