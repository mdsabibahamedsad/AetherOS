"""
Demo script showing the Unified Model Registry in action - Phase 3
"""

import time
from unified_model_registry import unified_model_registry
from provider_registry_enhanced import enhanced_provider_registry

print("=== Unified Model Registry Demo - Phase 3 ===")
print()

# Integrate the provider registry with the model registry
unified_model_registry.set_provider_registry(enhanced_provider_registry)

print("--- Testing Basic Model Info Retrieval ---")
# Test getting model info for various providers (will use fallback data since we don't have real API keys)
test_cases = [
    ("anthropic", "claude-3-opus-20240229"),
    ("openai", "gpt-4"),
    ("unknown-provider", "unknown-model"),
]

for provider_id, model_id in test_cases:
    print(f"Getting info for {provider_id}:{model_id}")
    model_info = unified_model_registry.get_model_info(provider_id, model_id)
    if model_info:
        if hasattr(model_info, 'display_name'):
            print(f"  Display name: {model_info.display_name}")
            print(f"  Context window: {getattr(model_info, 'context_window', 'N/A')}")
            print(f"  Provider ID: {getattr(model_info, 'provider_id', 'N/A')}")
            print(f"  Availability: {getattr(model_info, 'availability', 'N/A')}")
        else:
            print(f"  Model info (dict): {model_info}")
    else:
        print(f"  No model info found")
    print()

print("--- Testing Model Aliases ---")
# Register some model aliases
unified_model_registry.register_model_alias("gpt-4", "gpt-4-0613", "openai", is_primary=True)
unified_model_registry.register_model_alias("gpt-4-turbo", "gpt-4-1106-preview", "openai")
unified_model_registry.register_model_alias("claude-3", "claude-3-opus-20240229", "anthropic")

# Test resolving aliases
alias_tests = [
    ("openai", "gpt-4", "gpt-4-0613"),
    ("openai", "gpt-4-turbo", "gpt-4-1106-preview"),
    ("anthropic", "claude-3", "claude-3-opus-20240229"),
]

for provider_id, alias, expected_canonical in alias_tests:
    canonical_id = unified_model_registry._resolve_model_alias(provider_id, alias)
    status = "PASS" if canonical_id == expected_canonical else "FAIL"
    print(f"{status} {provider_id}:{alias} -> {canonical_id} (expected: {expected_canonical})")

print()
print("--- Testing Alias Retrieval ---")
# Get aliases for a model
aliases = unified_model_registry.get_model_aliases("openai", "gpt-4-0613")
print(f"Aliases for openai:gpt-4-0613: {aliases}")

print()
print("--- Testing Model Listing ---")
# List models for a provider (should include ones we've looked up)
openai_models = unified_model_registry.list_models_for_provider("openai")
print(f"Known OpenAI models: {openai_models}")

anthropic_models = unified_model_registry.list_models_for_provider("anthropic")
print(f"Known Anthropic models: {anthropic_models}")

print()
print("--- Testing Model Search ---")
# Search for models with specific criteria
print("Searching for models with context window > 8000:")
results = unified_model_registry.search_models(min_context_window=8000)
for provider_id, model_id, model_info in results[:5]:  # Show first 5 results
    context_window = getattr(model_info, 'context_window', 0) if model_info else 0
    print(f"  {provider_id}:{model_id} (context: {context_window})")

print()
print("--- Testing Registry Statistics ---")
stats = unified_model_registry.get_registry_stats()
print(f"Registry statistics:")
for key, value in stats.items():
    print(f"  {key}: {value}")

print()
print("=== Demo Complete ===")