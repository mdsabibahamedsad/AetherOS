"""Fireworks AI provider profile (OpenAI-compatible)."""

from providers import register_provider
from providers.base import ProviderProfile

fireworks = ProviderProfile(
    name="fireworks",
    aliases=("fireworks-ai",),
    env_vars=("FIREWORKS_API_KEY",),
    display_name="Fireworks AI",
    description="Fireworks AI — fast open-model inference (OpenAI-compatible)",
    signup_url="https://fireworks.ai/api-keys",
    category="cloud",
    logo="🎆",
    fallback_models=(
        "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "accounts/fireworks/models/deepseek-v3",
        "accounts/fireworks/models/qwen3-235b-a22b-instruct",
    ),
    base_url="https://api.fireworks.ai/inference/v1",
    default_aux_model="accounts/fireworks/models/llama-v3p3-70b-instruct",
)

register_provider(fireworks)
