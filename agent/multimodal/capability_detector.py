"""Multimodal Capability Detection (Phase 3 of Master Prompt 10).

Determines, for every configured model/provider, which modalities it actually
supports: text, vision, audio input/output, video, document, OCR, structured
output, streaming, tool calling, computer use.

Authoritative source is the production model catalog
(``agent.models_dev.get_model_capabilities``).  A small manual override
registry lets operators pin capabilities for models the catalog doesn't cover.
The key invariant (MASTER 10 Phase 3): never send an unsupported modality to a
model.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from agent.multimodal.media_abstraction import MediaType

logger = logging.getLogger(__name__)


class CapabilityType(Enum):
    """Fine-grained capability flags a model/provider may expose."""

    TEXT = "text"
    VISION = "vision"                       # image understanding
    VISION_OCR = "vision_ocr"               # can read text inside images
    VISION_GROUND = "vision_ground"         # spatial grounding (bbox)
    AUDIO_INPUT = "audio_input"             # understands audio directly
    AUDIO_OUTPUT = "audio_output"           # can emit speech (realtime/TTS)
    AUDIO_TRANSCRIBE = "audio_transcribe"   # STT
    AUDIO_GENERATE = "audio_generate"       # TTS
    VIDEO_INPUT = "video_input"             # understands video frames
    VIDEO_GENERATE = "video_generate"
    DOCUMENT = "document"                   # structured document understanding
    OCR = "ocr"
    STRUCTURED_OUTPUT = "structured_output"
    STREAMING = "streaming"
    TOOL_CALLING = "tool_calling"
    COMPUTER_USE = "computer_use"
    REASONING = "reasoning"
    CHART_UNDERSTAND = "chart_understand"
    DIAGRAM_UNDERSTAND = "diagram_understand"
    TABLE_UNDERSTAND = "table_understand"
    MULTIMODAL_REASON = "multimodal_reason"
    MULTIMODAL_EMBED = "multimodal_embed"


class ProviderType(Enum):
    """Logical provider families the router understands."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    XAI = "xai"
    MISTRAL = "mistral"
    GROQ = "groq"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    LOCAL = "local"
    CUSTOM = "custom"

    @classmethod
    def from_id(cls, provider: str) -> "ProviderType":
        """Map a production provider id to a ProviderType (best effort)."""
        norm = (provider or "").lower()
        table = {
            "openai": cls.OPENAI, "openai-codex": cls.OPENAI,
            "anthropic": cls.ANTHROPIC,
            "gemini": cls.GOOGLE, "google": cls.GOOGLE,
            "xai": cls.XAI, "xai-oauth": cls.XAI,
            "mistral": cls.MISTRAL,
            "groq": cls.GROQ,
            "deepseek": cls.DEEPSEEK,
            "openrouter": cls.OPENROUTER,
            "ollama": cls.OLLAMA, "ollama-cloud": cls.OLLAMA,
        }
        return table.get(norm, cls.CUSTOM)


@dataclass
class ModelCapability:
    """Capability profile for a single model."""

    provider: str
    model: str
    capabilities: Set[CapabilityType] = field(default_factory=set)
    context_window: int = 200000
    max_output_tokens: int = 8192
    model_family: str = ""
    source: str = "catalog"  # catalog | override | heuristics

    def supports(self, cap: CapabilityType) -> bool:
        return cap in self.capabilities

    def supports_modality(self, media_type: MediaType) -> bool:
        if media_type == MediaType.TEXT:
            return True
        if media_type == MediaType.IMAGE:
            return self.supports(CapabilityType.VISION)
        if media_type == MediaType.AUDIO:
            return self.supports(CapabilityType.AUDIO_INPUT) or self.supports(CapabilityType.AUDIO_TRANSCRIBE)
        if media_type == MediaType.VIDEO:
            return self.supports(CapabilityType.VIDEO_INPUT)
        if media_type == MediaType.DOCUMENT:
            return self.supports(CapabilityType.DOCUMENT) or self.supports(CapabilityType.OCR)
        if media_type == MediaType.SCREEN:
            return self.supports(CapabilityType.VISION) or self.supports(CapabilityType.COMPUTER_USE)
        if media_type == MediaType.CAMERA:
            return self.supports(CapabilityType.VISION)
        if media_type == MediaType.STRUCTURED_DATA:
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "capabilities": sorted(c.value for c in self.capabilities),
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "model_family": self.model_family,
            "source": self.source,
        }


# ---------------------------------------------------------------------------
# Manual override registry — operators can pin capabilities for models the
# catalog misses (e.g. a local Ollama model, or a preview model).
# ---------------------------------------------------------------------------

_OVERRIDES: Dict[tuple, Set[CapabilityType]] = {
    ("ollama", "llava"): {CapabilityType.TEXT, CapabilityType.VISION, CapabilityType.VISION_OCR},
    ("ollama", "llava:13b"): {CapabilityType.TEXT, CapabilityType.VISION, CapabilityType.VISION_OCR},
    ("ollama", "bakllava"): {CapabilityType.TEXT, CapabilityType.VISION},
    ("ollama", "llama3.2-vision"): {CapabilityType.TEXT, CapabilityType.VISION},
    ("ollama", "qwen2.5vl"): {CapabilityType.TEXT, CapabilityType.VISION, CapabilityType.VISION_OCR},
}


def register_capability_override(
    provider: str, model: str, capabilities: Set[CapabilityType]
) -> None:
    """Pin explicit capabilities for a (provider, model) pair."""
    _OVERRIDES[(provider.lower(), model.lower())] = set(capabilities)


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


