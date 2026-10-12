"""Stable Multimodal API (Phase 91 of Master Prompt 10).

Exposes the canonical ``media.*`` verbs:
    ingest, inspect, convert, transcribe, ocr, analyze, embed, search,
    stream, export

Each function is a thin, stable wrapper over the multimodal layer and the
production tools, returning plain dicts.  Existing Aetheros APIs are never
modified.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from agent.multimodal.input_router import MediaRouter, route_file, route_url
from agent.multimodal.media_abstraction import (
    MediaObject,
    SensitivityLevel,
    create_image_media,
    validate_media_object,
)
from agent.multimodal.memory import MultimodalMemoryStore, default_store
from agent.multimodal.perception import (
    analyze_image,
    analyze_video,
    extract_document,
    extract_video_frames,
    ocr_media,
    synthesize_speech,
    transcribe_audio,
)
from agent.multimodal.privacy_router import ProviderPrivacyRouter, default_privacy_router
from PIL import Image
from agent.multimodal.provenance import ConfidenceTracker, ProvenanceTracker

logger = logging.getLogger(__name__)


def _ok(**kwargs: Any) -> Dict[str, Any]:
    kwargs["success"] = True
    return kwargs


def _err(message: str) -> Dict[str, Any]:
    return {"success": False, "error": message}


def media_ingest(
    source: str,
    source_type: Optional[str] = None,
    sensitivity: str = "private",
    metadata: Optional[Dict[str, Any]] = None,
    router: Optional[MediaRouter] = None,
) -> Dict[str, Any]:
    """Normalize arbitrary input into a MediaObject."""
    router = router or MediaRouter()
    try:
        # Convert string source_type to InputSourceType enum if provided
        from agent.multimodal.input_router import InputSourceType
        if isinstance(source_type, str):
            try:
                source_type = InputSourceType(source_type)
            except ValueError:
                source_type = None  # let router auto-detect
        media = router.route_input(
            source,
            source_type=source_type,
            source=source,
            sensitivity=SensitivityLevel(sensitivity),
            metadata=metadata or {},
        )
    except Exception as e:
        return _err(f"ingest failed: {e}")
    return _ok(media=media.to_dict())


def media_inspect(
    media: MediaObject,
    privacy: Optional[ProviderPrivacyRouter] = None,
) -> Dict[str, Any]:
    """Return normalized metadata (Phase 6/32) + privacy classification."""
    errors = validate_media_object(media)
    if errors:
        return _err("; ".join(errors))
    decision = (privacy or default_privacy_router()).decide(media)
    return _ok(
        media_id=media.media_id,
        type=media.type.value,
        mime_type=media.mime_type,
        size=media.size,
        duration=media.duration,
        dimensions=media.dimensions,
        source=media.source,
        timestamp=media.timestamp,
        hash=media.hash,
        sensitivity=media.sensitivity.value,
        processing_target=decision.target.value,
        privacy_reason=decision.reason,
    )


def media_ocr(
    media: MediaObject,
    language: Optional[str] = None,
    trackers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return ocr_media(media, language=language, tracker=_pt(trackers), confidence=_ct(trackers))


def media_transcribe(
    media: MediaObject,
    trackers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return transcribe_audio(media, tracker=_pt(trackers), confidence=_ct(trackers))


def media_analyze(
    media: MediaObject,
    question: str = "",
    trackers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Route to the correct analyzer for the media modality."""
    from agent.multimodal.media_abstraction import MediaType

    if media.type == MediaType.VIDEO:
        return analyze_video(media, question, _pt(trackers), _ct(trackers))
    if media.type == MediaType.DOCUMENT:
        return extract_document(media, _pt(trackers), _ct(trackers))
    if media.type in (MediaType.IMAGE, MediaType.SCREEN, MediaType.CAMERA):
        return analyze_image(media, question or "Describe this image.", _pt(trackers), _ct(trackers))
    return _err(f"no analyzer for modality: {media.type.value}")


def media_convert(
    media: MediaObject,
    target_format: str = "png",
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert a media file to another format (image resize/format change)."""
    from agent.multimodal.media_abstraction import MediaType

    if media.type not in (MediaType.IMAGE, MediaType.SCREEN):
        return _err("convert currently supports image/screen inputs")
    try:
        with Image.open(media.source) as img:
            out = output_path or media.source.rsplit(".", 1)[0] + "." + target_format
            img.save(out, format=target_format.upper())
    except Exception as e:
        return _err(f"convert failed: {e}")
    return _ok(output_path=out, media=create_image_media(out).to_dict())


def media_embed(
    media: MediaObject,
    model: str = "text-embedding-3-small",
    store: Optional[MultimodalMemoryStore] = None,
) -> Dict[str, Any]:
    """Best-effort embedding + storage (Phase 55). Embedding is optional."""
    store = store or default_store()
    vector: Optional[List[float]] = None
    try:
        from agent.auxiliary_client import call_llm

        text = str(media.metadata.get("content", "")) or media.source
        resp = call_llm(
            task="embedding",
            messages=[{"role": "user", "content": text[:8000]}],
            model=model,
        )
        if isinstance(resp, dict):
            candidate = resp.get("embedding") or resp.get("data")
            if isinstance(candidate, list) and candidate and isinstance(candidate[0], (int, float)):
                vector = candidate
    except Exception as e:
        logger.debug("embedding unavailable, storing reference only: %s", e)
    entry_id = store.store_media(media, embedding=vector)
    return _ok(entry_id=entry_id, embedded=vector is not None)


def media_search(
    query: str,
    limit: int = 10,
    kinds: Optional[List[str]] = None,
    store: Optional[MultimodalMemoryStore] = None,
) -> Dict[str, Any]:
    """Retrieve across stored media references (Phase 56 RAG)."""
    store = store or default_store()
    results = store.search(query, limit=limit, kinds=kinds)
    return _ok(
        query=query,
        results=[r.to_dict() for r in results],
        count=len(results),
    )


def media_stream(
    source: str,
    kind: str = "audio",
    max_frames: int = 500,
) -> Dict[str, Any]:
    """Create a bounded stream via the stream manager (Phase 48)."""
    from agent.multimodal.stream_manager import MultimodalStreamManager

    mgr = MultimodalStreamManager(max_frames=max_frames)
    frame = mgr.push("default", kind, {"source": source})
    return _ok(stream="default", started=frame is not None, stats=mgr.stats())


def media_export(
    media: MediaObject,
    output_path: str,
    export_format: str = "json",
) -> Dict[str, Any]:
    """Export media metadata/analysis to JSON (Phase 87)."""
    payload = {
        "media": media.to_dict(),
        "analysis": media.metadata.get("analysis", ""),
    }
    try:
        if export_format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(payload["media"].get("source", ""))
    except Exception as e:
        return _err(f"export failed: {e}")
    return _ok(output_path=output_path, format=export_format)


def _pt(trackers: Optional[Dict[str, Any]]) -> Optional[ProvenanceTracker]:
    return trackers.get("provenance") if trackers else None


def _ct(trackers: Optional[Dict[str, Any]]) -> Optional[ConfidenceTracker]:
    return trackers.get("confidence") if trackers else None


def new_trackers() -> Dict[str, Any]:
    return {"provenance": ProvenanceTracker(), "confidence": ConfidenceTracker()}