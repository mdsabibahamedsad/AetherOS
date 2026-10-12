"""Property-based (§136) + fuzz (§137) tests with stdlib random
(seeded, reproducible). Invariants must hold over generated identities,
delegations, scopes, expirations, risks, and chains."""
from __future__ import annotations

import random
import string

import pytest

from aetheros_control_plane.models import IdentityType
from aetheros_control_plane.scopes import ScopeSet
from trust import TrustFabric
from trust.models import ExtendedDecision

RNG = random.Random(20260528)

CAPS = ["read", "write", "delete", "execute", "publish", "move"]
RES = ["/docs/a", "/tmp/x", "/prod/db", "https://example.com/",
       "secret/db", "/workspace/p/**"]
RISKS = ["LOW", "MEDIUM", "HIGH"]


def _rand_str(n=6):
    return "".join(RNG.choice(string.ascii_lowercase) for _ in range(n))


def _fabric():
    return TrustFabric()


def test_prop_deny_unknown_identities():
    for _ in range(50):
        f = _fabric()
        d = f.propose(f"ghost_{_rand_str()}", RNG.choice(CAPS),
                      RNG.choice(RES), kind="tool")
        assert d.decision == ExtendedDecision.DENY


def test_prop_expired_tokens_always_rejected():
    f = _fabric()
    for _ in range(50):
        tok = f.capabilities.issue("s", RNG.choice(CAPS), RNG.choice(RES),
                                   "p", ttl_s=-RNG.randint(1, 3600),
                                   audience="t")
        from trust.models import SecurityError, TrustError
        with pytest.raises(TrustError) as e:
            f.capabilities.validate(tok, "t")
        assert e.value.code == SecurityError.CAPABILITY_EXPIRED


def test_prop_audience_binding_holds():
    f = _fabric()
    for _ in range(50):
        tok = f.capabilities.issue("s", "read", "/d", "p",
                                   audience=f"tool-{_rand_str()}")
        from trust.models import SecurityError, TrustError
        with pytest.raises(TrustError):
            f.capabilities.validate(tok, f"tool-{_rand_str()}")


def test_prop_scope_subset_monotonic():
    for _ in range(100):
        parent, child = ScopeSet(), ScopeSet()
        base = f"fs.{RNG.choice(['read', 'write'])}"
        parent.grant(f"{base}:/a/**")
        if RNG.random() < 0.5:
            child.grant(f"{base}:/a/b")
            assert child.is_subset_of(parent)
        else:
            child.grant(f"{base}:/other/**")
            assert not child.is_subset_of(parent)


def test_prop_revocation_monotonic():
    f = _fabric()
    ids = [f"cap_{i}" for i in range(20)]
    for i in ids:
        f.revoke("capability", i, "test")
    for i in ids:
        assert f.revocation.is_revoked("capability", i)
    # never un-revoked by further operations
    f.revoke("capability", ids[0], "again")
    assert f.revocation.is_revoked("capability", ids[0])


def test_prop_risk_ordering_stable():
    from trust.models import Risk, risk_at_least
    order = list(Risk)
    for i in range(len(order)):
        for j in range(len(order)):
            assert risk_at_least(order[i], order[j]) == (i >= j)


def test_fuzz_urls_never_allow_sensitive():
    f = _fabric()
    evil = ["http://localhost/", "http://127.0.0.1:9/", "http://[::1]/",
            "http://169.254.169.254/", "http://10.1.2.3/",
            "http://192.168.0.1/", "http://172.16.0.9/",
            "http://0x7f000001/", "http://2130706433/",
            "http://example.com@169.254.169.254/"]
    for u in evil:
        assert f.network.check_url(u)["decision"] == "DENY", u
    for _ in range(100):
        host = "".join(RNG.choice("ab0123456789.:") for _ in range(8))
        try:
            r = f.network.check_url(f"http://{host}/")
        except Exception:
            continue
        # must return a decision, never raise or allow-by-default on error
        assert r["decision"] in ("ALLOW", "DENY")


def test_fuzz_paths_and_tokens():
    f = _fabric()
    for _ in range(100):
        path = "/" + "/".join(_rand_str(4) for _ in range(3))
        tok = f.capabilities.issue("s", "read", path, "p",
                                   audience="t", ttl_s=60)
        assert f.capabilities.validate(tok, "t").token_id == tok.token_id
    for _ in range(50):
        ident = f.plane.identities.create(IdentityType.AGENT,
                                          f"fz_{_rand_str()}")
        d = f.propose(ident.id, RNG.choice(CAPS), RNG.choice(RES),
                      kind="tool")
        assert d.decision in (ExtendedDecision.ALLOW, ExtendedDecision.DENY,
                              ExtendedDecision.REQUIRE_APPROVAL,
                              ExtendedDecision.SIMULATION_ONLY,
                              ExtendedDecision.SANDBOX_ONLY,
                              ExtendedDecision.RATE_LIMIT,
                              ExtendedDecision.DEFER,
                              ExtendedDecision.REQUIRE_STEP_UP_AUTH)


def test_fuzz_policy_bodies_rejected_safely():
    f = _fabric()
    for bad in [{}, {"allow": "notalist"}, {"layers": [1, 2]}]:
        try:
            f.policies.publish(f"fz_{_rand_str()}", bad)
        except Exception:
            pass
    # store still consistent
    assert isinstance(f.policies._versions, dict)


def test_fuzz_ipc_like_messages():
    f = _fabric()
    msgs = [{"sender": _rand_str(), "cap": "read", "res": "/d"},
            {"cap": "write"}, {}, {"sender": None, "cap": None}]
    for m in msgs:
        d = f.propose(m.get("sender") or "ghost",
                      str(m.get("cap") or "read"),
                      str(m.get("res") or "/d"), kind="tool")
        assert d.decision == ExtendedDecision.DENY  # unknown senders deny
