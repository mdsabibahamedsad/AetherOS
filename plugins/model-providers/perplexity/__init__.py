"""Perplexity provider profile (OpenAI-compatible)."""

from providers import register_provider
from providers.base import ProviderProfile

perplexity = ProviderProfile(
    name="perplexity",
    aliases=("pplx", "perplexity-ai"),
    env_vars=("PERPLEXITY_API_KEY",),
    display_name="Perplexity",
    description="Perplexity — Sonar models via OpenAI-compatible API",
    signup_url="https://www.perplexity.ai/settings/api",
    category="cloud",
    logo="🌐",
    fallback_models=(
        "sonar-pro",
        "sonar",
        "sonar-reasoning-pro",
    ),
    base_url="https://api.perplexity.ai",
    default_aux_model="sonar",
)

register_provider(perplexity)
