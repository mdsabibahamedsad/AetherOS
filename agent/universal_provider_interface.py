"""
Universal Provider Interface for Aetheros

This module defines the abstract base class that all provider adapters must implement
to provide a consistent interface for the Aetheros model intelligence layer.
"""

import abc
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass


@dataclass
class ModelInfo:
    """Standardized model information across all providers."""
    id: str
    provider_id: str
    display_name: str
    canonical_id: Optional[str] = None
    family: Optional[str] = None
    version: Optional[str] = None
    context_window: int = 0
    input_modalities: List[str] = None
    output_modalities: List[str] = None
    reasoning_support: bool = False
    tool_support: bool = False
    structured_output_support: bool = False
    vision_support: bool = False
    audio_support: bool = False
    embedding_support: bool = False
    image_support: bool = False
    availability: str = "unknown"  # unknown, available, unavailable, deprecated
    status: str = ""  # e.g., "active", "deprecated", "preview"
    pricing_metadata: Dict[str, Any] = None
    limits: Dict[str, Any] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.input_modalities is None:
            self.input_modalities = []
        if self.output_modalities is None:
            self.output_modalities = []
        if self.pricing_metadata is None:
            self.pricing_metadata = {}
        if self.limits is None:
            self.limits = {}


@dataclass
class ChatRequest:
    """Standardized chat request format."""
    messages: List[Dict[str, Any]]
    model: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None
    reasoning_effort: Optional[str] = None  # e.g., "low", "medium", "high"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ChatResponse:
    """Standardized chat response format."""
    id: str
    model: str
    provider: str
    created: int
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProviderCapabilities:
    """Standardized provider capabilities."""
    supports_chat: bool = True
    supports_streaming: bool = False
    supports_tool_calls: bool = False
    supports_structured_output: bool = False
    supports_vision: bool = False
    supports_audio: bool = False
    supports_embeddings: bool = False
    supports_reasoning: bool = False
    max_models_returned: Optional[int] = None


class UniversalProviderInterface(abc.ABC):
    """
    Abstract base class that defines the universal provider interface.
    
    All provider adapters in Aetheros must implement this interface to ensure
    consistent behavior across different AI providers.
    """

    def __init__(self, provider_id: str, display_name: str):
        self.provider_id = provider_id
        self.display_name = display_name
        self._capabilities = ProviderCapabilities()
        self._status = "unknown"  # unknown, healthy, degraded, unhealthy
        self._last_health_check = 0.0

    @abc.abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with the provider using provided credentials.
        
        Args:
            credentials: Dictionary containing authentication information
                        (api_key, oauth_token, etc.)
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        pass

    @abc.abstractmethod
    def validate_credentials(self) -> Tuple[bool, Optional[str]]:
        """
        Validate that the current credentials are valid and functional.
        
        Returns:
            Tuple of (is_valid, error_message)
            If is_valid is True, error_message should be None
            If is_valid is False, error_message should describe the issue
        """
        pass

    @abc.abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """
        Retrieve the list of available models from the provider.
        
        Returns:
            List of ModelInfo objects representing available models
        """
        pass

    @abc.abstractmethod
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get detailed information about a specific model.
        
        Args:
            model_id: The identifier of the model to retrieve
            
        Returns:
            ModelInfo object if found, None otherwise
        """
        pass

    @abc.abstractmethod
    def health_check(self) -> Tuple[str, float]:
        """
        Perform a health check on the provider.
        
        Returns:
            Tuple of (status, response_time_ms)
            status: "healthy", "degraded", "unhealthy", "unknown"
            response_time_ms: Response time in milliseconds
        """
        pass

    @abc.abstractmethod
    def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Send a chat completion request to the provider.
        
        Args:
            request: Standardized chat request
            
        Returns:
            Standardized chat response
        """
        pass

    @abc.abstractmethod
    def stream(self, request: ChatRequest):
        """
        Send a streaming chat completion request to the provider.
        
        Args:
            request: Standardized chat request
            
        Yields:
            Standardized chat response chunks
        """
        pass

    @abc.abstractmethod
    def tool_call(self, request: ChatRequest) -> ChatResponse:
        """
        Execute a tool call request (for providers that support native tool use).
        
        Args:
            request: Standardized chat request with tools
            
        Returns:
            Standardized chat response
        """
        pass

    @abc.abstractmethod
    def structured_output(self, request: ChatRequest) -> ChatResponse:
        """
        Request structured output from the provider.
        
        Args:
            request: Standardized chat request with response_format
            
        Returns:
            Standardized chat response with structured output
        """
        pass

    @abc.abstractmethod
    def vision(self, request: ChatRequest) -> ChatResponse:
        """
        Process a vision/image input request.
        
        Args:
            request: Standardized chat request with image content
            
        Returns:
            Standardized chat response
        """
        pass

    @abc.abstractmethod
    def audio(self, request: ChatRequest) -> ChatResponse:
        """
        Process an audio input/request.
        
        Args:
            request: Standardized chat request with audio content
            
        Returns:
            Standardized chat response
        """
        pass

    @abc.abstractmethod
    def embeddings(self, request: ChatRequest) -> ChatResponse:
        """
        Generate embeddings for input text.
        
        Args:
            request: Standardized chat request
            
        Returns:
            Standardized chat response with embeddings
        """
        pass

    def get_capabilities(self) -> ProviderCapabilities:
        """Get the provider's capabilities."""
        return self._capabilities

    def get_status(self) -> str:
        """Get the current health status of the provider."""
        return self._status

    def update_health_status(self, status: str, response_time_ms: float):
        """Update the provider's health status."""
        self._status = status
        self._last_health_check = response_time_ms

    def normalize_model_id(self, model_id: str) -> str:
        """
        Normalize a model ID to a standard format.
        
        Args:
            model_id: Raw model ID from provider or user
            
        Returns:
            Normalized model ID
        """
        # Default implementation - providers can override if needed
        return model_id.strip().lower()

    def denormalize_model_id(self, normalized_id: str) -> str:
        """
        Convert a normalized model ID back to provider-specific format.
        
        Args:
            normalized_id: Normalized model ID
            
        Returns:
            Provider-specific model ID
        """
        # Default implementation - providers can override if needed
        return normalized_id