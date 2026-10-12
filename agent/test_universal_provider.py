"""
Test script for the universal provider interface
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Mock the anthropic import for testing purposes
class MockAnthropic:
    class Anthropic:
        def __init__(self, *args, **kwargs):
            pass
        
        class messages:
            @staticmethod
            def create(*args, **kwargs):
                class MockResponse:
                    id = "test-id"
                    model = "test-model"
                    created_timestamp = 1234567890
                    content = [type('obj', (object,), {'text': 'test response'})()]
                    stop_reason = "stop"
                    usage = type('obj', (object,), {'input_tokens': 10, 'output_tokens': 5})()
                return MockResponse()
            
            @staticmethod
            def stream(*args, **kwargs):
                # Return a mock stream
                for i in range(2):
                    yield type('obj', (object,), {
                        'id': f'test-chunk-{i}',
                        'model': 'test-model',
                        'timestamp': 1234567890 + i,
                        'delta': type('obj', (object,), {'text': f'chunk-{i}'})()
                    })()

# Replace the anthropic module with our mock
sys.modules['anthropic'] = MockAnthropic()

# Mock the anthropic_adapter module
class MockAnthropicAdapter:
    @staticmethod
    def build_anthropic_client(*args, **kwargs):
        return MockAnthropic.Anthropic()
        
    @staticmethod
    def build_anthropic_bedrock_client(*args, **kwargs):
        return MockAnthropic.Anthropic()
        
    @staticmethod
    def _is_oauth_token(key):
        return False

sys.modules['anthropic_adapter'] = MockAnthropicAdapter

# Mock the model_metadata module
class MockModelMetadata:
    @staticmethod
    def get_model_context_length(*args, **kwargs):
        return 200000

sys.modules['model_metadata'] = MockModelMetadata

try:
    from anthropic_provider_impl import AnthropicProvider
    from provider_registry import provider_registry
    from universal_provider_interface import UniversalProviderInterface, ModelInfo, ChatRequest, ProviderCapabilities
except Exception as e:
    print(f"Error importing modules: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def test_anthropic_provider_interface():
    """Test that the Anthropic provider correctly implements the universal interface."""
    print("Testing Anthropic provider implementation...")
    
    # Create provider instance
    provider = AnthropicProvider()
    
    # Verify it implements the interface
    assert isinstance(provider, UniversalProviderInterface), "Provider should implement UniversalProviderInterface"
    
    # Test interface methods exist
    assert hasattr(provider, 'authenticate'), "Provider should have authenticate method"
    assert hasattr(provider, 'validate_credentials'), "Provider should have validate_credentials method"
    assert hasattr(provider, 'list_models'), "Provider should have list_models method"
    assert hasattr(provider, 'get_model'), "Provider should have get_model method"
    assert hasattr(provider, 'health_check'), "Provider should have health_check method"
    assert hasattr(provider, 'chat'), "Provider should have chat method"
    assert hasattr(provider, 'stream'), "Provider should have stream method"
    assert hasattr(provider, 'tool_call'), "Provider should have tool_call method"
    assert hasattr(provider, 'structured_output'), "Provider should have structured_output method"
    assert hasattr(provider, 'vision'), "Provider should have vision method"
    assert hasattr(provider, 'audio'), "Provider should have audio method"
    assert hasattr(provider, 'embeddings'), "Provider should have embeddings method"
    
    print("[PASS] All interface methods present")
    
    # Test provider properties
    assert provider.provider_id == "anthropic", "Provider ID should be 'anthropic'"
    assert provider.display_name == "Anthropic", "Display name should be 'Anthropic'"
    
    print("[PASS] Provider properties correct")
    
    # Test capabilities
    capabilities = provider.get_capabilities()
    assert isinstance(capabilities, ProviderCapabilities), "Should return ProviderCapabilities"
    assert capabilities.supports_chat == True, "Should support chat"
    assert capabilities.supports_streaming == True, "Should support streaming"
    assert capabilities.supports_tool_calls == True, "Should support tool calls"
    assert capabilities.supports_vision == True, "Should support vision"
    assert capabilities.supports_reasoning == True, "Should support reasoning"
    
    print("[PASS] Provider capabilities correct")
    
    # Test model normalization
    normalized = provider.normalize_model_id("  Claude-3-Opus  ")
    assert normalized == "claude-3-opus", "Should normalize model ID correctly"
    
    print("[PASS] Model normalization works")
    
    print("\nAll tests passed!")


def test_provider_registry():
    """Test the provider registry functionality."""
    print("\nTesting provider registry...")
    
    # Test initial state
    initial_providers = provider_registry.list_providers()
    print(f"Initial providers: {initial_providers}")
    
    # Test registering a provider
    provider_registry.register_provider("test-anthropic", AnthropicProvider)
    
    # Test that it's registered
    assert provider_registry.is_provider_registered("test-anthropic"), "Should be registered"
    
    # Test getting provider class
    provider_class = provider_registry.get_provider_class("test-anthropic")
    assert provider_class == AnthropicProvider, "Should return correct class"
    
    # Test getting provider instance
    provider_instance = provider_registry.get_provider_instance("test-anthropic")
    assert isinstance(provider_instance, AnthropicProvider), "Should return instance"
    
    # Test that we get the same instance on subsequent calls (caching)
    provider_instance2 = provider_registry.get_provider_instance("test-anthropic")
    assert provider_instance is provider_instance2, "Should return cached instance"
    
    print("[PASS] Provider registry works correctly")
    
    # Clean up
    provider_registry.unregister_provider("test-anthropic")
    
    print("[PASS] Provider registry cleanup works")


if __name__ == "__main__":
    try:
        test_anthropic_provider_interface()
        test_provider_registry()
        print("\n[SUCCESS] All tests passed!")
    except Exception as e:
        print(f"\n[FAILURE] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)