# Threat Model (Master Prompt 6, condensed STRIDE + AI threats)

Format: ATTACK → boundary → vulnerability → impact → mitigation →
detection → recovery. Full matrix in report §4; operational detail here.

1. Stolen per-boot session token (local attacker) → renderer↔gateway →
   token in main-process memory, drift-rejected, per-boot rotation →
   session hijack → short lifetime + rotation + STOP ALL/revoke paths →
   anomalous WS auth failures → restart/regenerate.
2. Malicious/compromised MCP server → MCP→core → overbroad tools →
   exfiltration/destruction → untrusted-by-default, visible trust,
   scoped tools, confirmations → approval denials/audit → disable server.
3. Malicious plugin → plugin→core → permission creep → privilege
   escalation → manifest permissions, lifecycle audit, disable/revoke →
   audit trail → disable + rotate affected credentials.
4. Prompt injection (page/file/mail/tool output) → content→system →
   instruction confusion → unauthorized action → data-only boundary, no
   content-built commands, gates re-check → denied approvals → deny/stop.
5. Agent self-authorization ("user approved this") → model→policy →
   trusted claims → bypass → authorization never from model text →
   gate logs → deny + inspect.
6. Path traversal/symlink escape → tool→resource → scope bugs → file
   theft/destruction → backend scope validation + confirmations →
   denied actions → restore from checkpoints.
7. Shell/command injection → renderer/IPC → concatenation → RCE →
   zero renderer-side exec; structured IPC params; backend owns parsing
   → command audit → interrupt + review.
8. SSRF/localhost/metadata → network→internal → open egress → cloud
   credential theft → backend egress policy (verify before claiming) →
   blocked-network events → revoke + rotate.
9. Credential leakage via errors/logs → secrets→surfaces → verbose
   errors → account takeover → masked storage + explicit reveal +
   `redactSecrets()` on all error toasts (tested) → red-team tests → rotate.
10. Cross-profile/workspace leakage → isolation → shared caches/keys →
    data mixing → per-profile homes/sockets, session-keyed prompts →
    scope tests → reset profile state.
11. Dependency confusion / compromised update → supply chain → RCE via
    install → official-repo remote pinning, lockfiles, review discipline
    → audit scripts → rollback release.
12. Resource exhaustion (agent loops, retry storms) → runners → no caps
    → DoS → timeouts, cancellation, STOP ALL, quotas (verify caps per
    runner; tracked gap where absent).
13. Session fixation / CSRF / XSS → web surfaces → token theft →
    per-boot tokens, Electron sandbox, no cookie auth in renderer →
    boot/auth anomalies → revoke + restart.
14. Malicious update / artifact poisoning → release → trojan →
    repo pinning + review + (recommend) signature verification (gap).

AI-specific: tool abuse, agent hijacking, context/memory poisoning,
indirect instructions, confused deputy, cross-agent escalation — all
contained by data-only content + re-evaluated gates + attribution.
Residuals and P0–P3 plan live in the final report.
