"""Canonical identity: ids, keys, signatures, expiry (Master 46 section 5)."""

import time

from aetheros_network.identity import (
    AgentIdentity,
    fingerprint_public_key,
    generate_signing_keypair,
    new_agent_id,
    new_instance_id,
    sign_bytes,
    verify_signature,
)


def test_agent_id_shape():
    aid = new_agent_id("acme")
    assert aid.startswith("aetheros:acme:")
    assert len(aid) > len("aetheros:acme:")


def test_instance_ids_unique():
    assert new_instance_id() != new_instance_id()


def test_key_fingerprint_stable():
    keys = generate_signing_keypair()
    fp1 = fingerprint_public_key(keys["public_der"])
    fp2 = fingerprint_public_key(keys["public_der"])
    assert fp1 == fp2
    assert fp1.startswith("sha256:")


def test_sign_verify_roundtrip():
    keys = generate_signing_keypair()
    payload = b"agent-card-bytes"
    sig = sign_bytes(keys["private_der"], payload)
    assert verify_signature(keys["public_der"], sig, payload) is True
    assert verify_signature(keys["public_der"], sig, b"tampered") is False


def test_verify_wrong_key_fails():
    a = generate_signing_keypair()
    b = generate_signing_keypair()
    sig = sign_bytes(a["private_der"], b"hello")
    assert verify_signature(b["public_der"], sig, b"hello") is False


def test_identity_validate_ok():
    ident = AgentIdentity(agent_id=new_agent_id(), canonical_name="x")
    assert ident.validate() == []


def test_identity_rejects_bad_id():
    ident = AgentIdentity(agent_id="not a valid id!!")
    assert ident.validate() != []


def test_identity_expiry_and_revocation():
    ident = AgentIdentity(agent_id=new_agent_id(), created_at=time.time() - 100,
                          expires_at=time.time() - 1)
    assert ident.is_expired is True
    assert ident.effective_status == "expired"
    ident2 = AgentIdentity(agent_id=new_agent_id(), revocation_status="revoked")
    assert ident2.effective_status == "revoked"


def test_audit_key_stable():
    keys = generate_signing_keypair()
    ident = AgentIdentity(agent_id=new_agent_id(),
                          public_keys=[fingerprint_public_key(keys["public_der"])])
    assert ident.audit_key().startswith(ident.agent_id)
