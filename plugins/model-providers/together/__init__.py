"""Together AI provider profile (OpenAI-compatible)."""

from providers import register_provider
from providers.base import ProviderProfile

together = ProviderProfile(
    name="together",
    aliases=("together-ai", "togetherai"),
    env_vars=("TOGETHER_API_KEY",),
    display_name="Together AI",
    description="Together AI — open-model cloud inference (OpenAI-compatible)",
    signup_url="https://api.together.xyz/settings/api-keys",
    category="cloud",
    logo="🟠",
    fallback_models=(
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "Qwen/Qwen3-235B-A22B-Instruct-Turbo",
    ),
    base_url="https://api.together.xyz/v1",
    default_aux_model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
)

register_provider(together)
