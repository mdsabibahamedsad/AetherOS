"""Transport unit tests (offline) + discovery parsing (sections 68-70, 132)."""

import json

import pytest

from aetheros_network.discovery import import_card_file
from aetheros_network.transport import (
    A2ATransport,
    TransportConfig,
    TransportError,
    _parse_sse,
)


def test_http_blocked_by_default():
    with pytest.raises(TransportError, match="insecure"):
        A2ATransport("http://lan.local:8765", TransportConfig())


def test_unsupported_scheme_rejected():
    with pytest.raises(TransportError, match="unsupported scheme"):
        A2ATransport("ftp://example.com/", TransportConfig())


def test_no_silent_redirects_configured():
    # Defense documented in code: httpx follow_redirects=False. Assert the
    # source still carries that invariant.
    src = open("aetheros_network/transport.py", encoding="utf-8").read()
    assert "follow_redirects=False" in src


def test_sse_json_event_parsed():
    ev = _parse_sse('data: {"type": "progress", "pct": 50}')
    assert ev == {"type": "progress", "pct": 50}


def test_sse_done_parsed():
    assert _parse_sse("data: [DONE]") == {"type": "done"}


def test_sse_text_fallback():
    ev = _parse_sse("data: hello world")
    assert ev["text"] == "hello world"


def test_sse_ignores_comments():
    assert _parse_sse(": keep-alive") is None


def test_import_card_file(tmp_path):
    card = {"protocolVersion": "1.0", "name": "Manual", "version": "1.0",
            "url": "https://manual.example.com/"}
    p = tmp_path / "card.json"
    p.write_text(json.dumps(card))
    res = import_card_file(p)
    assert res.errors == []
    assert res.source == "manual"
    assert res.identity["trust_level"] == "discovered"


def test_import_card_file_bad_json(tmp_path):
    p = tmp_path / "card.json"
    p.write_text("{not json")
    res = import_card_file(p)
    assert res.errors != []


def test_discovery_result_is_untrusted_by_default(tmp_path):
    card = {"protocolVersion": "1.0", "name": "X", "version": "1.0",
            "url": "https://x.example.com/"}
    p = tmp_path / "card.json"
    p.write_text(json.dumps(card))
    res = import_card_file(p)
    assert res.identity["trust_level"] in ("discovered", "unknown")
