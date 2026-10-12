"""Tests for aetheros_integrations.webhooks — signing, verification, dedup, replay."""

import json

import httpx
import pytest

from aetheros_integrations.webhooks import WebhookEngine, sign_payload, verify_signature


@pytest.fixture
def settings():
    from aetheros_integrations.config import IntegrationsSettings

    return IntegrationsSettings(data_dir="integrations")


@pytest.fixture
def engine(tmp_path, settings):
    eng = WebhookEngine(settings, dirpath=tmp_path)
    yield eng
    eng.close()


class TestSignatures:
    def test_sign_and_verify_roundtrip(self):
        body = b'{"a": 1}'
        sig = sign_payload("secret", body)
        assert verify_signature("secret", body, sig) is True

    def test_wrong_secret_fails(self):
        body = b'{"a": 1}'
        sig = sign_payload("secret", body)
        assert verify_signature("wrong", body, sig) is False

    def test_empty_signature_fails(self):
        assert verify_signature("secret", b"{}", "") is False


class TestOutgoing:
    def test_deliver_success(self, engine, settings):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200)

        engine._http = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)
        delivery = engine.deliver("https://dest.example.com/hook", {"kind": "test"}, event="test.event")
        assert delivery.status == "delivered"
        assert delivery.attempts == 1
        assert calls[0].headers["X-AetherOS-Event"] == "test.event"
        assert "X-AetherOS-Signature" in calls[0].headers

    def test_signature_header_matches_body(self, engine):
        captured = {}

        def handler(request):
            captured["body"] = request.read()
            captured["sig"] = request.headers.get("X-AetherOS-Signature", "")
            return httpx.Response(200)

        engine._http = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)
        engine.deliver("https://dest.example.com/hook", {"kind": "test"}, event="e", secret="cfg-secret")
        assert verify_signature("cfg-secret", captured["body"], captured["sig"]) is True

    def test_retry_on_failure_then_success(self, engine, settings):
        engine._settings.webhook.retry_backoff_s = 0.01
        engine._settings.webhook.default_max_attempts = 3
        attempts = []

        def handler(request):
            attempts.append(1)
            if len(attempts) < 2:
                return httpx.Response(500)
            return httpx.Response(200)

        engine._http = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)
        delivery = engine.deliver("https://dest.example.com/hook", {"kind": "t"})
        assert delivery.status == "delivered"
        assert delivery.attempts == 2

    def test_fails_after_max_attempts(self, engine, settings):
        engine._settings.webhook.retry_backoff_s = 0.01
        engine._settings.webhook.default_max_attempts = 3
        attempts = []

        def handler(request):
            attempts.append(1)
            return httpx.Response(503)

        engine._http = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)
        delivery = engine.deliver("https://dest.example.com/hook", {"kind": "t"})
        assert delivery.status == "failed"
        assert delivery.attempts == 3

    def test_network_error_fails(self, engine, settings):
        engine._settings.webhook.retry_backoff_s = 0.01
        engine._settings.webhook.default_max_attempts = 2

        def handler(request):
            raise httpx.ConnectError("refused")

        engine._http = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)
        delivery = engine.deliver("https://dest.example.com/hook", {"kind": "t"})
        assert delivery.status == "failed"
        assert delivery.last_error

    def test_duplicate_delivery_deduped(self, engine):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200)

        engine._http = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)
        first = engine.deliver("https://dest.example.com/hook", {"kind": "t"}, event="e")
        second = engine.deliver("https://dest.example.com/hook", {"kind": "t"}, event="e")
        assert first.status == "delivered"
        assert second.status == "rejected"
        assert "duplicate" in second.last_error
        assert len(calls) == 1

    def test_replay(self, engine):
        def handler(request):
            return httpx.Response(200)

        engine._http = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)
        original = engine.deliver("https://dest.example.com/hook", {"kind": "t"}, event="e")
        replayed = engine.replay(original.id, "https://dest.example.com/hook")
        assert replayed.status == "delivered"
        assert replayed.payload["kind"] == "t"
        assert replayed.payload["_replay_of"] == original.id

    def test_history_and_stats(self, engine):
        def handler(request):
            return httpx.Response(200)

        engine._http = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)
        engine.deliver("https://dest.example.com/hook", {"kind": "a"}, event="e1", integration_id="i1")
        engine.deliver("https://dest.example.com/hook", {"kind": "b"}, event="e2", integration_id="i2")
        assert len(engine.history()) == 2
        assert len(engine.history(integration_id="i1")) == 1
        stats = engine.stats()
        assert stats["total"] == 2
        assert stats["delivered"] == 2


class TestIncoming:
    def test_valid_signature_delivers(self, engine):
        received = []

        def handler(payload, delivery):
            received.append(payload)

        engine.register_handler(handler)
        body = json.dumps({"event": "push"}).encode()
        sig = sign_payload(engine.secret, body)
        delivery = engine.handle_incoming(body, signature=sig, event="push")
        assert delivery.status == "delivered"
        assert delivery.signature_valid is True
        assert received == [{"event": "push"}]

    def test_bad_signature_rejected(self, engine):
        body = b'{"event": "push"}'
        sig = sign_payload("attacker-secret", body)
        delivery = engine.handle_incoming(body, signature=sig, event="push")
        assert delivery.status == "rejected"
        assert delivery.signature_valid is False
        assert "signature" in delivery.last_error

    def test_hop_limit_exceeded_rejected(self, engine, settings):
        settings.webhook.max_hops = 3
        body = b'{"event": "push"}'
        sig = sign_payload(engine.secret, body)
        delivery = engine.handle_incoming(body, signature=sig, event="push", headers={"X-AetherOS-Hops": "4"})
        assert delivery.status == "rejected"
        assert "hop" in delivery.last_error

    def test_duplicate_incoming_rejected(self, engine):
        body = b'{"event": "push"}'
        sig = sign_payload(engine.secret, body)
        first = engine.handle_incoming(body, signature=sig, event="push")
        second = engine.handle_incoming(body, signature=sig, event="push")
        assert first.status == "delivered"
        assert second.status == "rejected"
        assert "duplicate" in second.last_error