def _catalog_capabilities(provider: str, model: str) -> Optional[ModelCapability]:
    """Query the production models.dev catalog for a model's capabilities."""
    try:
        from agent.models_dev import get_model_capabilities
    except Exception as e:  # pragma: no cover - import path safety
        logger.debug("models_dev unavailable: %s", e)
        return None
    try:
        caps = get_model_capabilities(provider, model)
    except Exception as e:
        logger.debug("get_model_capabilities(%s, %s) failed: %s", provider, model, e)
        return None
    if caps is None:
        return None
    capabilities: Set[CapabilityType] = {CapabilityType.TEXT}
    if getattr(caps, "supports_tools", False):
        capabilities.add(CapabilityType.TOOL_CALLING)
    if getattr(caps, "supports_vision", False):
        capabilities.update(
            {CapabilityType.VISION, CapabilityType.VISION_OCR}
        )
    if getattr(caps, "supports_reasoning", False):
        capabilities.add(CapabilityType.REASONING)
    return ModelCapability(
        provider=provider,
        model=model,
        capabilities=capabilities,
        context_window=getattr(caps, "context_window", 200000),
        max_output_tokens=getattr(caps, "max_output_tokens", 8192),
        model_family=getattr(caps, "model_family", ""),
        source="catalog",
    )


def _heuristic_capabilities(provider: str, model: str) -> ModelCapability:
    """Best-effort capability inference when the catalog has no entry."""
    capabilities: Set[CapabilityType] = {CapabilityType.TEXT}
    ml = model.lower()
    # Vision-capable naming conventions (well-known families)
    vision_hints = (
        "vision", "-v", "vl", "4o", "opus", "sonnet", "gemini", "flash", "gpt-4",
        "claude-3", "qwen2.5-vl", "llava", "grok-2-vision", "grok-vision",
        "grok-3", "glm-4v", "internvl", "moondream",
    )
    if any(h in ml for h in vision_hints) and not ml.startswith(("text-", "tts", "whisper")):
        capabilities.update({CapabilityType.VISION, CapabilityType.VISION_OCR})
    if ml.startswith(("whisper", "gpt-4o-transcribe", "grok-stt", "stt")):
        capabilities.update({CapabilityType.AUDIO_TRANSCRIBE, CapabilityType.AUDIO_INPUT})
    if ml.startswith(("gpt-4o-mini-tts", "gpt-4o-tts", "eleven_", "voice", "tts")):
        capabilities.add(CapabilityType.AUDIO_OUTPUT)
    if any(h in ml for h in ("audio", "voice", "realtime")):
        capabilities.update({CapabilityType.AUDIO_INPUT, CapabilityType.AUDIO_OUTPUT})
    if ml.startswith(("gpt-4o", "gpt-4.1", "gpt-4.5", "claude-3-5", "claude-3-7", "claude-4", "gemini-2", "grok-4")):
        capabilities.update({CapabilityType.STREAMING, CapabilityType.STRUCTURED_OUTPUT})
    if any(h in ml for h in ("realtime", "computer-use", "computer_use", "cua")):
        capabilities.add(CapabilityType.COMPUTER_USE)
    return ModelCapability(
        provider=provider, model=model, capabilities=capabilities, source="heuristics"
    )


class CapabilityDetector:
    """Detect and cache per-model capability profiles (Phase 3)."""

    def __init__(self, provider_whitelist: Optional[List[str]] = None) -> None:
        self._cache: Dict[tuple, ModelCapability] = {}
        self._provider_whitelist = set(provider_whitelist or [])

    def detect(self, provider: str, model: str) -> ModelCapability:
        """Return the capability profile for (provider, model), cached."""
        key = (provider.lower(), model.lower())
        if key in self._cache:
            return self._cache[key]

        override = _OVERRIDES.get(key)
        if override is not None:
            profile = ModelCapability(
                provider=provider, model=model, capabilities=set(override), source="override"
            )
        else:
            catalog = _catalog_capabilities(provider, model)
            if catalog is not None:
                # Merge any operator override on top of catalog truth.
                if override:
                    catalog.capabilities.update(override)
                profile = catalog
            else:
                profile = _heuristic_capabilities(provider, model)

        self._cache[key] = profile
        return profile

    def supports(self, provider: str, model: str, cap: CapabilityType) -> bool:
        return self.detect(provider, model).supports(cap)

    def find_capable_model(
        self,
        providers: List[str],
        models: List[str],
        required: CapabilityType,
    ) -> Optional[ModelCapability]:
        """Return the first (provider, model) pair that supports ``required``."""
        for provider in providers:
            for model in models:
                if self._provider_whitelist and provider not in self._provider_whitelist:
                    continue
                profile = self.detect(provider, model)
                if profile.supports(required):
                    return profile
        return None

    def route_modality(
        self, providers: List[str], models: List[str], media_type: MediaType
    ) -> Optional[ModelCapability]:
        """Phase 4 primitive: pick a model that can handle ``media_type``."""
        modality_map = {
            MediaType.TEXT: CapabilityType.TEXT,
            MediaType.IMAGE: CapabilityType.VISION,
            MediaType.AUDIO: CapabilityType.AUDIO_INPUT,
            MediaType.VIDEO: CapabilityType.VIDEO_INPUT,
            MediaType.DOCUMENT: CapabilityType.DOCUMENT,
            MediaType.SCREEN: CapabilityType.VISION,
            MediaType.CAMERA: CapabilityType.VISION,
            MediaType.STRUCTURED_DATA: CapabilityType.TEXT,
        }
        cap = modality_map.get(media_type)
        if cap is None:
            return None
        return self.find_capable_model(providers, models, cap)

    def clear_cache(self) -> None:
        self._cache.clear()