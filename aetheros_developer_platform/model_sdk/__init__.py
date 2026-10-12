"""
Model SDK for AetherOS
======================

SDK for registering and managing AI model providers.

Supported model types:
    - LLM (Large Language Models)
    - Embedding Models
    - Image Models
    - Speech Models
    - Video Models

Usage::

    from aetheros_developer_platform.model_sdk import ModelManager

    manager = ModelManager()
    manager.register_llm_provider("my-provider", MyLLMProvider())
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Types of AI models."""
    LLM = "llm"
    EMBEDDING = "embedding"
    IMAGE = "image"
    SPEECH = "speech"
    VIDEO = "video"


@dataclass
class ModelInfo:
    """Information about an AI model."""
    id: str
    name: str
    model_type: ModelType
    provider: str
    description: str = ""
    max_tokens: int = 4096
    context_window: int = 4096
    pricing: Dict[str, float] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a completion."""
        ...

    @abstractmethod
    def stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "",
        **kwargs,
    ):
        """Stream a completion."""
        ...

    def list_models(self) -> List[ModelInfo]:
        """List available models."""
        return []


class BaseEmbeddingModel(ABC):
    """Base class for embedding models."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensions."""
        ...


class BaseModelImage(ABC):
    """Base class for image models."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        **kwargs,
    ) -> Any:
        """Generate an image."""
        ...


class BaseSpeechModel(ABC):
    """Base class for speech models."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        **kwargs,
    ) -> Any:
        """Synthesize speech."""
        ...

    @abstractmethod
    def transcribe(
        self,
        audio: Any,
        **kwargs,
    ) -> str:
        """Transcribe audio."""
        ...


class BaseVideoModel(ABC):
    """Base class for video models."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        **kwargs,
    ) -> Any:
        """Generate a video."""
        ...


class ModelManager:
    """Manages AI model providers for AetherOS.

    Usage::

        manager = ModelManager()
        manager.register_llm_provider("my-provider", MyLLMProvider())
        result = manager.complete("my-provider", [{"role": "user", "content": "Hello"}])
    """

    def __init__(self) -> None:
        self._llm_providers: Dict[str, BaseLLMProvider] = {}
        self._embedding_providers: Dict[str, BaseEmbeddingModel] = {}
        self._image_providers: Dict[str, BaseModelImage] = {}
        self._speech_providers: Dict[str, BaseSpeechModel] = {}
        self._video_providers: Dict[str, BaseVideoModel] = {}
        self._models: Dict[str, ModelInfo] = {}

    def register_llm_provider(
        self,
        name: str,
        provider: BaseLLMProvider,
    ) -> None:
        """Register an LLM provider."""
        self._llm_providers[name] = provider
        logger.info("Registered LLM provider: %s", name)

    def register_embedding_provider(
        self,
        name: str,
        provider: BaseEmbeddingModel,
    ) -> None:
        """Register an embedding model provider."""
        self._embedding_providers[name] = provider
        logger.info("Registered embedding provider: %s", name)

    def register_image_provider(
        self,
        name: str,
        provider: BaseModelImage,
    ) -> None:
        """Register an image model provider."""
        self._image_providers[name] = provider
        logger.info("Registered image provider: %s", name)

    def register_speech_provider(
        self,
        name: str,
        provider: BaseSpeechModel,
    ) -> None:
        """Register a speech model provider."""
        self._speech_providers[name] = provider
        logger.info("Registered speech provider: %s", name)

    def register_video_provider(
        self,
        name: str,
        provider: BaseVideoModel,
    ) -> None:
        """Register a video model provider."""
        self._video_providers[name] = provider
        logger.info("Registered video provider: %s", name)

    def register_model(self, model: ModelInfo) -> None:
        """Register a model info entry."""
        self._models[model.id] = model

    def complete(
        self,
        provider_name: str,
        messages: List[Dict[str, str]],
        model: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a completion using an LLM provider."""
        provider = self._llm_providers.get(provider_name)
        if not provider:
            raise ValueError(f"LLM provider '{provider_name}' not found")
        return provider.complete(messages, model=model, **kwargs)

    def embed(
        self,
        provider_name: str,
        texts: List[str],
    ) -> List[List[float]]:
        """Generate embeddings using an embedding provider."""
        provider = self._embedding_providers.get(provider_name)
        if not provider:
            raise ValueError(f"Embedding provider '{provider_name}' not found")
        return provider.embed(texts)

    def generate_image(
        self,
        provider_name: str,
        prompt: str,
        **kwargs,
    ) -> Any:
        """Generate an image using an image provider."""
        provider = self._image_providers.get(provider_name)
        if not provider:
            raise ValueError(f"Image provider '{provider_name}' not found")
        return provider.generate(prompt, **kwargs)

    def synthesize_speech(
        self,
        provider_name: str,
        text: str,
        **kwargs,
    ) -> Any:
        """Synthesize speech using a speech provider."""
        provider = self._speech_providers.get(provider_name)
        if not provider:
            raise ValueError(f"Speech provider '{provider_name}' not found")
        return provider.synthesize(text, **kwargs)

    def transcribe(
        self,
        provider_name: str,
        audio: Any,
        **kwargs,
    ) -> str:
        """Transcribe audio using a speech provider."""
        provider = self._speech_providers.get(provider_name)
        if not provider:
            raise ValueError(f"Speech provider '{provider_name}' not found")
        return provider.transcribe(audio, **kwargs)

    def generate_video(
        self,
        provider_name: str,
        prompt: str,
        **kwargs,
    ) -> Any:
        """Generate a video using a video provider."""
        provider = self._video_providers.get(provider_name)
        if not provider:
            raise ValueError(f"Video provider '{provider_name}' not found")
        return provider.generate(prompt, **kwargs)

    def list_providers(
        self,
        model_type: Optional[ModelType] = None,
    ) -> List[str]:
        """List all registered providers."""
        providers = []
        if model_type is None or model_type == ModelType.LLM:
            providers.extend(self._llm_providers.keys())
        if model_type is None or model_type == ModelType.EMBEDDING:
            providers.extend(self._embedding_providers.keys())
        if model_type is None or model_type == ModelType.IMAGE:
            providers.extend(self._image_providers.keys())
        if model_type is None or model_type == ModelType.SPEECH:
            providers.extend(self._speech_providers.keys())
        if model_type is None or model_type == ModelType.VIDEO:
            providers.extend(self._video_providers.keys())
        return providers

    def list_models(
        self,
        model_type: Optional[ModelType] = None,
    ) -> List[ModelInfo]:
        """List all registered models."""
        models = list(self._models.values())
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        return models

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get a model by ID."""
        return self._models.get(model_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get model manager statistics."""
        return {
            "llm_providers": len(self._llm_providers),
            "embedding_providers": len(self._embedding_providers),
            "image_providers": len(self._image_providers),
            "speech_providers": len(self._speech_providers),
            "video_providers": len(self._video_providers),
            "models": len(self._models),
        }


# Global model manager
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Return the global ModelManager singleton."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
