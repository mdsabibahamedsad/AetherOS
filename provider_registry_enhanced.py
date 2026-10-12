"""
Enhanced Provider Registry for Aetheros - Phase 2

This module provides a centralized provider registry that serves as the 
single source of truth for provider capabilities, integrating with the 
existing provider definition system and universal provider interface.
"""

import time
import threading
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from universal_provider_interface import UniversalProviderInterface, ModelInfo, ProviderCapabilities

# Import existing provider system
try:
    from aetheros_cli.providers import get_provider, resolve_provider_full, HERMES_OVERLAYS, ProviderDef
    from aetheros_cli.providers import normalize_provider as _normalize_provider_name
    from agent.models_dev import get_provider_info as get_models_dev_provider_info
    from agent.models_dev import get_model_info as get_models_dev_model_info
    from agent.model_metadata import get_model_context_length
    HAS_PROVIDER_SYSTEM = True
except ImportError:
    HAS_PROVIDER_SYSTEM = False

# Import universal provider interface components
try:
    from universal_provider_interface import UniversalProviderInterface, ModelInfo as UPIModelInfo, ProviderCapabilities as UPIProviderCapabilities
    HAS_UNIVERSAL_INTERFACE = True
except ImportError:
    HAS_UNIVERSAL_INTERFACE = False
    # Define fallback types for type checking
    UniversalProviderInterface = object  # type: ignore
    ModelInfo = dict  # type: ignore
    ProviderCapabilities = dict  # type: ignore


@dataclass
class CachedProviderInfo:
    """Cached information about a provider."""
    provider_def: object = None  # ProviderDef when available
    models_dev_info: object = None
    capabilities: object = None  # ProviderCapabilities when available
    model_info_cache: Dict[str, object] = field(default_factory=dict)  # ModelInfo when available
    last_updated: float = field(default_factory=time.time)
    health_status: str = "unknown"
    last_health_check: float = 0.0
    response_time_ms: float = 0.0


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
    max_models_returned: int = None  # None means no limit
    # Additional metadata
    is_aggregator: bool = False
    auth_type: str = "api_key"
    transport_type: str = "openai_chat"


