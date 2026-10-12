"""Mistral AI provider profile (OpenAI-compatible)."""

from providers import register_provider
from providers.base import ProviderProfile

mistral = ProviderProfile(
    name="mistral",
    env_vars=("MISTRAL_API_KEY",),
    display_name="Mistral AI",
    description="Mistral AI — direct API (OpenAI-compatible)",
    signup_url="https://console.mistral.ai/",
    category="cloud",
    logo="🔷",
    fallback_models=(
        "mistral-large-latest",
        "mistral-small-latest",
        "open-mistral-nemo",
    ),
    base_url="https://api.mistral.ai/v1",
    default_aux_model="open-mistral-nemo",
)

register_provider(mistral)
