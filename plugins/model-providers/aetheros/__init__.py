"""AetherOS provider profile."""

from typing import Any

from agent.aetheros_portal_tags import aetheros_portal_tags
from providers import register_provider
from providers.base import ProviderProfile


class AetherOSProfile(ProviderProfile):
    """AetherOS — product tags, reasoning with AetherOS-specific omission."""

    def build_extra_body(
        self, *, session_id: str | None = None, **context
    ) -> dict[str, Any]:
        return {"tags": aetheros_portal_tags()}

    def build_api_kwargs_extras(
        self,
        *,
        reasoning_config: dict | None = None,
        supports_reasoning: bool = False,
        **context,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """AetherOS: passes full reasoning_config, but OMITS when disabled."""
        extra_body = {}
        if supports_reasoning:
            if reasoning_config is not None:
                rc = dict(reasoning_config)
                if rc.get("enabled") is False:
                    pass  # AetherOS omits reasoning when disabled
                else:
                    extra_body["reasoning"] = rc
            else:
                extra_body["reasoning"] = {"enabled": True, "effort": "medium"}
        return extra_body, {}


aetheros = AetherOSProfile(
    name="aetheros",
    aliases=("nous", "nous-portal", "aetheros"),
    env_vars=("NOUS_API_KEY",),
    display_name="AetherOS",
    description="AetherOS — Aetheros model family",
    signup_url="https://aetheros.com/",
    fallback_models=(
        "aetheros-3-405b",
        "aetheros-3-70b",
    ),
    base_url="https://inference.aetheros.com/v1",
    auth_type="oauth_device_code",
)

# Backward-compat alias for the legacy object name.
nous = aetheros

register_provider(aetheros)
