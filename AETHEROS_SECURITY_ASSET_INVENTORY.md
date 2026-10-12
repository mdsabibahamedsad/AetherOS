# AETHEROS SECURITY ASSET INVENTORY (Master 26 — condensed)

Date: 2026-08-24 · Evidence-based; every status traces to an executed suite.

## Executed this session
- `tests/security`: **351/351 PASS** (was 350/1 — see FIXED below)
- Electron main-process hardening/platform/update/uninstall suites: **161/161 PASS**
- Golden SC09–SC12 (secret redaction, injection containment, exfil
  redaction, permission nesting): PASS (M20 suite)

## FIXED
- **Fail-open token TTL** (`aetheros_security/tokens/__init__.py`):
  negative `expires_in` minted a NON-EXPIRING token (`exp=0`). Fixed to
  yield an already-expired token; `0 = no expiry` contract preserved.
  Severity HIGH (auth-lifetime bypass on malformed input). Regression:
  `tests/security/test_tokens.py::test_token_expiry` (previously failing,
  now passing).

## Existing defense inventory (verified present)
- Deterministic authorization: `aetheros_security/runtime.SecurityContext`
  (+ delegation depth), tool registry `check_fn` gating, confirmation
  prompts (desktop/TUI/gateway), orchestrator capability-intersection +
  approval/expiry model (M19 swarm_guards), secret redaction in checkpoints
  & telemetry (`aetheros_reliability.checkpoint`, observability/redaction).
- Supply chain: supply-chain-audit.yml, osv-scanner.yml, uv-lockfile-check,
  scripts/security/{check-secrets,audit-dependencies,audit-security}.
- Boundary tests already in-tree: tests/security (351), filesystem/shell
  sandboxing in tools/environments, MCP oauth managers.

## NOT_TESTED this session (live adversarial runs require API spend /
display host; documented per rules)
Live-model prompt-injection campaigns (direct/indirect/multimodal),
browser/computer-use live escape attempts, SSRF from live network paths,
multi-monitor/OS-permission matrices, long-session leak soaks.

## Remaining risks (ACCEPTED_RISK / open)
1. Prompt-injection defenses are structural (data≠authority, deterministic
   authz) but no LLM-live red team was executed this session → PARTIAL.
2. Wayland/screen-capture security: NOT_TESTED (M22/M24 carryover).
3. Signing infrastructure absent (M25) → artifact integrity relies on
   hashes only until certs are provisioned.

No known CRITICAL vulnerability remains. Status rationale: coverage gaps,
not unpatched findings, gate the final verdict.
