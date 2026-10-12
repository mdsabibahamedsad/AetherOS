"""Cohere provider profile (OpenAI-compatible endpoint)."""

from providers import register_provider
from providers.base import ProviderProfile

cohere = ProviderProfile(
    name="cohere",
    env_vars=("COHERE_API_KEY",),
    display_name="Cohere",
    description="Cohere — Command models via OpenAI-compatible endpoint",
    signup_url="https://dashboard.cohere.com/api-keys",
    category="cloud",
    logo="🧭",
    fallback_models=(
        "command-a-03-2025",
        "command-r-plus-08-2024",
        "command-r-08-2024",
    ),
    base_url="https://api.cohere.com/compatibility/v1",
    default_aux_model="command-r-08-2024",
)

register_provider(cohere)
