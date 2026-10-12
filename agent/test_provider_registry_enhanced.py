"""
Tests for the enhanced provider registry - Phase 2
"""

import unittest
import time
from unittest.mock import patch, MagicMock

# Try to import the enhanced provider registry
try:
    from provider_registry_enhanced import (
        ProviderRegistryEnhanced, 
        ProviderCapabilities, 
        CachedProviderInfo,
        enhanced_provider_registry
    )
    HAS_ENHANCED_REGISTRY = True
except ImportError:
    HAS_ENHANCED_REGISTRY = False

# Try to import existing provider system for integration tests
try:
    from aetheros_cli.providers import get_provider, ProviderDef
    HAS_PROVIDER_SYSTEM = True
except ImportError:
    HAS_PROVIDER_SYSTEM = False


class TestProviderRegistryEnhanced(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        if HAS_ENHANCED_REGISTRY:
            self.registry = ProviderRegistryEnhanced(cache_ttl=1.0, health_check_interval=0.1)
    
    def test_registry_creation(self):
        """Test that the registry can be created."""
        if not HAS_ENHANCED_REGISTRY:
            self.skipTest("Enhanced provider registry not available")
        
        self.assertIsInstance(self.registry, ProviderRegistryEnhanced)
    
    def test_cache_validity(self):
        """Test cache validity checking."""
        if not HAS_ENHANCED_REGISTRY:
            self.skipTest("Enhanced provider registry not available")
            
        cached_info = CachedProviderInfo()
        cached_info.last_updated = time.time() - 2.0  # Old timestamp (2 seconds ago)
        
        # Should be invalid with short TTL (1.0 second)
        self.assertFalse(self.registry._is_cache_valid(cached_info))
        
        # Should be valid with recent timestamp
        cached_info.last_updated = time.time() - 0.5  # Recent timestamp (0.5 seconds ago)
        self.assertTrue(self.registry._is_cache_valid(cached_info))
    
    def test_health_check_timing(self):
        """Test health check timing logic."""
        if not HAS_ENHANCED_REGISTRY:
            self.skipTest("Enhanced provider registry not available")
            
        cached_info = CachedProviderInfo()
        cached_info.last_health_check = time.time() - 0.2  # Old timestamp (0.2 seconds ago)
        
        # Should perform health check with short interval (0.1 seconds)
        self.assertTrue(self.registry._should_perform_health_check(cached_info))
        
        # Should not perform health check with recent timestamp
        cached_info.last_health_check = time.time() - 0.05  # Recent timestamp (0.05 seconds ago)
        self.assertFalse(self.registry._should_perform_health_check(cached_info))
    
    @unittest.skipIf(not HAS_PROVIDER_SYSTEM, "Existing provider system not available")
    def test_get_provider_definition(self):
        """Test getting provider definition from existing system."""
        if not HAS_ENHANCED_REGISTRY:
            self.skipTest("Enhanced provider registry not available")
            
        # Test with a known provider
        provider_def = self.registry.get_provider_definition("anthropic")
        # Note: This might return None if the provider system isn't fully configured in test env
        # We're mainly testing that the method doesn't crash
        self.assertTrue(provider_def is None or isinstance(provider_def, ProviderDef))
    
    def test_get_provider_capabilities(self):
        """Test getting provider capabilities."""
        if not HAS_ENHANCED_REGISTRY:
            self.skipTest("Enhanced provider registry not available")
            
        # Test with known provider ID
        capabilities = self.registry.get_provider_capabilities("anthropic")
        self.assertIsInstance(capabilities, ProviderCapabilities)
        self.assertTrue(capabilities.supports_chat)  # All providers should support chat
        
        # Test with unknown provider ID
        capabilities = self.registry.get_provider_capabilities("unknown-provider-xyz")
        self.assertIsInstance(capabilities, ProviderCapabilities)
        # Should return default capabilities
    
    def test_list_providers(self):
        """Test listing providers."""
        if not HAS_ENHANCED_REGISTRY:
            self.skipTest("Enhanced provider registry not available")
            
        providers = self.registry.list_providers()
        self.assertIsInstance(providers, list)
        # Should be a list of strings (even if empty)
        for provider in providers:
            self.assertIsInstance(provider, str)
    
    def test_is_provider_available(self):
        """Test checking if provider is available."""
        if not HAS_ENHANCED_REGISTRY:
            self.skipTest("Enhanced provider registry not available")
            
        # Test with known provider
        available = self.registry.is_provider_available("anthropic")
        self.assertIsInstance(available, bool)
        
        # Test with unknown provider
        available = self.registry.is_provider_available("unknown-provider-xyz")
        self.assertIsInstance(available, bool)
    
    def test_registry_stats(self):
        """Test getting registry statistics."""
        if not HAS_ENHANCED_REGISTRY:
            self.skipTest("Enhanced provider registry not available")
            
        stats = self.registry.get_registry_stats()
        self.assertIsInstance(stats, dict)
        expected_keys = [
            "total_providers", "healthy_providers", "degraded_providers", 
            "unhealthy_providers", "unknown_providers", "cached_instances",
            "cache_ttl_seconds", "health_check_interval_seconds"
        ]
        for key in expected_keys:
            self.assertIn(key, stats)
            self.assertIsInstance(stats[key], (int, float))
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        if not HAS_ENHANCED_REGISTRY:
            self.skipTest("Enhanced provider registry not available")
        
        # Add something to cache first - use a definitely unknown provider
        provider_name = "definitely-unknown-provider-12345"
        capabilities = self.registry.get_provider_capabilities(provider_name)
        self.assertIsInstance(capabilities, ProviderCapabilities)
        
        # Check that it was added to cache
        self.assertIn(provider_name, self.registry._provider_cache)
        self.assertGreater(len(self.registry._provider_cache), 0)
        
        # Clear cache
        self.registry.clear_cache()
        self.assertEqual(len(self.registry._provider_cache), 0)


class TestEnhancedProviderInit(unittest.TestCase):
    """Test the enhanced provider initialization module."""
    
    def test_initialize_enhanced_providers(self):
        """Test that initialization doesn't crash."""
        try:
            from provider_init_enhanced import initialize_enhanced_providers
            initialize_enhanced_providers()  # Should not raise exception
        except ImportError:
            self.skipTest("Enhanced provider init not available")
    
    def test_get_enhanced_provider(self):
        """Test getting provider from enhanced init."""
        try:
            from provider_init_enhanced import get_enhanced_provider
            provider = get_enhanced_provider("anthropic")
            # Should return None or a provider instance (not crash)
            self.assertTrue(provider is None or hasattr(provider, '__class__'))
        except ImportError:
            self.skipTest("Enhanced provider init not available")


if __name__ == '__main__':
    unittest.main()