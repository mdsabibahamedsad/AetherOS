# AETHEROS MASTER 15 — COMPUTER-USE FINAL REPORT

Date: 2026-08-23 · Companion to `AETHEROS_MASTER_15_COMPUTER_USE_AUDIT.md` (Phase 0).

---

## 1–7. Architecture (as built)

Master 15 adds a new `aetheros_computer/` package that provides the **unified
action layer** over the existing production spine (browser tools, computer-use
backends, terminal environments, vision stack). No existing engine was
rewritten; every module composes downward into MASTER 7 security, MASTER 10
perception, and the existing tool implementations.

```
USER INTENT
   ↓
ExecutionPlan (approval.py) ── plan preview for R3+/R4 actions
   ↓
UnifiedApprovalEngine ── hardline blocklist → allowlists/YOLO → risk gate
   │                        gateway queue (wait|async) / CLI prompt / fail-closed deny
   ↓
APIDispatcher (dispatcher.py) ── API → structured → accessibility → DOM → visual → coords
   ↓
Existing engines (browser_tool, computer_use, terminal_tool, vision_tools)
   ↓
VerificationEngine → RecoveryEngine (scaffold) → audit log (computer_actions/*.jsonl)
```

### Module inventory

| Module | Phases | Contents |
|---|---|---|
| `aetheros_computer/action.py` | 1–3, 19 | `ActionDomain`, `RiskTier` (R0–R4, aligned with MASTER 7 action_guard), `ActionMetadata` (+dict round-trip for audit), canonical registry of **64 actions** across browser/desktop/terminal/vision/filesystem/system with per-action risk + verification requirement, `FieldClassification` + `classify_field()`, `SubmissionSummary`, JSONL action-log under `<AETHEROS_HOME>/computer_actions/` |
| `aetheros_computer/perception.py` | 6–9, 35–37 | `PerceptionSource`, `ElementRole` (28 ARIA-aligned roles), DPI-aware `BoundingBox.to_logical()`, `UIElement` with confidence + selector generation (`to_selector()` prefers ax_ref/css/text over coordinates), `PerceptionSnapshot` (text search, interactive-element filter), `PerceptionEngine` (browser-AX parse from CDP frame tree, vision-understand parse, merge-with-dedup preferring higher confidence), `VisualTargeter.find_target()` semantic-first ranking with configurable minimum confidence |
| `aetheros_computer/approval.py` | 3–5, 20–21, 54–57 | `check_hardline_block()` (12 unconditional patterns incl. rm -rf /, mkfs, shutdown, fork bomb — bypass-proof by design), 40+ approval-gated dangerous patterns with bypass-prevention normalization (ANSI strip, NFKC, backslash/empty-string splits, resolved-path rewrite), `ExecutionPlan`/`PlanStep` + ASCII-safe `to_user_preview()`, `build_execution_plan()`, `UnifiedApprovalEngine`: hardline→permanent/session allowlists→YOLO→risk gate→gateway queue (`wait=True` blocking or `wait=False` returning `PENDING:<id>`)→CLI inline→fail-closed deny; late resolution of expired requests refused (Phases 23/56); `create_submission_confirmation()` classifying fields before consequential POST; `create_login_handoff()` for password/MFA/CAPTCHA takeover |
| `aetheros_computer/dispatcher.py` | 10–11, 94 | `ExecutionPath` priority ladder implementing API-first strategy; capability registry + sensible per-domain defaults; `DispatchResult`; `Dispatcher.execute()` pipeline (approval → dispatch w/ fallback → verification → recovery → audit); `VerificationEngine` (STATE_MATCH via perception indicators, DOMAIN_CONFIRMATION, IDEMPOTENCY hooks); `RecoveryEngine` failure classifier (TARGET_NOT_FOUND / LOW_CONFIDENCE / TIMEOUT / UI_CHANGED) with bounded retries |

## 8–17. Safety posture delivered

- **Credentials**: never accepted as action parameters anywhere in the new layer;
  hardline patterns block credential destruction; login handoff pauses instead.
- **Untrusted content**: unchanged wrappers (`<untrusted_tool_result>` on
  browser_/web_/mcp_ results) remain the enforcement point; the unified layer
  adds verification but never elevates page/desktop text to instruction status.
- **Fail-closed**: high-risk action outside interactive context is denied, not
  silently executed. Expired approvals can never approve retroactively.
- **Bounded**: every request carries timeout + expiry; dispatcher caps retries.

## Verification & regression

| Suite | Baseline | After |
|---|---|---|
| browser/cdu/vision/terminal/file/approval/mcp tools | 631 passed / 9 failed (pre-existing Windows) | **identical — 9 same failures, zero regressions** |
| memory tools + lifecycle | 97 passed | 97 passed |
| **new** `tests/aetheros_computer/test_master15_action_model.py` | — | **23 passed** |

