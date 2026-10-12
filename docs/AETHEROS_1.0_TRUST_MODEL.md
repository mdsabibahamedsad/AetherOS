# AetherOS 1.0 Trust Model

Trust roots: (1) source commit (git), (2) build provenance (CI attestation),
(3) signer identity (codesign/Developer ID/Play), (4) transparency of SBOM.
Clients trust ONLY: manifests signed by the release key over fully
canonicalized JSON, artifacts whose SHA-256 + RSA signature match, HTTPS
origins, non-revoked + non-downgrade releases. No trust by version recency,
filename, or TLS alone. Revocation/kill-switch is authoritative and
fail-closed. Users verify via About/Trust Center (version, channel, build,
commit, signer, verification state). Threats addressed: MITM (HTTPS+sig),
tamper (hash+sig), replay/downgrade (version policy), compromised CDN
(signature over content, not location), insider publish (four-eyes approval +
immutable RC). Residual: key compromise (rotation plan required at launch),
device-path validation pending.
