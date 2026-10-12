"""Tests for aetheros_integrations.auth — OAuth2, PKCE, device flow, JWT."""

import base64
import hashlib

import httpx
import pytest

from aetheros_integrations.auth import AuthEngine, AuthError, OAuth2ClientConfig


def _token_body(**overrides):
    body = {
        "access_token": "acc-token-1",
        "refresh_token": "ref-token-1",
        "token_type": "Bearer",
        "scope": "read write",
        "expires_in": 3600,
    }
    body.update(overrides)
    return body


class _MockTransport(httpx.MockTransport):
    def __init__(self, responses):
        self._responses = responses
        self._index = 0
        self.last_body = None
        super().__init__(self._handle)

    def _handle(self, request):
        self.last_body = request.read() if request.content else None
        if self._index < len(self._responses):
            resp = self._responses[self._index]
            self._index += 1
            return resp
        return httpx.Response(500, json={"error": "no more responses"})


@pytest.fixture
def vault_and_settings(tmp_path):
    from aetheros_integrations.config import IntegrationsSettings
    from aetheros_integrations.security import CredentialVault

    settings = IntegrationsSettings(data_dir="integrations")
    vault = CredentialVault(settings, dirpath=tmp_path)
    return vault, settings


@pytest.fixture
def oauth_config():
    return OAuth2ClientConfig(
        client_id="client-123",
        client_secret="secret-456",
        redirect_uri="http://localhost/callback",
        auth_endpoint="https://idp.example.com/authorize",
        token_endpoint="https://idp.example.com/token",
        device_endpoint="https://idp.example.com/device",
        scopes=["read", "write"],
        use_pkce=True,
    )


class TestSimpleCredentials:
    def test_store_api_key_roundtrip(self, vault_and_settings):
        vault, settings = vault_and_settings
        auth = AuthEngine(vault=vault, settings=settings)
        cid = auth.store_api_key("github", "abc123")
        assert auth.auth_header(cid) == {"Authorization": "Bearer abc123"}
        auth.close()

    def test_store_pat(self, vault_and_settings):
        vault, settings = vault_and_settings
        auth = AuthEngine(vault=vault, settings=settings)
        cid = auth.store_pat("github", "ghp_x")
        assert auth.auth_header(cid)["Authorization"].endswith("ghp_x")
        auth.close()


class TestOAuth2PKCE:
    def test_start_returns_url_and_exchange(self, vault_and_settings, oauth_config):
        vault, settings = vault_and_settings
        auth = AuthEngine(vault=vault, settings=settings)
        transport = _MockTransport([httpx.Response(200, json=_token_body())])
        auth._http = httpx.Client(transport=transport, timeout=5.0)

        started = auth.start_authorization_code("github", oauth_config)
        assert "state=" in started["url"]
        assert "code_challenge=" in started["url"]
        assert "code_challenge_method=S256" in started["url"]

        token = auth.exchange_authorization_code("github", oauth_config, "auth-code", started["state"])
        assert token.access_token == "acc-token-1"
        assert token.refresh_token == "ref-token-1"
        assert token.scope == ["read", "write"]
        auth.close()

    def test_exchange_requires_started_flow(self, vault_and_settings, oauth_config):
        vault, settings = vault_and_settings
        auth = AuthEngine(vault=vault, settings=settings)
        with pytest.raises(AuthError):
            auth.exchange_authorization_code("github", oauth_config, "code", "unknown-state")
        auth.close()

    def test_pkce_verifier_sent_in_exchange(self, vault_and_settings, oauth_config):
        vault, settings = vault_and_settings
        auth = AuthEngine(vault=vault, settings=settings)
        transport = _MockTransport([httpx.Response(200, json=_token_body())])
        auth._http = httpx.Client(transport=transport, timeout=5.0)
        started = auth.start_authorization_code("github", oauth_config)
        auth.exchange_authorization_code("github", oauth_config, "code", started["state"])
        # verifier must be S256-consistent with the challenge in the auth URL
        import urllib.parse

        query = urllib.parse.parse_qs(started["url"].split("?", 1)[1])
        challenge = query["code_challenge"][0]
        data = urllib.parse.parse_qs(transport.last_body.decode())
        verifier = data["code_verifier"][0]
        recomputed = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        assert recomputed == challenge
        auth.close()