New-test coverage: canonical registry keys & risk lookups; metadata round-trip;
field classification (credential/financial/sensitive/public); hardline blocks
(incl. declared-low-risk override attempt); dangerous-pattern gating; read-only
pass-through; non-interactive fail-closed denial; gateway queue→notify→resolve→
session-scope flow (`wait=False`); expired-request late-resolution refusal +
cleanup sweep; YOLO auto-allow with hardline precedence; execution-plan risk
derivation; cp1252-safe previews; sensitive-submission consequence flagging.

## Honest scope statement

**Landed:** the four modules above + tests + both Master docs. Smoke-verified
end-to-end behaviors: hardline/dangerous gating decisions, plan preview,
api-first path ordering, metadata persistence contract.

**Not landed (attempted, aborted safely):** adding
`browser_download` / `browser_upload` / `browser_form_fill` / `browser_submit`
schemas+handlers into `tools/browser_tool.py`. Multiple edit strategies failed
on tooling/encoding constraints; per the preservation rule the change was
aborted with the target file byte-verified untouched (the only working-tree
delta there is a pre-existing `hermes→aetheros` docstring rename predating this
work, left intact). Insertion point documented: append schemas after
`BROWSER_TOOL_SCHEMAS` (line ~1616), extend `_BROWSER_SCHEMA_MAP` with the
master15 list at line ~3787, add four `registry.register` blocks after the
`browser_console` registration (~line 3863).

## Remaining limitations (mapped to checklist)

1. Perception engine's desktop-AX path currently falls through to vision
   (no public UIA/AT-SPI integration yet) — macOS-only native AX today.
2. No per-monitor DPI scale query; `BoundingBox` normalization exists but no
   live scale-factor source on Win32/Linux.
3. RecoveryEngine strategies are classified but not yet implemented
   (re-observe/adapt loop is scaffolded).
4. MCP computer-tool passthrough, watch mode, multi-agent handoff, stress &
   cross-platform GUI evaluation cycles remain future work (documented in audit
   §14 items 26–70).
5. Windows verified natively this session; Linux/macOS rest on code-path
   symmetry + existing CI coverage.

## Core principle — upheld

OBSERVE → UNDERSTAND → PLAN → AUTHORIZE → ACT → OBSERVE → VERIFY → RECOVER is
now an explicit, test-enforced pipeline rather than a convention: nothing in
the unified layer executes without passing the same hardline floor that guards
terminal commands, risky work requires preview + approval binding, approvals
expire, unknown contexts deny, and every decision is auditable via
`ActionMetadata` JSONL logs.

---

## ADDENDUM — Phase sweep completion (same day)

Second pass closed the remaining implementable gaps **additively** (no working
module rewritten):

| New file | Closes |
|---|---|
| `aetheros_computer/idempotency.py` | 52 (TTL store, reset_key for failed retries) |
| `aetheros_computer/dataflow.py` | 26 transfer records/exfil verdict · 71 phishing heuristics (punycode, @-authority, IP-literal, subdomain depth, brand mismatch) |
| `aetheros_computer/pattern_memory.py` | 48/49 UI-pattern store — redact-then-refuse contract, confidence decay, user forget |
| `aetheros_computer/task_checkpoint.py` | 50 checkpoints · 51 resume_filter · 82 budgets |
| `tools/browser_transfer_tools.py` | 15 tabs (CDP Target.*) · 17 download (SSRF/policy/secret-URL/size/dup guards, never-execute flag) · 18 upload (source screening + DOM.setFileInputFiles) |
| `tools/browser_form_tools.py` | 19 classified batch fill via existing browser_type · 20 confirm-gated submit w/ credential masking · 52 duplicate-submit block |

Upgrades inside Master-15-owned modules:
- `dispatcher.py`: estop gate · safe-mode read-only gate · budget gate · dry-run path · idempotency pre-check · checkpoint recording · **RecoveryEngine strategies implemented** (reobserve→retry, timeout doubling, high-risk explicit-retry guard) → closes 11, 67, 68, 83*, 84*, 85* (*CU-level integration of existing global mechanisms)
- `approval.py`: TARGET hash binding on approve (Phase 57) — wrong-target approvals refused
- `toolsets.py`: 5 names appended to the `"browser"` toolset (additive only)

### Updated tally

| Status | Before | After |
|---|---|---|
| Done | 53 | **70** |
| Partial | 38 | **27** |
| Not started | 9 | **3** (89 knowledge integration, 95 scenario suite, 98 stress) |

### Verification

- New tests: `tests/aetheros_computer/test_master15_safety_layer.py` (19) +
  `tests/tools/test_master15_browser_transfer.py` (14) → **56 total Master-15
  tests green** (incl. the original 23).
- Regression: browser/cdu/vision/terminal/file/approval/mcp suites =
  **631 passed / same 9 pre-existing Windows failures** — zero regressions.
- Wiring proven: all 5 tools registry-registered AND present in
  `TOOLSETS["browser"]["tools"]`.

Remaining honest gaps are evaluation-scale items (golden scenarios, adversarial
website corpus, long-run stress) plus live consumption of pattern-memory by the
targeter and MASTER-14 retrieval hints — all documented for follow-up.
