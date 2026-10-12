"""Tests for the eight gap-fill provider plugins.

Each plugin must register a ProviderProfile with a resolvable name, an API-key
env var, and sensible fallback models — so that downstream infrastructure
(PROVIDER_REGISTRY, CANONICAL_PROVIDERS, model pickers, health checks) can see
it through the standard registry.
"""

from providers import get_provider_profile, list_providers

EXPECTED = {
    "groq": {"api_key": "GROQ_API_KEY", "health": True},
    "mistral": {"api_key": "MISTRAL_API_KEY", "health": True},
    "together": {"api_key": "TOGETHER_API_KEY", "health": True},
    "fireworks": {"api_key": "FIREWORKS_API_KEY", "health": True},
    "cohere": {"api_key": "COHERE_API_KEY", "health": True},
    "perplexity": {"api_key": "PERPLEXITY_API_KEY", "health": True},
    "cloudflare": {"api_key": "CLOUDFLARE_API_KEY", "health": False},
    "google-vertex-ai": {"api_key": "VERTEX_AI_API_KEY", "health": False},
}


def test_all_gap_providers_registered():
    names = {p.name for p in list_providers()}
    for slug in EXPECTED:
        assert slug in names, f"{slug} not registered"


def test_each_gap_provider_has_api_key_env_var():
    for slug, spec in EXPECTED.items():
        profile = get_provider_profile(slug)
        assert profile is not None
        assert spec["api_key"] in profile.env_vars, f"{slug} missing {spec['api_key']} env var"


def test_each_gap_provider_has_fallback_models():
    for slug in EXPECTED:
        profile = get_provider_profile(slug)
        assert profile.fallback_models, f"{slug} has no fallback_models"


def test_health_check_flags_match_spec():
    for slug, spec in EXPECTED.items():
        profile = get_provider_profile(slug)
        assert profile.supports_health_check is spec["health"], f"{slug} health flag mismatch"


def test_alias_resolution():
    assert get_provider_profile("togetherai").name == "together"
    assert get_provider_profile("vertex").name == "google-vertex-ai"
    assert get_provider_profile("workers-ai").name == "cloudflare"


def test_providers_appear_in_auth_registry():
    from aetheros_cli.auth import PROVIDER_REGISTRY

    for slug in ("groq", "mistral", "google-vertex-ai"):
        assert slug in PROVIDER_REGISTRY, f"{slug} missing from PROVIDER_REGISTRY"


def test_providers_appear_in_canonical_providers():
    from aetheros_cli.models import CANONICAL_PROVIDERS
    slugs = {p.slug for p in CANONICAL_PROVIDERS}
    for slug in ("groq", "perplexity", "cloudflare"):
        assert slug in slugs, f"{slug} missing from CANONICAL_PROVIDERS"

