"""AetherOS Integrations — Authentication Engine.

Unified authentication supporting API keys, OAuth2 (authorization code +
PKCE + client credentials), OpenID Connect, JWT (HS256/RS256), PATs, bearer
tokens, refresh tokens, device flow, and secure credential storage through
the encrypted vault. All network calls go through httpx with injectable
transport for testing.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from aetheros_integrations.config import load_integrations_settings
from aetheros_integrations.models import AuthMethod
from aetheros_integrations.security import AuditLog, CredentialVault

logger = logging.getLogger(__name__)


class AuthError(RuntimeError):
    pass


class TokenUnavailableError(AuthError):
    pass


@dataclass
class OAuth2ClientConfig:
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""
    auth_endpoint: str = ""
    token_endpoint: str = ""
    device_endpoint: str = ""
    revocation_endpoint: str = ""
    scopes: List[str] = field(default_factory=list)
    use_pkce: bool = True
    jwks_url: str = ""
    issuer: str = ""
    extra_auth_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenBundle:
    access_token: str = ""
    refresh_token: str = ""
    id_token: str = ""
    token_type: str = "Bearer"
    scope: List[str] = field(default_factory=list)
    expires_in: float = 0.0
    issued_at: float = field(default_factory=time.time)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if not self.expires_in:
            return False
        return time.time() >= self.issued_at + self.expires_in

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "id_token": self.id_token,
            "token_type": self.token_type,
            "scope": self.scope,
            "expires_in": self.expires_in,
            "issued_at": self.issued_at,
        }


def _pkce_pair() -> Dict[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return {"verifier": verifier, "challenge": challenge}


class AuthEngine:
    """Entry point for all authentication flows used by integrations."""

    def __init__(self, vault: Optional[CredentialVault] = None, audit: Optional[AuditLog] = None, settings=None):
        self._settings = settings or load_integrations_settings()
        self._vault = vault or CredentialVault(self._settings)
        self._audit = audit or AuditLog(settings=self._settings)
        self._http = httpx.Client(timeout=30.0)
        self._lock = threading.RLock()
        self._code_verifiers: Dict[str, str] = {}
        self._device_flows: Dict[str, Dict[str, Any]] = {}

    def close(self) -> None:
        self._http.close()

    # ---- API key / PAT / bearer (simple) --------------------------------

    def store_api_key(self, provider_key: str, api_key: str, *, scopes: Optional[List[str]] = None) -> str:
        env = self._vault.store(provider_key, {"api_key": api_key}, kind="api_key", scopes=scopes)
        self._audit.record("credential.created", actor="user", target=provider_key, detail={"kind": "api_key"})
        return env.id

    def store_pat(self, provider_key: str, pat: str, *, scopes: Optional[List[str]] = None) -> str:
        env = self._vault.store(provider_key, {"pat": pat}, kind="pat", scopes=scopes)
        self._audit.record("credential.created", actor="user", target=provider_key, detail={"kind": "pat"})
        return env.id

    def store_bearer(self, provider_key: str, token: str, *, scopes: Optional[List[str]] = None) -> str:
        env = self._vault.store(provider_key, {"bearer": token}, kind="bearer", scopes=scopes)
        self._audit.record("credential.created", actor="user", target=provider_key, detail={"kind": "bearer"})
        return env.id

    def auth_header(self, credential_id: str) -> Dict[str, str]:
        """Resolve the Authorization header for a stored credential."""
        secrets_map = self._vault.decrypt(credential_id)
        if "bearer" in secrets_map:
            return {"Authorization": f"Bearer {secrets_map['bearer']}"}
        if "pat" in secrets_map:
            return {"Authorization": f"Bearer {secrets_map['pat']}"}
        if "api_key" in secrets_map:
            return {"Authorization": f"Bearer {secrets_map['api_key']}"}
        raise AuthError(f"Credential {credential_id} is not a simple bearer-type credential")

    # ---- OAuth2 authorization code + PKCE -------------------------------

    def start_authorization_code(
        self,
        provider_key: str,
        config: OAuth2ClientConfig,
    ) -> Dict[str, str]:
        """Return an authorization URL. For PKCE the verifier is kept in memory."""
        params: Dict[str, Any] = {
            "client_id": config.client_id,
            "response_type": "code",
            "redirect_uri": config.redirect_uri,
            "scope": " ".join(config.scopes),
            "state": secrets.token_urlsafe(16),
        }
        state = params["state"]
        if config.use_pkce:
            pair = _pkce_pair()
            params["code_challenge"] = pair["challenge"]
            params["code_challenge_method"] = "S256"
            with self._lock:
                self._code_verifiers[state] = pair["verifier"]
        params.update(config.extra_auth_params)
        url = config.auth_endpoint + ("&" if "?" in config.auth_endpoint else "?") + urlencode(params)
        return {"url": url, "state": state}

    def exchange_authorization_code(
        self,
        provider_key: str,
        config: OAuth2ClientConfig,
        code: str,
        state: str,
    ) -> TokenBundle:
        data: Dict[str, Any] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.redirect_uri,
            "client_id": config.client_id,
        }
        if config.use_pkce:
            verifier = self._code_verifiers.pop(state, None)
            if not verifier:
                raise AuthError("No PKCE verifier for state — authorization flow was not started")
            data["code_verifier"] = verifier
        else:
            data["client_secret"] = config.client_secret
        return self._token_request(provider_key, config.token_endpoint, data)

    # ---- OAuth2 client credentials --------------------------------------

    def client_credentials(self, provider_key: str, config: OAuth2ClientConfig) -> TokenBundle:
        data = {
            "grant_type": "client_credentials",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "scope": " ".join(config.scopes),
        }
        return self._token_request(provider_key, config.token_endpoint, data)

    # ---- Refresh tokens -------------------------------------------------

    def refresh(self, provider_key: str, config: OAuth2ClientConfig, refresh_token: str, scope: Optional[List[str]] = None) -> TokenBundle:
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        }
        if scope:
            data["scope"] = " ".join(scope)
        return self._token_request(provider_key, config.token_endpoint, data)

    # ---- Device flow ----------------------------------------------------

    def start_device_flow(self, provider_key: str, config: OAuth2ClientConfig) -> Dict[str, Any]:
        data = {"client_id": config.client_id, "scope": " ".join(config.scopes)}
        resp = self._http.post(config.device_endpoint, data=data)
        resp.raise_for_status()
        body = resp.json()
        flow = {
            "device_code": body.get("device_code"),
            "user_code": body.get("user_code"),
            "verification_uri": body.get("verification_uri", body.get("verification_url", "")),
            "expires_in": body.get("expires_in", self._settings.auth.device_poll_interval_s * 10),
            "interval": body.get("interval", 5),
            "provider_key": provider_key,
            "config_client_id": config.client_id,
        }
        flow_id = f"device_{uuid.uuid4().hex[:10]}"
        with self._lock:
            self._device_flows[flow_id] = flow
        return {"flow_id": flow_id, **flow}

    def poll_device_flow(self, flow_id: str, config: OAuth2ClientConfig) -> Optional[TokenBundle]:
        with self._lock:
            flow = self._device_flows.get(flow_id)
        if not flow:
            raise AuthError("Unknown device flow")
        resp = self._http.post(
            config.token_endpoint,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": flow["device_code"],
                "client_id": config.client_id,
            },
        )
        if resp.status_code == 400:
            body = resp.json()
            if body.get("error") in {"authorization_pending", "slow_down"}:
                return None
            if body.get("error") == "expired_token":
                with self._lock:
                    self._device_flows.pop(flow_id, None)
                raise AuthError("Device flow expired")
        resp.raise_for_status()
        with self._lock:
            self._device_flows.pop(flow_id, None)
        return self._parse_token(resp.json())

    # ---- OIDC -----------------------------------------------------------

    def discover_oidc(self, issuer: str) -> Dict[str, Any]:
        url = issuer.rstrip("/") + "/.well-known/openid-configuration"
        resp = self._http.get(url)
        resp.raise_for_status()
        return resp.json()

    def exchange_oidc(self, provider_key: str, issuer: str, config: OAuth2ClientConfig, code: str, state: str) -> TokenBundle:
        metadata = self.discover_oidc(issuer)
        config.token_endpoint = metadata.get("token_endpoint", config.token_endpoint)
        return self.exchange_authorization_code(provider_key, config, code, state)

    # ---- JWT ------------------------------------------------------------

    def sign_jwt(
        self,
        claims: Dict[str, Any],
        *,
        secret: str = "",
        private_key: str = "",
        algorithm: str = "HS256",
        issuer: str = "",
        audience: str = "",
        expires_in: float = 0.0,
    ) -> str:
        import jwt

        now = int(time.time())
        payload: Dict[str, Any] = dict(claims)
        payload["iat"] = now
        payload["nbf"] = now
        payload["exp"] = now + int(expires_in or self._settings.auth.token_ttl_s)
        if issuer:
            payload["iss"] = issuer
        if audience:
            payload["aud"] = audience
        if algorithm.startswith("HS"):
            return jwt.encode(payload, secret or _jwt_default_secret(self._settings), algorithm=algorithm)
        return jwt.encode(payload, private_key, algorithm=algorithm)

    def verify_jwt(self, token: str, *, secret: str = "", algorithms: Optional[List[str]] = None) -> Dict[str, Any]:
        import jwt

        algs = algorithms or ["HS256"]
        key = secret or _jwt_default_secret(self._settings)
        return jwt.decode(token, key, algorithms=algs, options={"verify_exp": True})

    # ---- internal -------------------------------------------------------

    def _token_request(self, provider_key: str, endpoint: str, data: Dict[str, Any]) -> TokenBundle:
        try:
            resp = self._http.post(endpoint, data=data)
        except httpx.HTTPError as exc:
            raise AuthError(f"Token request failed: {exc}") from exc
        if resp.status_code >= 400:
            raise AuthError(f"Token endpoint returned {resp.status_code}: {resp.text[:200]}")
        return self._parse_token(resp.json())

    def _parse_token(self, body: Dict[str, Any]) -> TokenBundle:
        if "access_token" not in body:
            raise AuthError("Token response missing access_token")
        return TokenBundle(
            access_token=body.get("access_token", ""),
            refresh_token=body.get("refresh_token", ""),
            id_token=body.get("id_token", ""),
            token_type=body.get("token_type", "Bearer"),
            scope=[s for s in body.get("scope", "").split() if s],
            expires_in=float(body.get("expires_in", 0) or 0),
            raw=body,
        )


def _jwt_default_secret(settings) -> str:
    key = getattr(settings.auth, "jwt_issuer", "aetheros")
    return hashlib.sha256(key.encode()).hexdigest()
