"""Groq provider profile (OpenAI-compatible LPU inference)."""

from providers import register_provider
from providers.base import ProviderProfile

groq = ProviderProfile(
    name="groq",
    env_vars=("GROQ_API_KEY",),
    display_name="Groq",
    description="Groq — ultra-fast LPU inference (OpenAI-compatible)",
    signup_url="https://console.groq.com/keys",
    category="cloud",
    logo="⚡",
    fallback_models=(
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ),
    base_url="https://api.groq.com/openai/v1",
    default_aux_model="llama-3.1-8b-instant",
)

register_provider(groq)
