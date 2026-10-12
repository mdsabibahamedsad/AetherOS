"""
Tests for the unified model registry - Phase 3
"""

import unittest
import time
from unittest.mock import patch, MagicMock

# Try to import the unified model registry
try:
    from unified_model_registry import UnifiedModelRegistry, CachedModelInfo, ModelAlias
    HAS_UNIFIED_REGISTRY = True
except ImportError:
    HAS_UNIFIED_REGISTRY = False


class TestUnifiedModelRegistry(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        if HAS_UNIFIED_REGISTRY:
            self.registry = UnifiedModelRegistry(cache_ttl=1.0, enable_background_updates=False)
    
    def test_registry_creation(self):
        """Test that the registry can be created."""
        if not HAS_UNIFIED_REGISTRY:
            self.skipTest("Unified model registry not available")
        
        self.assertIsInstance(self.registry, UnifiedModelRegistry)
    
    def test_cache_validity(self):
        """Test cache validity checking.""" 
        if not HAS_UNIFIED_REGISTRY:
            self.skipTest("Unified model registry not available")
            
        cached_info = CachedModelInfo()
        cached_info.last_updated = 0  # Old timestamp
        
        # Should be invalid with short TTL
        self.assertFalse(self.registry._is_cache_valid(cached_info))
        
        # Should be valid with recent timestamp
        cached_info.last_updated = time.time() - 0.5  # Recent timestamp
        self.assertTrue(self.registry._is_cache_valid(cached_info))
    
    def test_model_alias_creation(self):
        """Test creating model aliases."""
        if not HAS_UNIFIED_REGISTRY:
            self.skipTest("Unified model registry not available")
            
        # Test creating an alias
        self.registry.register_model_alias("gpt-4", "gpt-4-0613", "openai", is_primary=True)
        
        # Test resolving the alias
        canonical_id = self.registry._resolve_model_alias("openai", "gpt-4")
        self.assertEqual(canonical_id, "gpt-4-0613")
        
        # Test getting aliases
        aliases = self.registry.get_model_aliases("openai", "gpt-4-0613")
        self.assertIn("gpt-4", aliases)
    
    def test_get_model_info_basic(self):
        """Test getting basic model info when no sources are available."""
        if not HAS_UNIFIED_REGISTRY:
            self.skipTest("Unified model registry not available")
            
        # Test with unknown provider/model
        model_info = self.registry.get_model_info("unknown-provider", "unknown-model")
        self.assertIsNotNone(model_info)
        # Should return a basic model info object
        self.assertTrue(hasattr(model_info, 'id') or isinstance(model_info, dict))
    
    def test_list_models_for_provider(self):
        """Test listing models for a provider."""
        if not HAS_UNIFIED_REGISTRY:
            self.skipTest("Unified model registry not available")
            
        # Initially should be empty
        models = self.registry.list_models_for_provider("test-provider")
        self.assertEqual(models, [])
        
        # After getting model info, it should be in the list
        self.registry.get_model_info("test-provider", "test-model")
        models = self.registry.list_models_for_provider("test-provider")
        self.assertIn("test-model", models)
    
    def test_registry_stats(self):
        """Test getting registry statistics."""
        if not HAS_UNIFIED_REGISTRY:
            self.skipTest("Unified model registry not available")
            
        stats = self.registry.get_registry_stats()
        self.assertIsInstance(stats, dict)
        expected_keys = [
            "total_providers", "total_models", "total_aliases", 
            "cached_models", "cache_ttl_seconds", "background_updates_enabled"
        ]
        for key in expected_keys:
            self.assertIn(key, stats)
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        if not HAS_UNIFIED_REGISTRY:
            self.skipTest("Unified model registry not available")
            
        # Add something to cache first
        self.registry.get_model_info("test-provider", "test-model")
        self.assertGreater(len(self.registry._model_cache), 0)
        
        # Clear cache
        self.registry.clear_cache()
        self.assertEqual(len(self.registry._model_cache), 0)


if __name__ == '__main__':
    unittest.main()