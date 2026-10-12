"""
Anthropic Provider Implementation using the Universal Provider Interface

This demonstrates how existing providers can be adapted to implement the
universal provider interface while maintaining backward compatibility.
"""

import anthropic
from typing import Any, Dict, List, Optional, Tuple
from universal_provider_interface import UniversalProviderInterface, ModelInfo, ChatRequest, ChatResponse, ProviderCapabilities
from model_metadata import get_model_context_length


class AnthropicProvider(UniversalProviderInterface):
    """
    Anthropic provider implementation that adheres to the universal provider interface.
    
    This wrapper maintains backward compatibility with existing Anthropic adapter
    functions while providing the standardized interface required by the model
    intelligence layer.
    """

    def __init__(self):
        super().__init__("anthropic", "Anthropic")
        self._client = None
        self._api_key = None
        self._base_url = None
        
        # Set Anthropic-specific capabilities
        self._capabilities = ProviderCapabilities(
            supports_chat=True,
            supports_streaming=True,
            supports_tool_calls=True,
            supports_structured_output=False,  # Anthropic doesn't have native structured output
            supports_vision=True,
            supports_audio=False,
            supports_embeddings=False,
            supports_reasoning=True,
            max_models_returned=None
        )

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with Anthropic using API key.
        
        Args:
            credentials: Dictionary containing 'api_key' and optionally 'base_url'
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            self._api_key = credentials.get('api_key')
            self._base_url = credentials.get('base_url')
            
            if not self._api_key:
                return False
                
            # Build the Anthropic client (reusing existing logic)
            from anthropic_adapter import build_anthropic_client
            self._client = build_anthropic_client(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=30.0  # Default timeout for auth test
            )
            
            return True
        except Exception:
            self._client = None
            return False

    def validate_credentials(self) -> Tuple[bool, Optional[str]]:
        """
        Validate Anthropic credentials by attempting a simple API call.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self._client:
            return False, "No client initialized - authenticate() must be called first"
            
        try:
            # Attempt a minimal API call to validate credentials
            # Using a simple message to test connectivity
            message = self._client.messages.create(
                model="claude-3-haiku-20240307",  # Use a lightweight model for testing
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            return True, None
        except anthropic.AuthenticationError as e:
            return False, f"Authentication failed: {str(e)}"
        except anthropic.PermissionDeniedError as e:
            return False, f"Permission denied: {str(e)}"
        except Exception as e:
            return False, f"Validation failed: {str(e)}"

    def list_models(self) -> List[ModelInfo]:
        """
        Retrieve available Anthropic models.
        
        Note: Anthropic doesn't provide a models endpoint, so we return
        a curated list of known models with metadata from model_metadata.
        
        Returns:
            List of ModelInfo objects
        """
        # For now, return a basic list - in practice this would integrate
        # with model_metadata or models.dev to get comprehensive model info
        known_models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", 
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ]
        
        models = []
        for model_id in known_models:
            try:
                context_length = get_model_context_length(
                    model=model_id,
                    base_url=self._base_url or "",
                    api_key=self._api_key or ""
                )
                
                model_info = ModelInfo(
                    id=model_id,
                    provider_id=self.provider_id,
                    display_name=model_id.replace("-", " ").title(),
                    context_window=context_length or 200000,
                    reasoning_support=True,
                    tool_support=True,
                    vision_support=True,
                    availability="available"
                )
                models.append(model_info)
            except Exception:
                # Skip models we can't get info for
                continue
                
        return models

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get detailed information about a specific Anthropic model.
        
        Args:
            model_id: The identifier of the model to retrieve
            
        Returns:
            ModelInfo object if found, None otherwise
        """
        normalized_id = self.normalize_model_id(model_id)
        models = self.list_models()
        for model in models:
            if self.normalize_model_id(model.id) == normalized_id:
                return model
        return None

    def health_check(self) -> Tuple[str, float]:
        """
        Perform a health check on the Anthropic provider.
        
        Returns:
            Tuple of (status, response_time_ms)
        """
        import time
        start_time = time.time()
        
        if not self._client:
            status = "unknown"
            response_time = 0.0
        else:
            try:
                # Simple test to check connectivity
                self._client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1,
                    messages=[{"role": "user", "content": "test"}]
                )
                status = "healthy"
            except anthropic.RateLimitError:
                status = "degraded"  # Rate limited but service is healthy
            except anthropic.AuthenticationError:
                status = "unhealthy"  # Auth issues
            except Exception:
                status = "unhealthy"  # Other errors
                
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        return status, response_time

    def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Send a chat completion request to Anthropic.
        
        Args:
            request: Standardized chat request
            
        Returns:
            Standardized chat response
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Call authenticate() first.")
            
        # Convert standardized request to Anthropic format
        anthropic_messages = []
        for msg in request.messages:
            anthropic_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Prepare Anthropic-specific parameters
        params = {
            "model": request.model,
            "max_tokens": request.max_tokens or 4096,
            "messages": anthropic_messages,
        }
        
        if request.temperature is not None:
            params["temperature"] = request.temperature
        if request.top_p is not None:
            params["top_p"] = request.top_p
        if request.stream:
            params["stream"] = request.stream
            
        # Handle thinking/reasoning parameters for supported models
        if request.reasoning_effort:
            # Map reasoning effort to Anthropic's thinking parameters
            # This would need to be implemented based on Anthropic's specific format
            pass
            
        # Make the API call
        response = self._client.messages.create(**params)
        
        # Convert Anthropic response to standardized format
        return ChatResponse(
            id=response.id,
            model=response.model,
            provider=self.provider_id,
            created=response.created_timestamp,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.content[0].text if response.content else ""
                },
                "finish_reason": response.stop_reason
            }],
            usage={
                "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                "completion_tokens": response.usage.output_tokens if response.usage else 0,
                "total_tokens": (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0
            }
        )

    def stream(self, request: ChatRequest):
        """
        Send a streaming chat completion request to Anthropic.
        
        Args:
            request: Standardized chat request
            
        Yields:
            Standardized chat response chunks
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Call authenticate() first.")
            
        # Convert standardized request to Anthropic format
        anthropic_messages = []
        for msg in request.messages:
            anthropic_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Prepare Anthropic-specific parameters
        params = {
            "model": request.model,
            "max_tokens": request.max_tokens or 4096,
            "messages": anthropic_messages,
            "stream": True
        }
        
        if request.temperature is not None:
            params["temperature"] = request.temperature
        if request.top_p is not None:
            params["top_p"] = request.top_p
            
        # Make the streaming API call
        stream = self._client.messages.stream(**params)
        
        # Yield standardized response chunks
        for chunk in stream:
            # Convert Anthropic stream chunk to standardized format
            # This is a simplified implementation - real implementation would
            # need to handle different chunk types properly
            if hasattr(chunk, 'delta') and chunk.delta:
                yield ChatResponse(
                    id=getattr(chunk, 'id', ''),
                    model=getattr(chunk, 'model', request.model),
                    provider=self.provider_id,
                    created=int(getattr(chunk, 'timestamp', 0)),
                    choices=[{
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": getattr(chunk.delta, 'text', '')
                        }
                    }]
                )

    def tool_call(self, request: ChatRequest) -> ChatResponse:
        """
        Execute a tool call request via Anthropic's tool use capability.
        
        Args:
            request: Standardized chat request with tools
            
        Returns:
            Standardized chat response
        """
        # Anthropic tool calls are handled through the regular chat interface
        # when tools are provided in the request
        return self.chat(request)

    def structured_output(self, request: ChatRequest) -> ChatResponse:
        """
        Request structured output from Anthropic.
        
        Note: Anthropic doesn't have native structured output support,
        so this would need to be implemented via prompting or not supported.
        
        Args:
            request: Standardized chat request with response_format
            
        Returns:
            Standardized chat response
        """
        # For now, fall back to regular chat - in a full implementation,
        # this would either use prompting techniques or raise NotImplementedError
        return self.chat(request)

    def vision(self, request: ChatRequest) -> ChatResponse:
        """
        Process a vision/image input request via Anthropic's vision capability.
        
        Args:
            request: Standardized chat request with image content
            
        Returns:
            Standardized chat response
        """
        # Anthropic vision is handled through the regular chat interface
        # when image content is included in messages
        return self.chat(request)

    def audio(self, request: ChatRequest) -> ChatResponse:
        """
        Process an audio input/request.
        
        Note: Anthropic doesn't support audio input natively.
        
        Args:
            request: Standardized chat request with audio content
            
        Returns:
            Standardized chat response
        """
        raise NotImplementedError("Anthropic provider does not support audio input")

    def embeddings(self, request: ChatRequest) -> ChatResponse:
        """
        Generate embeddings for input text.
        
        Note: Anthropic doesn't provide embedding models.
        
        Args:
            request: Standardized chat request
            
        Returns:
            Standardized chat response
        """
        raise NotImplementedError("Anthropic provider does not support embeddings")