# AetherOS Execution Threat Model & Security Tests (Master Prompt 5)

## Threat model (renderer scope; backend enforces)
- Prompt injection: external content (pages, files, mail) is DATA, never
  instructions — the renderer executes nothing from content; hostile
  prose passes through display unchanged and untrusted. Verified: no
  content-driven command construction in `src/`.
- Tool/command injection: no string-concatenated shell in renderer; all
  execution crosses typed IPC/RPC with structured params.
- Path traversal: scope validation + sanitization live in main/backend
  (`workspace:sanitize`, fs guards) — unchanged, not reimplemented.
- SSRF / exfiltration / escalation / confused deputy: server-side scopes;
  renderer shows scope, never widens it. MCP servers untrusted by
  default with visible trust states.
- Credential leakage: secrets masked at rest (`redacted_value`),
  explicit per-key reveal, and now `redactSecrets()` over every error
  notification message + detail (tested shapes: PEM blocks, sk-/ghp-/
  xox-/AKIA/Bearer/key=value). Backend owns redaction in logs/tool
  output; renderer adds the display layer.
- Malicious MCP/browser/file content: rendered as data with provenance;
  consequential actions (submit/publish/delete/send) always confirm.

## Security tests (this pass)
- `secret-redaction.test.ts` (8): masks 8 credential shapes; benign
  prose/paths/ids untouched (incl. hostile-but-secretless prose);
  presence detection without revealing content.
- Notification path: redaction applied inside `readableError`, so every
  `notifyError` caller (40+ sites) is covered without touching call sites.
- Existing suites re-pass: skills view (toolset rows edited), session,
  prompts, command-palette, agent, navigation (15/15 targeted).
- Pre-existing Electron main-process suites (`test:desktop:platforms`)
  untouched; backend security suites out of renderer scope (not claimed).

## Failure tests (status)
Covered by existing behavior + honest messaging: tool unavailable,
timeout, crash, network failure, permission denied, invalid input,
partial output, duplicate execution (idempotent paths), restart recovery.
No new simulations added — failure is surfaced, never staged.

## Remaining risks
1. Backend log/tool-output redaction not re-verified here (renderer
   layer only). 2. No backend verified-flag (Prompt 4 gap). 3. Six
   fabricated surfaces still present (prior reports). 4. No automated
   pentest harness in-repo.
