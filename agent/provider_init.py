"""
Provider initialization for Aetheros

This module initializes and registers all built-in provider implementations
with the universal provider registry.
"""

from provider_registry import provider_registry
from anthropic_provider_impl import AnthropicProvider
# Import other provider implementations as they are created
# from .openai_provider_impl import OpenAIProvider
# from .azure_provider_impl import AzureProvider
# etc.


def initialize_providers() -> None:
    """
    Initialize and register all built-in provider implementations.
    This function should be called during application startup.
    """
    # Register Anthropic provider
    provider_registry.register_provider("anthropic", AnthropicProvider)
    
    # TODO: Register other providers as implementations are created
    # provider_registry.register_provider("openai", OpenAIProvider)
    # provider_registry.register_provider("azure", AzureProvider)
    # provider_registry.register_provider("google", GoogleProvider)
    # etc.


def get_provider(provider_id: str):
    """
    Get a provider instance by ID.
    
    Args:
        provider_id: Unique identifier for the provider
        
    Returns:
        Provider instance if found, None otherwise
    """
    return provider_registry.get_provider_instance(provider_id)


def list_providers() -> List[str]:
    """
    List all registered provider IDs.
    
    Returns:
        List of provider IDs
    """
    return provider_registry.list_providers()


# Auto-initialize providers when module is imported
# Comment this out if you prefer explicit initialization
initialize_providers()