class TestClientCredentials:
    def test_exchange(self, vault_and_settings, oauth_config):
        vault, settings = vault_and_settings
        auth = AuthEngine(vault=vault, settings=settings)
        transport = _MockTransport([httpx.Response(200, json=_token_body(access_token="cc-token"))])
        auth._http = httpx.Client(transport=transport, timeout=5.0)
        oauth_config.use_pkce = False
        token = auth.client_credentials("github", oauth_config)
        assert token.access_token == "cc-token"
        auth.close()

    def test_token_endpoint_error_raises(self, vault_and_settings, oauth_config):
        vault, settings = vault_and_settings
        auth = AuthEngine(vault=vault, settings=settings)
        transport = _MockTransport([httpx.Response(401, json={"error": "invalid_client"})])
        auth._http = httpx.Client(transport=transport, timeout=5.0)
        oauth_config.use_pkce = False
        with pytest.raises(AuthError):
            auth.client_credentials("github", oauth_config)
        auth.close()


class TestDeviceFlow:
    def test_full_flow(self, vault_and_settings, oauth_config):
        vault, settings = vault_and_settings
        auth = AuthEngine(vault=vault, settings=settings)
        device_start = httpx.Response(
            200,
            json={"device_code": "dev-code", "user_code": "ABCD-1234", "verification_uri": "https://idp.example.com/device", "expires_in": 1800, "interval": 5},
        )
        poll_pending = httpx.Response(400, json={"error": "authorization_pending"})
        poll_success = httpx.Response(200, json=_token_body(access_token="device-token"))
        transport = _MockTransport([device_start, poll_pending, poll_success])
        auth._http = httpx.Client(transport=transport, timeout=5.0)

        started = auth.start_device_flow("github", oauth_config)
        assert started["device_code"] == "dev-code"
        assert started["user_code"] == "ABCD-1234"

        # first poll -> pending, returns None
        assert auth.poll_device_flow(started["flow_id"], oauth_config) is None
        # second poll -> token
        token = auth.poll_device_flow(started["flow_id"], oauth_config)
        assert token.access_token == "device-token"
        auth.close()


class TestJWT:
    def test_sign_and_verify_hs256(self, vault_and_settings):
        vault, settings = vault_and_settings
        auth = AuthEngine(vault=vault, settings=settings)
        token = auth.sign_jwt({"sub": "user-1", "role": "admin"}, secret="test-secret", expires_in=600)
        payload = auth.verify_jwt(token, secret="test-secret")
        assert payload["sub"] == "user-1"
        assert payload["role"] == "admin"
        assert payload["exp"] > payload["iat"]
        auth.close()

    def test_wrong_secret_fails(self, vault_and_settings):
        vault, settings = vault_and_settings
        auth = AuthEngine(vault=vault, settings=settings)
        token = auth.sign_jwt({"sub": "user-1"}, secret="correct", expires_in=600)
        import jwt as pyjwt

        with pytest.raises(pyjwt.InvalidSignatureError):
            auth.verify_jwt(token, secret="wrong")
        auth.close()

    def test_expired_token_rejected(self, vault_and_settings):
        vault, settings = vault_and_settings
        auth = AuthEngine(vault=vault, settings=settings)
        token = auth.sign_jwt({"sub": "x"}, secret="s", expires_in=-10)
        import jwt as pyjwt

        with pytest.raises(pyjwt.ExpiredSignatureError):
            auth.verify_jwt(token, secret="s")
        auth.close()


class TestRefresh:
    def test_refresh(self, vault_and_settings, oauth_config):
        vault, settings = vault_and_settings
        auth = AuthEngine(vault=vault, settings=settings)
        transport = _MockTransport([httpx.Response(200, json=_token_body(access_token="refreshed"))])
        auth._http = httpx.Client(transport=transport, timeout=5.0)
        oauth_config.use_pkce = False
        token = auth.refresh("github", oauth_config, "old-refresh-token")
        assert token.access_token == "refreshed"
        auth.close()
