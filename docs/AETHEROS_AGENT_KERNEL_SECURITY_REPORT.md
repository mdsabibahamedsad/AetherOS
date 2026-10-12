# AetherOS Agent Kernel 1.0 — Security Report

## Invariants tested (§94, all PASS in `test_agent_kernel_security.py`)

1. child authority never exceeds parent — PASS (subset enforced, excess
   denied with warning).
2. untrusted content never becomes authority — PASS (escalation caps not
   granted; `untrusted_no_authority` rule active).
3. policy denial cannot be bypassed by model output — PASS (ungranted
   `privileged.wipe` denied).
4. renderer cannot grant backend authority — PASS (unknown grant denied).
5. remote agent cannot directly invoke privileged capability — PASS
   (`device.control` denied/failed without grant).
6. revoked identity cannot execute — PASS (fixed `revoke_grant` past-expiry
   bug; invocation denied).
7. expired approval cannot execute — PASS (expired request stays expired).
8. emergency stop cannot be overridden by agent — PASS (invocation denied
   with "Emergency stop active").
9. secret data cannot cross forbidden boundary — PASS
   (`SECRET→PUBLIC` denied).
10. simulation cannot be reported as reality — PASS (hardware stub raises
    `REQUIRES_HARDWARE`, surfaced as denied/failed).

Plus: prompt-injection payload denied, SSRF (169.254.169.254) denied via
network denylist.

## Residual risks

- Full-CLI `main.py` has a pre-existing `agent` subparser conflict —
  kernel CLI verified standalone; main entrypoint still broken upstream.
- `AIAgent` live path (`AETHEROS_KERNEL_REAL_AGENT=1`) untested here (no
  credentials); stub is the default.
- MCP/A2A remote-component adversarial testing limited to grant mediation;
  no live malicious-server harness executed (REQUIRES_EXTERNAL_ENVIRONMENT).
- No third-party audit, signing, or attestation claims made.
