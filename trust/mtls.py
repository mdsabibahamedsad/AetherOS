"""mTLS for Trust Fabric transport (§51): local CA issuance, server +
client certificates, contexts that REQUIRE peer verification
(TLS 1.2+), hostname/pinning options. Used by `trust serve --tls`.
"""
from __future__ import annotations

import datetime
import ipaddress
import ssl
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class CertPaths:
    ca_cert: Path
    cert: Path
    key: Path


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def issue_ca(common_name: str, out_dir: Path) -> CertPaths:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(_now())
            .not_valid_after(_now() + datetime.timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0),
                           critical=True)
            .add_extension(x509.KeyUsage(
                digital_signature=False, content_commitment=False,
                key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=True, crl_sign=True,
                encipher_only=False, decipher_only=False), critical=True)
            .sign(key, hashes.SHA256()))
    out_dir.mkdir(parents=True, exist_ok=True)
    ca_cert = out_dir / "ca.pem"
    ca_key = out_dir / "ca-key.pem"
    ca_cert.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    ca_key.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()))
    return CertPaths(ca_cert, ca_cert, ca_key)


def issue_cert(ca: CertPaths, common_name: str, sans: List[str],
               out_prefix: Path, server: bool = True) -> CertPaths:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    ca_cert = x509.load_pem_x509_certificate(ca.ca_cert.read_bytes())
    ca_key = serialization.load_pem_private_key(ca.key.read_bytes(),
                                                password=None)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    names = []
    for s in sans:
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(s)))
        except ValueError:
            names.append(x509.DNSName(s))
    builder = (x509.CertificateBuilder()
               .subject_name(x509.Name([x509.NameAttribute(
                   NameOID.COMMON_NAME, common_name)]))
               .issuer_name(ca_cert.subject)
               .public_key(key.public_key())
               .serial_number(x509.random_serial_number())
               .not_valid_before(_now())
               .not_valid_after(_now() + datetime.timedelta(days=90))
               .add_extension(x509.SubjectAlternativeName(names),
                              critical=False)
               .add_extension(x509.BasicConstraints(ca=False, path_length=None),
                              critical=True))
    eku = ([ExtendedKeyUsageOID.SERVER_AUTH] if server
           else [ExtendedKeyUsageOID.CLIENT_AUTH])
    cert = builder.add_extension(
        x509.ExtendedKeyUsage(eku), critical=True).sign(
            ca_key, hashes.SHA256())
    cert_p = out_prefix.with_suffix(".pem")
    key_p = out_prefix.with_name(out_prefix.name + "-key.pem")
    cert_p.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_p.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()))
    return CertPaths(ca.ca_cert, cert_p, key_p)


def server_context(ca_cert: Path, cert: Path, key: Path) -> ssl.SSLContext:
    """Require + verify client certs against our CA. TLS 1.2 minimum."""
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_cert_chain(str(cert), str(key))
    ctx.load_verify_locations(str(ca_cert))
    return ctx


def client_context(ca_cert: Path, cert: Path, key: Path) -> ssl.SSLContext:
    """Verify server against our CA. TLS 1.2 minimum."""
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True
    ctx.load_cert_chain(str(cert), str(key))
    ctx.load_verify_locations(str(ca_cert))
    return ctx


def verify_spki_pin(peer_der: bytes, expected_b64: str) -> bool:
    """Compare SHA-256 of peer DER against a pinned base64 digest.
    Simplification: production should hash the SPKI bytes specifically."""
    import base64
    import hashlib
    return base64.b64encode(hashlib.sha256(peer_der).digest()).decode() == expected_b64


def bootstrap_local_pki(out_dir: Optional[Path] = None) -> dict:
    """Dev/test CA + server + client certs. NOT production PKI."""
    base = out_dir or Path(tempfile.mkdtemp(prefix="trust-pki-"))
    ca = issue_ca("aetheros-trust-local-ca", base)
    server = issue_cert(ca, "aetheros-trust-server",
                        ["localhost", "127.0.0.1"], base / "server",
                        server=True)
    client = issue_cert(ca, "aetheros-trust-client", ["trust-client"],
                        base / "client", server=False)
    return {"dir": str(base), "ca": ca, "server": server, "client": client,
            "note": "LOCAL test PKI only — production needs real CA"}