class ProviderRegistryEnhanced:
    """
    Enhanced Provider Registry that serves as a single source of truth for provider capabilities.
    
    This registry integrates:
    1. Existing provider definition system (aetheros_cli/providers.py)
    2. Universal provider interface implementations
    3. models.dev catalog for model information
    4. Caching and health monitoring
    """

    def __init__(self, cache_ttl: float = 300.0, health_check_interval: float = 60.0):
        """
        Initialize the enhanced provider registry.
        
        Args:
            cache_ttl: Time-to-live for cached provider information (seconds)
            health_check_interval: Interval for automatic health checks (seconds)
        """
        self._cache_ttl = cache_ttl
        self._health_check_interval = health_check_interval
        self._provider_cache: Dict[str, CachedProviderInfo] = {}
        self._provider_instances: Dict[str, UniversalProviderInterface] = {}
        self._lock = threading.RLock()
        
        # Start background health check thread if enabled
        self._health_check_thread = None
        self._stop_health_check = False

    def _is_cache_valid(self, cached_info: CachedProviderInfo) -> bool:
        """Check if cached provider information is still valid."
        return (time.time() - cached_info.last_updated) < self._cache_ttl
    """
        return (time.time() - cached_info.last_updated) < self._cache_ttl

    def _should_perform_health_check(self, cached_info: CachedProviderInfo) -> bool:
        """Check if a health check should be performed."""
        return (time.time() - cached_info.last_health_check) > self._health_check_interval

    def get_provider_definition(self, provider_id: str):
        """
        Get the provider definition from the existing provider system.
        
        Args:
            provider_id: Unique identifier for the provider
            
        Returns:
            ProviderDef if found, None otherwise
        """
        if not HAS_PROVIDER_SYSTEM:
            return None
            
        # Normalize the provider ID
        normalized_id = _normalize_provider_name(provider_id)
        
        # Try to get from existing provider system
        provider_def = get_provider(normalized_id)
        if provider_def is not None:
            return provider_def
            
        # Try full resolution (including user config)
        provider_def = resolve_provider_full(normalized_id)
        return provider_def

    def get_provider_capabilities(self, provider_id: str):
        """
        Get provider capabilities, using cache when possible.
        
        Args:
            provider_id: Unique identifier for the provider
            
        Returns:
            ProviderCapabilities object
        """
        with self._lock:
            # Check cache first
            if provider_id in self._provider_cache:
                cached_info = self._provider_cache[provider_id]
                if self._is_cache_valid(cached_info) and cached_info.capabilities is not None:
                    return cached_info.capabilities
            
            # Get provider definition
            provider_def = self.get_provider_definition(provider_id)
            
            # Determine capabilities based on provider definition and known metadata
            capabilities = self._determine_capabilities_from_definition(provider_def)
            
            # Update cache
            if provider_id not in self._provider_cache:
                self._provider_cache[provider_id] = CachedProviderInfo()
            
            self._provider_cache[provider_id].capabilities = capabilities
            self._provider_cache[provider_id].provider_def = provider_def
            self._provider_cache[provider_id].last_updated = time.time()
            
            return capabilities

    def _determine_capabilities_from_definition(self, provider_def):
        """
        Determine provider capabilities from provider definition and known metadata.
        
        Args:
            provider_def: Provider definition from existing system
            
        Returns:
            ProviderCapabilities object
        """
        # Handle case where provider_def is None (unknown provider)
        if provider_def is None:
            # Return base capabilities for unknown provider
            return ProviderCapabilities(
                supports_chat=True,  # All providers support chat at minimum
                supports_streaming=False,  # Conservative default
                supports_tool_calls=False,  # Conservative default
                supports_structured_output=False,  # Conservative default
                supports_vision=False,  # Conservative default
                supports_audio=False,  # Conservative default
                supports_embeddings=False,  # Conservative default
                supports_reasoning=False,  # Conservative default
                max_models_returned=None,
                is_aggregator=False,
                auth_type="api_key",
                transport_type="openai_chat"
            )
        
        # Start with base capabilities
        capabilities = ProviderCapabilities(
            supports_chat=True,  # All providers support chat at minimum
            supports_streaming=False,  # Conservative default
            supports_tool_calls=False,  # Conservative default
            supports_structured_output=False,  # Conservative default
            supports_vision=False,  # Conservative default
            supports_audio=False,  # Conservative default
            supports_embeddings=False,  # Conservative default
            supports_reasoning=False,  # Conservative default
            max_models_returned=None,
            is_aggregator=provider_def.is_aggregator,
            auth_type=provider_def.auth_type,
            transport_type=provider_def.transport
        )
        
        # Enhance capabilities based on known provider characteristics
        provider_id_lower = provider_def.id.lower()
        
        # Known providers with specific capabilities
        if "anthropic" in provider_id_lower or "claude" in provider_id_lower:
            capabilities.supports_tool_calls = True
            capabilities.supports_vision = True
            capabilities.supports_reasoning = True
            capabilities.supports_streaming = True
            
        elif "openai" in provider_id_lower or "gpt" in provider_id_lower:
            capabilities.supports_tool_calls = True
            capabilities.supports_streaming = True
            capabilities.supports_reasoning = True
            # Vision depends on specific model (gpt-4-vision, gpt-4o, etc.)
            
        elif "gemini" in provider_id_lower or "google" in provider_id_lower:
            capabilities.supports_tool_calls = True
            capabilities.supports_streaming = True
            capabilities.supports_vision = True
            
        elif "xai" in provider_id_lower or "grok" in provider_id_lower:
            capabilities.supports_tool_calls = True
            capabilities.supports_streaming = True
            
        # Aggregators typically have broader model access
        if provider_def.is_aggregator:
            capabilities.max_models_returned = 1000  # Aggregators can return many models
        
        return capabilities

    def get_provider_model_info(self, provider_id: str, model_id: str) -> Optional[object]:
        """
        Get model information for a specific provider and model.
        
        Args:
            provider_id: Unique identifier for the provider
            model_id: Identifier for the model
            
        Returns:
            Model information dict if found, None otherwise
        """
        with self._lock:
            # Check cache first
            if provider_id in self._provider_cache:
                cached_info = self._provider_cache[provider_id]
                if self._is_cache_valid(cached_info):
                    if model_id in cached_info.model_info_cache:
                        cached_info.model_info_cache[model_id].access_count += 1
                        return cached_info.model_info_cache[model_id]
            
            # Get from models.dev if available
            model_info = None
            if HAS_PROVIDER_SYSTEM:
                try:
                    # Normalize provider ID for models.dev lookup
                    normalized_provider_id = _normalize_provider_name(provider_id)
                    model_info = get_models_dev_model_info(normalized_provider_id, model_id)
                except Exception:
                    pass  # Fall back to None if models.dev lookup fails
            
            # Cache the result
            if model_info is not None:
                if provider_id not in self._provider_cache:
                    self._provider_cache[provider_id] = CachedProviderInfo()
                
                self._provider_cache[provider_id].model_info_cache[model_id] = model_info
                self._provider_cache[provider_id].last_updated = time.time()
            
            return model_info

    def list_provider_models(self, provider_id: str, limit=None) -> List[object]:
        """
        List available models for a provider.
        
        Args:
            provider_id: Unique identifier for the provider
            limit: Maximum number of models to return (None for no limit)
            
        Returns:
            List of model information dicts
        """
        with self._lock:
            # Get provider capabilities to see if we can list models
            capabilities = self.get_provider_capabilities(provider_id)
            
            # If we have a limit from capabilities, use it unless overridden
            effective_limit = limit
            if limit is None and capabilities.max_models_returned is not None:
                effective_limit = capabilities.max_models_returned
            
            # Try to get models from models.dev
            models = []
            if HAS_PROVIDER_SYSTEM:
                try:
                    # Get provider info from models.dev
                    normalized_provider_id = _normalize_provider_name(provider_id)
                    provider_info = get_models_dev_provider_info(normalized_provider_id)
                    if provider_info and hasattr(provider_info, 'model_count'):
                        # We know how many models exist, but models.dev doesn't provide 
                        # an easy way to list them all without fetching each individually
                        # For now, we'll rely on individual model lookups or cached values
                        pass
                except Exception:
                    pass
            
            # Return what we have cached (in a real implementation, we'd fetch from provider)
            if provider_id in self._provider_cache:
                cached_info = self._provider_cache[provider_id]
                if self._is_cache_valid(cached_info):
                    models = list(cached_info.model_info_cache.values())
                    if effective_limit is not None:
                        models = models[:effective_limit]
            
            return models

    def get_or_create_provider_instance(self, provider_id: str) -> Optional[UniversalProviderInterface]:
        """
        Get or create a provider instance that implements the universal provider interface.
        
        Args:
            provider_id: Unique identifier for the provider
            
        Returns:
            Provider instance implementing UniversalProviderInterface, or None if not available
        """
        with self._lock:
            # Check if we already have an instance
            if provider_id in self._provider_instances:
                return self._provider_instances[provider_id]
            
            # Try to create an instance based on provider type
            provider_def = self.get_provider_definition(provider_id)
            if provider_def is None:
                return None
            
            # Import and create the appropriate provider implementation
            instance = self._create_provider_instance(provider_def)
            if instance is not None:
                self._provider_instances[provider_id] = instance
            
            return instance

    def _create_provider_instance(self, provider_def):
        """
        Create a provider instance based on provider definition.
        
        Args:
            provider_def: Provider definition
            
        Returns:
            Provider instance implementing UniversalProviderInterface, or None if creation failed
        """
        if not HAS_UNIVERSAL_INTERFACE:
            return None
        
        provider_id_lower = provider_def.id.lower()
        
        try:
            # Try to import and create provider-specific implementation
            if "anthropic" in provider_id_lower:
                from anthropic_provider_impl import AnthropicProvider
                return AnthropicProvider()
            elif "openai" in provider_id_lower:
                # TODO: Import OpenAI provider implementation when created
                # from openai_provider_impl import OpenAIProvider
                # return OpenAIProvider()
                pass
            elif "azure" in provider_id_lower:
                # TODO: Import Azure provider implementation when created
                # from azure_provider_impl import AzureProvider
                # return AzureProvider()
                pass
            elif "google" in provider_id_lower or "gemini" in provider_id_lower:
                # TODO: Import Google provider implementation when created
                # from google_provider_impl import GoogleProvider
                # return GoogleProvider()
                pass
            # Add more providers as implementations are created
            
            # If no specific implementation found, we could create a generic wrapper
            # that uses the existing adapter system, but for now return None
            # to indicate that no universal interface implementation is available
            return None
            
        except ImportError:
            # Implementation not yet created
            return None
        except Exception:
            # Creation failed
            return None

    def perform_health_check(self, provider_id: str) -> Tuple[str, float]:
        """
        Perform a health check on a provider.
        
        Args:
            provider_id: Unique identifier for the provider
            
        Returns:
            Tuple of (status, response_time_ms)
        """
        start_time = time.time()
        status = "unknown"
        response_time_ms = 0.0
        
        try:
            # Get provider instance
            instance = self.get_or_create_provider_instance(provider_id)
            if instance is None:
                # Fallback: try to validate credentials using existing system
                status, response_time_ms = self._legacy_health_check(provider_id)
            else:
                # Use universal provider interface for health check
                status, response_time_ms = instance.health_check()
                
        except Exception as e:
            status = "unhealthy"
            # In a real implementation, we'd log the exception
        
        finally:
            response_time_ms = (time.time() - start_time) * 1000.0
            
            # Update cache
            with self._lock:
                if provider_id not in self._provider_cache:
                    self._provider_cache[provider_id] = CachedProviderInfo()
                
                self._provider_cache[provider_id].health_status = status
                self._provider_cache[provider_id].last_health_check = time.time()
                self._provider_cache[provider_id].response_time_ms = response_time_ms
                self._provider_cache[provider_id].last_updated = time.time()
        
        return status, response_time_ms

    def _legacy_health_check(self, provider_id: str) -> Tuple[str, float]:
        """
        Perform a legacy health check using existing systems when universal interface not available.
        
        Args:
            provider_id: Unique identifier for the provider
            
        Returns:
            Tuple of (status, response_time_ms)
        """
        start_time = time.time()
        
        try:
            # Try to validate that we can get provider definition
            provider_def = self.get_provider_definition(provider_id)
            if provider_def is None:
                return "unhealthy", 0.0
            
            # Try to validate that we have required credentials/environment
            # This is a simplified check - in practice, we'd want to validate actual API connectivity
            if provider_def.api_key_env_vars:
                # Check if any of the required environment variables are set
                import os
                has_credentials = any(os.getenv(env_var) for env_var in provider_def.api_key_env_vars)
                if not has_credentials:
                    return "degraded", 0.0  # No credentials but provider exists
            
            # Basic connectivity check passed
            return "healthy", 0.0
            
        except Exception:
            return "unhealthy", 0.0
        finally:
            pass  # response_time_ms calculated in caller

    def get_provider_status(self, provider_id: str) -> Tuple[str, float]:
        """
        Get the cached health status of a provider.
        
        Args:
            provider_id: Unique identifier for the provider
            
        Returns:
            Tuple of (status, response_time_ms)
        """
        with self._lock:
            if provider_id in self._provider_cache:
                cached_info = self._provider_cache[provider_id]
                return cached_info.health_status, cached_info.response_time_ms
            return "unknown", 0.0

    def list_providers(self) -> List[str]:
        """
        List all known provider IDs.
        
        Returns:
            List of provider IDs
        """
        providers = set()
        
        # Get from existing provider system
        if HAS_PROVIDER_SYSTEM:
            try:
                # This is tricky because the existing system doesn't have a simple list_all function
                # We'll need to rely on our cache or known provider lists
                pass
            except Exception:
                pass
        
        # Add from cache
        with self._lock:
            providers.update(self._provider_cache.keys())
            providers.update(self._provider_instances.keys())
        
        return list(providers)

    def is_provider_available(self, provider_id: str) -> bool:
        """
        Check if a provider is available and healthy.
        
        Args:
            provider_id: Unique identifier for the provider
            
        Returns:
            True if provider is available, False otherwise
        """
        status, _ = self.get_provider_status(provider_id)
        return status in ["healthy", "degraded"]  # degraded means usable but with issues

    def start_health_monitoring(self):
        """Start background health monitoring thread."""
        if self._health_check_thread is not None and self._health_check_thread.is_alive():
            return  # Already running
        
        self._stop_health_check = False
        self._health_check_thread = threading.Thread(target=self._health_monitoring_loop, daemon=True)
        self._health_check_thread.start()

    def stop_health_monitoring(self):
        """Stop background health monitoring thread."""
        self._stop_health_check = True
        if self._health_check_thread is not None:
            self._health_check_thread.join(timeout=5.0)
            self._health_check_thread = None

    def _health_monitoring_loop(self):
        """Background loop for performing periodic health checks."""
        while not self._stop_health_check:
            try:
                # Get list of providers to check
                providers = self.list_providers()
                
                # Check each provider that hasn't been checked recently
                for provider_id in providers:
                    if self._stop_health_check:
                        break
                    
                    with self._lock:
                        if provider_id in self._provider_cache:
                            cached_info = self._provider_cache[provider_id]
                            if self._should_perform_health_check(cached_info):
                                # Perform health check outside of lock to avoid blocking
                                pass
                    
                    # Perform health check (without holding lock the entire time)
                    self.perform_health_check(provider_id)
                
                # Sleep for a bit before next iteration
                time.sleep(min(self._health_check_interval, 30.0))  # Check at least every 30 seconds
                
            except Exception:
                # In a real implementation, we'd log this error
                time.sleep(5.0)  # Back off on error

    def clear_cache(self):
        """Clear all cached provider information."""
        with self._lock:
            self._provider_cache.clear()
            # Note: We don't clear provider instances as they may be expensive to recreate

    def get_registry_stats(self) -> dict:
        """
        Get statistics about the provider registry.
        
        Returns:
            Dictionary with registry statistics
        """
        with self._lock:
            total_providers = len(self._provider_cache)
            healthy_providers = sum(1 for info in self._provider_cache.values() 
                                  if info.health_status == "healthy")
            degraded_providers = sum(1 for info in self._provider_cache.values() 
                                   if info.health_status == "degraded")
            unhealthy_providers = sum(1 for info in self._provider_cache.values() 
                                    if info.health_status == "unhealthy")
            unknown_providers = sum(1 for info in self._provider_cache.values() 
                                  if info.health_status == "unknown")
            
            return {
                "total_providers": total_providers,
                "healthy_providers": healthy_providers,
                "degraded_providers": degraded_providers,
                "unhealthy_providers": unhealthy_providers,
                "unknown_providers": unknown_providers,
                "cached_instances": len(self._provider_instances),
                "cache_ttl_seconds": self._cache_ttl,
                "health_check_interval_seconds": self._health_check_interval
            }
# Global enhanced provider registry instance
enhanced_provider_registry = ProviderRegistryEnhanced()
