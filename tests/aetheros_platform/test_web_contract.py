"""Tests for web/server contracts (Master 69)."""

import pytest

from aetheros_platform.web_contract import (
    Page,
    cors_origin_allowed,
    make_error,
    validate_security_headers,
    validate_server_config,
)


def test_error_catalog_and_leak_guard():
    e = make_error("not_found", "No such task.", request_id="r1")
    assert e.http_status == 404 and not e.retryable
    r = make_error("rate_limited", "Slow down.", retry_after=30)
    assert r.retryable and r.retry_after == 30
    with pytest.raises(ValueError):
        make_error("nope", "x")
    with pytest.raises(ValueError):
        make_error("failed", 'Traceback File "x" boom')
    with pytest.raises(ValueError):
        make_error("failed", "key sk-live-secret here")


def test_security_headers_contract():
    ok, _ = validate_security_headers({
        "Content-Security-Policy": "x", "Strict-Transport-Security": "x",
        "X-Content-Type-Options": "x", "Referrer-Policy": "x",
        "Permissions-Policy": "x"})
    assert ok
    ok, missing = validate_security_headers({})
    assert not ok and len(missing) == 5


def test_cors_allowlist_no_wildcard_bypass():
    allow = ["https://app.example.com"]
    assert cors_origin_allowed("https://app.example.com", allow)
    assert not cors_origin_allowed("https://evil.com", allow)
    assert not cors_origin_allowed("https://app.example.com.evil.com", allow)
    assert cors_origin_allowed("https://a.example.com", ["*.example.com"])
    assert not cors_origin_allowed("https://example.com.evil.com", ["*.example.com"])


def test_pagination_bounded():
    assert Page(items=(), limit=50).limit == 50
    with pytest.raises(ValueError):
        Page(items=(), limit=0)
    with pytest.raises(ValueError):
        Page(items=(), limit=5000)


def test_config_validator():
    good = {"api_base_url": "https://api.example.com",
            "allowed_origins": ["https://app.example.com"],
            "auth_mode": "session"}
    assert validate_server_config(good)[0]
    bad = {"api_base_url": "", "allowed_origins": ["*"], "auth_mode": "x"}
    ok, problems = validate_server_config(bad)
    assert not ok and len(problems) >= 3
    # loopback dev exception documented, not a bypass
    dev = dict(good, allowed_origins=["http://localhost"])
    assert validate_server_config(dev)[0]
