"""Google Vertex AI provider profile.

Vertex AI exposes an OpenAI-compatible endpoint whose base URL is scoped by
GCP region and project::

    https://{REGION}-aiplatform.googleapis.com/v1beta1/openai

Configure it by setting ``VERTEX_AI_BASE_URL`` (or via
``aetheros providers set google-vertex-ai --base-url <url>``) and an access
token as ``VERTEX_AI_API_KEY``. Health checks are disabled because the base
URL is user-supplied and there is no public ``/models`` catalog.
"""

from providers import register_provider
from providers.base import ProviderProfile

google_vertex_ai = ProviderProfile(
    name="google-vertex-ai",
    aliases=("vertex-ai", "vertex", "vertex_ai"),
    env_vars=("VERTEX_AI_API_KEY", "VERTEX_AI_BASE_URL"),
    display_name="Google Vertex AI",
    description="Google Vertex AI — OpenAI-compatible endpoint (region/project-scoped base URL)",
    signup_url="https://console.cloud.google.com/vertex-ai",
    category="cloud",
    logo="🟢",
    supports_health_check=False,
    fallback_models=(
        "gemini-2.5-pro",
        "gemini-2.5-flash",
    ),
    base_url="",
    default_aux_model="gemini-2.5-flash",
)

register_provider(google_vertex_ai)
