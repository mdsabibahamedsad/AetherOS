"""Tests for provider health capabilities (``aetheros_cli/provider_health.py``).

``provider_capabilities`` builds a declarative capability summary from a
provider profile. ``probe_provider_health`` never raises and reports
unknown providers / missing keys gracefully.
"""

from aetheros_cli.provider_health import provider_capabilities, probe_provider_health


def test_provider_capabilities_unknown_returns_none():
    assert provider_capabilities("this-provider-does-not-exist") is None


def test_provider_capabilities_includes_new_fields():
    caps = provider_capabilities("groq")
    assert caps is not None
    assert caps["name"] == "groq"
    assert caps["category"] == "cloud"
    assert caps["supports_streaming"] is True
    assert caps["supports_health_check"] is True
    assert caps["logo"]
    assert "GROQ_API_KEY" in caps["env_vars"]


def test_probe_unknown_provider():
    result = probe_provider_health("does-not-exist")
    assert result["online"] is False
    assert result["error"] == "unknown_provider"


def test_probe_health_check_disabled_provider():
    result = probe_provider_health("cloudflare")
    assert result["provider"] == "cloudflare"
    assert result["online"] is False
    assert result["error"] == "health_check_disabled"


def test_probe_missing_key_reports_unconfigured():
    result = probe_provider_health("groq")
    assert result["provider"] == "groq"
    assert result["configured"] is False
    assert result["error"] == "no_api_key"
