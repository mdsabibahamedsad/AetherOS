"""
Universal Provider Registry for Aetheros

This module provides a registry for managing provider implementations
that adhere to the universal provider interface.
"""

from typing import Dict, List, Optional, Type
from universal_provider_interface import UniversalProviderInterface


class ProviderRegistry:
    """
    Registry for managing provider implementations.
    
    This allows the model intelligence layer to discover and instantiate
    provider implementations without hardcoding dependencies.
    """

    def __init__(self):
        self._providers: Dict[str, Type[UniversalProviderInterface]] = {}
        self._instances: Dict[str, UniversalProviderInterface] = {}

    def register_provider(
        self, 
        provider_id: str, 
        provider_class: Type[UniversalProviderInterface]
    ) -> None:
        """
        Register a provider implementation.
        
        Args:
            provider_id: Unique identifier for the provider
            provider_class: Class implementing UniversalProviderInterface
        """
        if not issubclass(provider_class, UniversalProviderInterface):
            raise ValueError(
                f"Provider class {provider_class} must implement UniversalProviderInterface"
            )
            
        self._providers[provider_id] = provider_class
        # Clear any cached instance when registering a new implementation
        self._instances.pop(provider_id, None)

    def get_provider_class(self, provider_id: str) -> Optional[Type[UniversalProviderInterface]]:
        """
        Get the provider class for a given provider ID.
        
        Args:
            provider_id: Unique identifier for the provider
            
        Returns:
            Provider class if found, None otherwise
        """
        return self._providers.get(provider_id)

    def get_provider_instance(self, provider_id: str) -> Optional[UniversalProviderInterface]:
        """
        Get or create an instance of a provider.
        
        Args:
            provider_id: Unique identifier for the provider
            
        Returns:
            Provider instance if found/registerable, None otherwise
        """
        if provider_id in self._instances:
            return self._instances[provider_id]
            
        provider_class = self.get_provider_class(provider_id)
        if provider_class is None:
            return None
            
        # Create and cache the instance
        instance = provider_class()
        self._instances[provider_id] = instance
        return instance

    def list_providers(self) -> List[str]:
        """
        List all registered provider IDs.
        
        Returns:
            List of provider IDs
        """
        return list(self._providers.keys())

    def is_provider_registered(self, provider_id: str) -> bool:
        """
        Check if a provider is registered.
        
        Args:
            provider_id: Unique identifier for the provider
            
        Returns:
            True if provider is registered, False otherwise
        """
        return provider_id in self._providers

    def unregister_provider(self, provider_id: str) -> None:
        """
        Unregister a provider.
        
        Args:
            provider_id: Unique identifier for the provider
        """
        self._providers.pop(provider_id, None)
        self._instances.pop(provider_id, None)

    def clear(self) -> None:
        """Clear all registered providers and instances."""
        self._providers.clear()
        self._instances.clear()


# Global provider registry instance
provider_registry = ProviderRegistry()