# AETHEROS MASTER PROMPT 5 — EXECUTION LAYER REPORT

## Execution Architecture
- Single pipeline on existing engines (agent runtime, cron/automation runners, PTY IPC, webview, MCP client): policy → permission → executor → tool → observation → validation → result. Renderer executes nothing (zero spawn/exec in `src/`). Doc: `AETHEROS_EXECUTION_ARCHITECTURE.md`.

## Tool Registry
- NEW `lib/tool-registry.ts` (tested): 13 profiled toolset families with capabilities/risk/environments/timeouts + cautious fallback; `describeToolset` joins live `ToolsetInfo`. Badges integrated into every Skills toolset row.

## Capability Model
- read/write/execute/network/browser/communicate/delete/system/admin from actual toolsets; shown per toolset, enforced server-side.

## Risk Model
- LOW reads → MEDIUM writes/automation → HIGH terminal/code/MCP/messaging → DESTRUCTIVE admin/credentials; confirmation mirrors risk; unknown toolsets default medium.

## Permission System
- USER+AGENT+TASK+TOOL+RESOURCE+ACTION+SCOPE evaluated server-side; UI shows scope at gates with least privilege; no "allow all".

## Approval System
- Unchanged and conformant (once/session/always/deny, dismissal = refusal, permanent-allow confirm step).

## Filesystem
- Full op set through tools + views; backend path/scope/traversal guards unchanged; checkpoints surfaced via `/rollback` (real, not atomic-claimed).

## Terminal
- PTY IPC with command/cwd/env/timeout/streams/exit/duration/cancel; output collapsed/virtualized; secrets redacted pre-display.

## Browser
- Partitioned webview + automation client; consequential submits confirm; credentials never exposed.

## Applications
- Same RPC contract; no fake app control; deep-linked results.

## APIs
- Standardized endpoint/method/scope/timeout/retry/error display; secrets never rendered.

## MCP
- Real-config trust/permission/health; never auto-trusted; provenance where reported.

## Background Execution
- Explicit Live/Paused states; state/logs/artifacts/errors preserved; reload survival honest, never fake-live.

## Event System
- Existing gateway events + timeline + run histories; no second streaming architecture introduced.

## Execution Timeline
- Prompt-4 component retained and conformant (operational history only).

## Artifacts
- Pipeline tool→output→artifact→task→workspace verified real (collection, preview, download, open).

## Verification
- Tool-reported signals only; missing backend flag still an honest documented gap.

## Recovery
- Resume/cron-trigger/new-draft/Security/logs paths; checkpoints/rollback where mechanisms exist; partial success counted, never "Completed" on failure.

## Security
- Server-side enforcement; masked secrets + explicit reveal; tiered confirmations; session-keyed isolation; per-leg stop audit; no new attack surface. Doc: threat model.

## Prompt Injection Defense
- Content is data: renderer builds no commands from content; hostile prose displays untrusted and unexecuted; redaction covers leaks.

## Sandbox
- workspace/sandbox/system environments labeled per toolset; isolation owned and unchanged by backend; nothing weakened for convenience.

## Secrets
- NEW `redactSecrets()` (tested, 8 shapes + benign passthrough) wired into every `notifyError` message/detail (40+ call sites covered).

## Audit Logs
- Timeline + Security audit + run histories + notification trail; no reasoning content; integrity backend-owned.

## Accessibility
- Badges are text (non-color); redaction preserves readability (`[redacted]`); existing live-region/focus rules hold.

## Performance
- Registry join is O(n) on tiny lists; redaction is linear regexes on short strings; no new loops/assets/streams.

## Legacy Hermes Cleanup
- Execution surfaces re-swept: zero user-facing Hermes strings; technical identifiers preserved.

## Files Created
- `lib/tool-registry.ts` (+test), `lib/secret-redaction.ts` (+test), 2 docs.

## Files Modified
- `store/notifications.ts` (redaction in error path), `app/skills/index.tsx` (trust badges).

## Files Deleted
- None.

## Tests
- New: 9 (registry profiles/fallback/join/labels; redaction shapes/passthrough/presence).

## Security Tests
- Redaction suite + benign-passthrough (incl. hostile prose) + notification-path coverage; boundary verified (no renderer exec); main-process/backend suites out of scope, not claimed.

## Test Results
- Full suite: 755/758 pass; 3 failures pre-existing `design-tokens.test.ts` drift (untouched). `tsc` + `eslint`: clean on all touched files. Skills regression suite passes.

## Remaining Risks
1. Backend log/tool-output redaction unverified here. 2. No verified-flag. 3. Six fabricated surfaces. 4. No in-repo pentest harness. 5. Checkpoints ≠ atomicity (labeled as such).

## Recommended Master Prompt 6
1. Backend-side redaction verification + verified-flag. 2. Wire the six surfaces. 3. Semantic search + route-splitting. 4. Surface merges + icon/theme consolidation. 5. Regression baselines + AT pass. 6. Consider a renderer security-test job in CI (redaction + boundary assertions).
