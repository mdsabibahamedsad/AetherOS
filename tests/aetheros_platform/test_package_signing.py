"""Ed25519 package signing roundtrip (Master 62 §56, §104).

Proves verify_signature enforces real cryptography: valid signatures pass,
tampered packages and wrong keys raise SignatureError. Previously the
ed25519 path was a `pass -> return True` stub (blind trust).
"""

import pytest


def _keys():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    priv = ed25519.Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH,
        serialization.NoEncryption()).decode()
    pub_hex = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    return priv_pem, pub_hex


def _packed(tmp_path):
    from sdk.packaging import pack_plugin
    src = tmp_path / "plug"
    src.mkdir()
    (src / "manifest.yaml").write_text(
        "name: test-plugin\nversion: 1.0.0\n", encoding="utf-8")
    (src / "__init__.py").write_text(
        "def register(ctx): pass\n", encoding="utf-8")
    return pack_plugin(src, output_path=tmp_path / "test.aep")


def test_ed25519_sign_verify_roundtrip(tmp_path):
    from sdk.signing import PublisherKey, sign_package, verify_signature
    priv_pem, pub_hex = _keys()
    pkg = _packed(tmp_path)
    sig = sign_package(pkg, priv_pem, "k1")
    assert isinstance(sig, str) and len(sig) == 128  # 64-byte ed25519 hex
    assert verify_signature(pkg, PublisherKey("k1", pub_hex)) is True


def test_tampered_package_rejected(tmp_path):
    from sdk.signing import (PublisherKey, SignatureError, sign_package,
                             verify_signature)
    priv_pem, pub_hex = _keys()
    pkg = _packed(tmp_path)
    sign_package(pkg, priv_pem, "k1")
    with open(pkg.package_path, "r+b") as fh:
        fh.seek(10)
        byte = fh.read(1)
        fh.seek(10)
        fh.write(bytes([byte[0] ^ 1]))
    with pytest.raises(SignatureError):
        verify_signature(pkg, PublisherKey("k1", pub_hex))


def test_wrong_key_rejected(tmp_path):
    from sdk.signing import (PublisherKey, SignatureError, sign_package,
                             verify_signature)
    priv_pem, _ = _keys()
    _, other_pub = _keys()
    pkg = _packed(tmp_path)
    sign_package(pkg, priv_pem, "k1")
    with pytest.raises(SignatureError):
        verify_signature(pkg, PublisherKey("k1", other_pub))


def test_missing_signature_rejected(tmp_path):
    from sdk.signing import PublisherKey, SignatureError, verify_signature
    _, pub_hex = _keys()
    pkg = _packed(tmp_path)
    with pytest.raises(SignatureError):
        verify_signature(pkg, PublisherKey("k1", pub_hex))
