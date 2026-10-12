"""Tests for aetheros_comm.protocol — protocol version negotiation."""

from __future__ import annotations

import pytest

from aetheros_comm.protocol import (PROTOCOL_VERSION, ProtocolError,
                                    negotiate_protocol, is_supported,
                                    supported_versions)


class TestSupported:
    def test_current_version_supported(self):
        assert is_supported(PROTOCOL_VERSION)

    def test_supported_versions_contains_current(self):
        assert PROTOCOL_VERSION in supported_versions()

    def test_unknown_version_not_supported(self):
        assert not is_supported("99.9")


class TestNegotiate:
    def test_negotiates_common_floor(self):
        assert negotiate_protocol(["1.0", "1.1"], ["1.0"]) == "1.0"

    def test_negotiates_highest_common(self):
        assert negotiate_protocol(["1.0", "1.1"], ["1.1", "1.2"]) == "1.1"

    def test_no_common_version_raises(self):
        with pytest.raises(ProtocolError):
            negotiate_protocol(["2.0"], ["1.0"])

    def test_empty_peer_raises(self):
        with pytest.raises(ProtocolError):
            negotiate_protocol(["1.0"], [])

    def test_peer_fallback_supported(self):
        # peer defaults to the fabric's own version when it sends nothing.
        assert negotiate_protocol(["1.0"], [PROTOCOL_VERSION]) == "1.0"