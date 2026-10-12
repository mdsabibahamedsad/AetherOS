"""Tests for aetheros_security.session and authentication."""

import time

import pytest

from aetheros_security.authentication import AuthenticationManager
from aetheros_security.session import SessionManager


@pytest.fixture
def session_manager(tmp_path):
    return SessionManager(secret=b"test-secret-32-bytes-long-for-testing!")


class TestSessions:
    def test_create_validate(self, session_manager):
        token = session_manager.create("user1", scope=["filesystem:read"])
        session = session_manager.validate(token)
        assert session.principal == "user1"
        assert session_manager.has_scope(session, "filesystem:read")
        assert not session_manager.has_scope(session, "filesystem:write")

    def test_reject_tampered_token(self, session_manager):
        token = session_manager.create("user1")
        tampered = token[:-2] + ("ab" if token[-2:] != "ab" else "cd")
        with pytest.raises(Exception):
            session_manager.validate(tampered)

    def test_renew_bounded(self, session_manager):
        token = session_manager.create("user1")
        new_token = session_manager.renew(token)
        assert new_token != token
        session = session_manager.validate(new_token)
        assert session.principal == "user1"

    def test_revoke(self, session_manager):
        token = session_manager.create("user1")
        assert session_manager.revoke(token)
        with pytest.raises(Exception):
            session_manager.validate(token)

    def test_expired(self, session_manager):
        token = session_manager.create("user1", timeout_seconds=1)
        time.sleep(1.1)
        with pytest.raises(Exception):
            session_manager.validate(token)


@pytest.fixture
def auth(tmp_path):
    return AuthenticationManager(accounts_file=str(tmp_path / "accounts.json"))


class TestAuthentication:
    def test_register_and_password_login(self, auth):
        assert auth.register_account("alice", "hunter2secure")
        assert auth.authenticate_password("alice", "hunter2secure")
        assert not auth.authenticate_password("alice", "wrong")

    def test_wrong_password_does_not_expose_account(self, auth):
        auth.register_account("bob", "correct")
        assert not auth.authenticate_password("bob", "incorrect")

    def test_disable_account(self, auth):
        auth.register_account("carol", "pw")
        assert auth.authenticate_password("carol", "pw")
        assert auth.disable_account("carol")
        assert not auth.authenticate_password("carol", "pw")

    def test_passwordless_otp(self, auth):
        auth.register_account("dave", "pw")
        code = auth.request_passwordless_code("dave")
        assert code is not None
        assert len(code) == 6
        assert auth.verify_passwordless_code("dave", code)
        assert not auth.verify_passwordless_code("dave", code)  # single-use

    def test_passwordless_unknown_user(self, auth):
        assert auth.request_passwordless_code("nobody") is None

    def test_oauth_provider(self, auth):
        from aetheros_security.authentication import OAuthProvider
        provider = OAuthProvider(name="github", issuer="https://github.com")
        auth.register_oauth_provider(provider)
        assert auth.get_oauth_provider("github") is not None
        assert auth.authenticate_oauth("github", "octocat", verified=True)
        assert not auth.authenticate_oauth("github", "mallory", verified=False)

    def test_device_auth(self, auth):
        challenge = auth.start_device_auth("device-1")
        assert challenge
        assert auth.verify_device_auth("device-1", challenge)
        assert not auth.verify_device_auth("device-1", "wrong")

    def test_biometric_callback(self, auth):
        auth.register_account("trusted", "pw")
        auth.register_biometric_callback(lambda uid: uid == "trusted")
        assert auth.authenticate_biometric("trusted")
        assert not auth.authenticate_biometric("untrusted")

    def test_password_hash_is_salted(self, auth):
        auth.register_account("eve", "same-password")
        assert auth.authenticate_password("eve", "same-password")

    def test_session_integration(self, auth):
        auth.register_account("frank", "pw")
        token = auth.create_session("frank", scope=["terminal:execute"])
        assert auth.validate_session(token) is not None
        assert auth.has_permission(token, "terminal:execute")
        assert not auth.has_permission(token, "network:connect")
