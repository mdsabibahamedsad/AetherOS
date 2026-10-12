"""
Enhanced Provider Initialization for Aetheros - Phase 2

This module initializes and registers all built-in provider implementations
with the enhanced provider registry.
"""

from provider_registry_enhanced import enhanced_provider_registry
from anthropic_provider_impl import AnthropicProvider
# Import other provider implementations as they are created
# from .openai_provider_impl import OpenAIProvider
# from .azure_provider_impl import AzureProvider
# etc.


def initialize_enhanced_providers() -> None:
    """
    Initialize and register all built-in provider implementations
    with the enhanced provider registry.
    This function should be called during application startup.
    """
    # Register Anthropic provider with enhanced registry
    # Note: The enhanced registry creates instances on demand,
    # but we can pre-warm the cache or perform initial health checks
    pass  # Enhanced registry handles instance creation on demand


def get_enhanced_provider(provider_id: str):
    """
    Get a provider instance by ID from the enhanced registry.
    
    Args:
        provider_id: Unique identifier for the provider
        
    Returns:
        Provider instance if found, None otherwise
    """
    return enhanced_provider_registry.get_or_create_provider_instance(provider_id)


def list_enhanced_providers() -> List[str]:
    """
    List all provider IDs known to the enhanced registry.
    
    Returns:
        List of provider IDs
    """
    return enhanced_provider_registry.list_providers()


def get_provider_capabilities(provider_id: str):
    """
    Get provider capabilities from the enhanced registry.
    
    Args:
        provider_id: Unique identifier for the provider
        
    Returns:
        ProviderCapabilities object
    """
    return enhanced_provider_registry.get_provider_capabilities(provider_id)


def get_provider_model_info(provider_id: str, model_id: str):
    """
    Get model information for a specific provider and model.
    
    Args:
        provider_id: Unique identifier for the provider
        model_id: Identifier for the model
        
    Returns:
        Model information dict if found, None otherwise
    """
    return enhanced_provider_registry.get_provider_model_info(provider_id, model_id)


def perform_provider_health_check(provider_id: str) -> Tuple[str, float]:
    """
    Perform a health check on a provider.
    
    Args:
        provider_id: Unique identifier for the provider
        
    Returns:
        Tuple of (status, response_time_ms)
    """
    return enhanced_provider_registry.perform_health_check(provider_id)


# Auto-initialize enhanced providers when module is imported
# Comment this out if you prefer explicit initialization
initialize_enhanced_providers()