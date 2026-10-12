"""Tests for aetheros_security.tokens module."""

import time

import pytest

from aetheros_security.tokens import TokenError, TokenManager, get_token_manager


def test_token_creation_and_validation():
    """Test basic token creation and validation."""
    manager = TokenManager()
    
    # Create a token
    token = manager.create(
        principal="user:alice",
        typ="bearer",
        scp=["filesystem:read"],
        expires_in=3600,
    )
    
    # Validate the token
    payload = manager.validate(token)
    assert payload.sub == "user:alice"
    assert payload.typ == "bearer"
    assert "filesystem:read" in payload.scp
    assert payload.iat > 0
    assert payload.exp > payload.iat


def test_token_expiry():
    """Test token expiration."""
    manager = TokenManager()
    
    # Create an expired token (expires in the past)
    token = manager.create(
        principal="user:alice",
        typ="bearer",
        expires_in=-1,  # Expired 1 second ago
    )
    
    # Validation should fail
    with pytest.raises(TokenError, match="Token expired"):
        manager.validate(token)


def test_token_rotation():
    """Test token rotation."""
    manager = TokenManager()
    
    # Create a token
    original_token = manager.create(
        principal="user:alice",
        typ="bearer",
        scp=["filesystem:read"],
        expires_in=3600,
    )
    
    # Rotate the token
    new_token = manager.rotate(original_token)
    
    # Original token should now be invalid (revoked)
    with pytest.raises(TokenError, match="Token revoked"):
        manager.validate(original_token)
    
    # New token should be valid
    payload = manager.validate(new_token)
    assert payload.sub == "user:alice"
    assert payload.typ == "bearer"
    assert "filesystem:read" in payload.scp
    # Should have a different JTI
    # Note: We can't directly compare JTIs without accessing payload, but rotation creates new token


def test_one_time_token_replay_protection():
    """Test that one-time tokens cannot be replayed."""
    manager = TokenManager()
    
    # Create a one-time token
    token = manager.create(
        principal="user:alice",
        typ="one_time",
        scp=["action:test"],
        one_time=True,
    )
    
    # First validation should succeed
    payload = manager.validate(token)
    assert payload.sub == "user:alice"
    assert payload.typ == "one_time"
    
    # Second validation should fail (replay protection)
    with pytest.raises(TokenError, match="Token replayed"):
        manager.validate(token)


def test_token_manager_get_token_manager_singleton():
    """Test that get_token_manager returns a singleton."""
    mgr1 = get_token_manager()
    mgr2 = get_token_manager()
    assert mgr1 is mgr2


def test_token_manager_stats():
    """Test token manager statistics."""
    manager = TokenManager()
    
    # Create and validate a token
    token = manager.create(
        principal="user:alice",
        typ="bearer",
        expires_in=3600,
    )
    manager.validate(token)
    
    stats = manager.get_stats()
    assert "replay_cache_size" in stats
    assert "revoked_cache_size" in stats
    # For bearer token validation, replay cache should be empty, revoked cache empty
    assert stats["replay_cache_size"] == 0
    assert stats["revoked_cache_size"] == 0