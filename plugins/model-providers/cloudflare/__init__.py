"""Cloudflare Workers AI provider profile.

Workers AI exposes an OpenAI-compatible endpoint scoped per account::

    https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1

The ``account_id`` lives in the path, so the base URL cannot be hardcoded.
Set ``CLOUDFLARE_BASE_URL`` to your full account-scoped endpoint (and
``CLOUDFLARE_API_KEY`` / ``CLOUDFLARE_ACCOUNT_ID``) or configure it through
``aetheros providers set cloudflare --base-url <url>``.
"""

from providers import register_provider
from providers.base import ProviderProfile

cloudflare = ProviderProfile(
    name="cloudflare",
    aliases=("cloudflare-workers-ai", "workers-ai"),
    env_vars=("CLOUDFLARE_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_BASE_URL"),
    display_name="Cloudflare Workers AI",
    description="Cloudflare Workers AI — serverless GPU inference (account-scoped base URL)",
    signup_url="https://dash.cloudflare.com/",
    category="cloud",
    logo="☁️",
    supports_health_check=False,  # requires account-scoped path; probe via configured base URL
    fallback_models=(
        "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "@cf/qwen/qwen3-235b-a22b-instruct",
    ),
    base_url="",
    default_aux_model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
)

register_provider(cloudflare)
