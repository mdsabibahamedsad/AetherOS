# AETHEROS PRODUCTION CERTIFICATION

Date: 2026-08-24 · Commit bb9f876 (+ M20–28 working tree) · Verdict:
**PRODUCTION_BLOCKED** — coverage/signing-blocked, zero unresolved
critical defects.

## Verified evidence (this session, Windows host)

| Suite | Result |
|---|---|
| Renderer (vitest) | **688/688**, 92 files |
| Electron main-process | **161/161** (hardening, session-windows, update, uninstall) |
| Python security | **351/351** (incl. fail-open token TTL fix + regression) |
| Typecheck / lint gates | clean |
| Entry JS payload | **3.22 MB ≤ 5 MB budget — PASS** (was 22.6 MB; root cause `codeSplitting:false`, fixed & measured) |
| Installers (sized artifacts) | NSIS 178.7MB PASS · MSI 187.5MB PASS · portable 179MB |

## Certification matrix (abridged — statuses per Master 1–28)

PASS: functionality, agent system, tools/filesystem/shell sandboxing, MCP,
memory architecture, security primitives (post-fix), accessibility tooling,
supply-chain CI (pinning/osv/sbom-audit workflows), regression.

PARTIAL: performance (runtime metrics need interactive profile),
desktop UX polish (visual-regression harness prerequisite), browser/
computer-use live flows, prompt-injection live campaigns.

NOT_TESTED: macOS/Linux interactive, X11/Wayland matrices, multi-monitor/DPI
sweeps, long-session soaks, live update round-trip.

BLOCKED: code signing (no certs provisioned), artifact provenance/SBOM
attestation (not configured), three-native-runner release workflow (absent).

## Release blockers (P0/P1) — per Phase 59 format

1. **Signing unavailable** · P0 · no certs/secrets provisioned · fix:
   add cert identities to GitHub Actions Secrets (Windows EV + Apple
   Developer ID), wire existing afterSign/notarize path · status: OPEN
2. **Release workflow missing** · P0 · no 3-runner TEST→BUILD→SIGN→HASH→
   ATTEST→VERIFY→PUBLISH pipeline · fix: author `.github/workflows/`
   desktop-release.yml using verified build scripts · status: OPEN
3. **Provenance/SBOM not generated or verified** · P1 · enable GitHub
   artifact attestations + SBOM step, verify post-publish · OPEN
4. **Cross-platform interactive QA** · P1 · run install/update/E2E matrix
   on native runners · OPEN

No user-data, data-integrity, security-critical, or functional P0 exists.
Known pre-existing test clusters remain documented (KI-* seed, M26 report)
and are non-blocking platform drift.

## Rule-compliant statements

Not claimed: "100% secure", "unhackable", "zero vulnerabilities",
platform readiness without testing, readiness from code inspection.
Claimed: every number above originates in an executed command on this host.
