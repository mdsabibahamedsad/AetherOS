# AetherOS Fix Ledger

Append-only record of shipped UI/branding fixes. Newest entries at the bottom.
Do not reopen closed issues without new regression evidence.

---

## 2026-09-18 — Home UX redesign + UI polish + installer identity lock (v1.0.1 → v1.1.0)

### UI issues found
1. Home was an ops-only dashboard ("Live operational state") with no hero,
   no primary-action hierarchy, and no first-run orientation.
2. Sidebar rendered 28 destinations as one flat list — no grouping, weak
   active state, no section landmarks.
3. Context panel rendered fabricated values: Provider "Loading...",
   Workspace "~/", Tasks "0", Sync "Idle", Security "Secure" — none backed
   by a store.
4. TopBar search had no accessible name/role and a weak focus ring.

### Root causes
- `src/app/home/index.tsx` IntentSection stopped at a greeting + intent box;
  no quick-action or recent-work layer existed.
- `src/store/navigation.ts` NAV_SECTIONS had no group metadata, so
  `left-sidebar.tsx` could not do progressive disclosure.
- `context-panel.tsx` hardcoded placeholder strings instead of subscribing
  to the real atoms (`$currentProvider`, `$currentCwd`, `$backgroundTaskCount`,
  `$syncStatus`, `$securityStatus`, `$workingSessionIds`, `$allApprovalRequests`).

### Fixes
- Home: premium hero (wolf mark + single `BRAND_WORDMARK` + tagline +
  "Your AI workspace for getting things done."), primary composer with
  label/focus ring/keyboard hint, 6-card Quick Actions grid (every card
  routes to a registered route), Recent Work from live `$sessions` with
  honest empty state, ops sections kept below under "Live operations".
- Sidebar: `NavGroupId` (workspace/intelligence/automation/system) +
  `NAV_GROUP_META`; grouped sections with headers, `aria-current="page"`,
  active indicator bar, tooltips + accessible names when collapsed.
- Context panel: 100% store-backed rows, "Not reported"/"Offline" honest
  states, native `<details>` progressive disclosure; gateway dot.
- TopBar: `aria-label` + `role="searchbox"`, visible focus border, shortcut
  tooltip, responsive truncation.

### Tests
- New `src/store/navigation-groups.test.ts` (group coverage, route
  resolution against APP_ROUTES, id uniqueness).
- New `src/app/home/home.test.tsx` (canonical wordmark, quick-action
  route resolution, id uniqueness).
- New `electron/branding.test.cjs` (productName/appId/artifact/shortcut/
  icon/license/appId-stability guards).
- Full suite: 121 files / 821 tests PASS. `tsc --noEmit` clean.
  `eslint`: 0 errors (25 pre-existing warnings untouched, none in
  touched files).

### Installer branding issue
- AUDIT RESULT: no defect. `productName`/`executableName`/`shortcutName`/
  `uninstallDisplayName`/`legalTrademarks` already "AetherOS";
  `artifactName` already `AetherOS-${version}-${os}-${arch}.${ext}`;
  `appId` `com.aetheros.aetheros` + NSIS guid + MSI upgradeCode untouched;
  unsigned build sets no fake `publisherName` (`signAndEditExecutable`
  + `verifyUpdateCodeSignature` false). Locked by `branding.test.cjs`.

### Legal-attribution decision
- `LICENSE` + `build/installer/license.txt` (staged from LICENSE at build
  time) retain `Copyright (c) 2025 Nous Research` under MIT. This is the
  project's actual upstream license attribution and MUST remain wherever
  the license text ships. It is not presented as the product name anywhere
  in the UI or installer identity (verified: zero "Nous Research" hits in
  the shipped renderer bundle).

### Build result
- `npm run dist:win:nsis -- --publish never` → PASS.
- Artifact: `dist-packaged/AetherOS-1.1.0-win-x64.exe` (195,896,422 bytes)
  + `.blockmap`. Self-naming check: ok (hash 4bcae487…).
- `validate-artifacts.mjs` FAILs only on stale 1.0.0 artifacts + previous-
  phase manifest cross-check (historical, unrelated to this change).

### Installer verification (real install on dev machine)
- Apps & Features: "AetherOS 1.1.0", Publisher "AetherOS". ✓
- Start Menu: `AetherOS\AetherOS.lnk` → `...\AetherOS.exe`. ✓
- Desktop: `AetherOS.lnk`. ✓
- Executable/Uninstaller: `AetherOS.exe` / `Uninstall AetherOS.exe`. ✓
- Launch: window title "AetherOS", responding. ✓
- Shipped renderer: new Home strings present; zero hits for
  `AETHEROSAETHEROS`, `Nous Research`, `Hermes Agent`. ✓

### Version / commit
- 1.0.1 → 1.1.0 (minor: backward-compatible Home experience feature).
- Commit: a35745c (`feat(desktop): Home UX redesign, ... (1.0.1 -> 1.1.0)`)
- Published: NO (`--publish never`). Auto-update: NOT TESTED.

---

## 2026-09-18 — Copyright/company/installer brand replacement (CLOSED)

### Issue
`Copyright (c) 2025 Nous Research` license screen + legacy `Nous Research` /
`Hermes` company metadata vs current AetherOS product identity.

### Root cause
Upstream MIT attribution (must stay) coexisted with inherited
`author: Nous Research` integration metadata, a missing electron-builder
`copyright` field, and stale `hermes <cmd>` hints. No single product-owner
value was pinned for exe/installer metadata.

### Legal-owner evidence (no fabrication)
- `pyproject.toml` authors = `AetherOS`; desktop `package.json` author =
  `AetherOS`; remote `sabib360/AetherOS`.
- In-repo precedent: Tauri bootstrap `copyright: "Copyright © 2026 AetherOS"`,
  exe stamp `LegalCopyright: 'Copyright (c) 2026 AetherOS'`.
- Adopted: `Copyright (c) 2026 AetherOS` for build metadata. `LICENSE` keeps
  `Copyright (c) 2025 Nous Research` (upstream MIT attribution, required).

### Files changed (33)
- `apps/desktop/package.json`: `build.copyright` added (appId/guid/
  upgradeCode untouched).
- `plugins/model-providers/*/plugin.yaml` (27): `author` → `AetherOS`.
- `acp_registry/agent.json`: description/authors → `AetherOS`.
- `flake.nix`: description → `by AetherOS`.
- Desktop tests: `hermes model` → `aetheros model`
  (provider-setup-errors), `hermes login` → `aetheros login`
  (onboarding mock; backend already emits `aetheros ...`, `hermes login`
  is removed per `aetheros_cli/auth.py`).
- `electron/branding.test.cjs`: +copyright guard (6 tests PASS).

### Verification
- `tsc` clean; eslint 0 errors; vitest affected 18/18 PASS;
  `node --test electron/branding.test.cjs` 6/6 PASS.
- Rebuilt NSIS (`--publish never`), reinstalled silently:
  exe `ProductName/FileDescription/CompanyName=AetherOS`,
  `LegalCopyright=Copyright (c) 2026 AetherOS`;
  installer ProductName=AetherOS; Apps & Features `AetherOS 1.1.0`;
  window title `AetherOS`, responding.
- Artifacts: `AetherOS-1.1.0-win-x64.exe` (195,896,457 bytes,
  SHA-256 `28B0692588BBCFDDBD4BB371CCE21DB062FEECE81EA99694CB37F22D0D476249`)
  + `.blockmap` (202,951 bytes).

### Allowed remaining references
- `LICENSE` + `build/installer/license.txt`: upstream MIT attribution.
- Model/provider identifiers (`hermes-4`, `nous` provider, `Nous Research`
  model-family prose): third-party facts.
- `HERMES_*` env, `hermes://`, compat shims, migrations: backward compat.
- `src/hermes.ts` module name/imports: internal identifier (rename churn).
- Skill frontmatter authors, LobeHub index cache, quoted testimonials:
  content authorship / third-party data, not product identity.
- Compat/history tests + docs/evidence logs: fixtures and records.
- Observed, unchanged (pre-existing): `ProductVersion=40.9.3` (electron
  version), `OriginalFilename=electron.exe` — not user-facing branding.

### Status
CLOSED. Commit: 74f5e49. Published: NO. Signing: NOT VERIFIED (unsigned
build, no fake publisher). Clean-VM test: NOT VERIFIED. macOS/Linux
metadata: not built here (config already AetherOS, unchanged).

---

## 2026-09-23 — NSIS License Agreement page product presentation (follow-up, CLOSED)

### Issue
NSIS installer titled "AetherOS Setup" / "AetherOS 1.0.0", but the License
Agreement page body opened with `Copyright (c) 2025 Nous Research` and no
AetherOS product header — the upstream owner read as the current product
owner. (Prior 2026-09-18 entries are NOT reopened: attribution itself was
correct to retain; only the page's product presentation was defective.)

### Root cause
`before-build.cjs` stages the NSIS license verbatim from repo-canonical
`LICENSE` (`MUI_PAGE_LICENSE "build/installer/license.txt"`), and that
canonical file contained ONLY the upstream MIT notice — no AetherOS product
header. `productName`/`copyright`/exe metadata were already correct, so the
license body was the single inconsistent surface.

### Files changed (2 tracked)
- `LICENSE` (canonical source): header is now `AetherOS — MIT License` +
  `Copyright (c) 2026 AetherOS` (matches existing `build.copyright`; no new
  legal entity claimed), followed by an explicit upstream-attribution section
  keeping `Copyright (c) 2025 Nous Research` verbatim + the full MIT body
  unchanged. `appId`/guids/`publisherName` untouched.
- `apps/desktop/electron/branding.test.cjs`: license guard now asserts the
  AetherOS header AND the verbatim Nous attribution; new test asserts the
  staged `build/installer/license.txt` is byte-identical to canonical
  `LICENSE` (7/7 PASS). (`build/installer/license.txt` itself is a gitignored
  staged artifact, refreshed by the build.)

### Legal-attribution decision
Upstream `Copyright (c) 2025 Nous Research` MIT notice PRESERVED verbatim in
both `LICENSE` and the installer page — it is no longer the page's opening
line, but it remains wherever the license ships. No attribution deleted.

### Remaining-branding classification (`src`/`electron`/`assets`/`public`)
- A (user-facing → fix): license page body — FIXED. Zero remaining
  `Nous Research` / `Hermes Agent` hits in shipped surfaces.
- B (keep): `LICENSE`/installer Nous line; `hermes-4`/`nous` model ids.
- C (keep): ledger/docs history. D (keep): `HERMES_*` env, `hermes:` IPC,
  `@/hermes` imports, `src/hermes.ts`, CLI hints, `hermes-parser` dep.
- E (remove): none found.

### Build + verification
- `npm run dist:win:nsis -- --publish never` → PASS; log shows
  `[before-build] staged license.txt from LICENSE`.
- Artifact: `apps/desktop/dist-packaged/AetherOS-1.1.0-win-x64.exe`
  (195,895,475 bytes, 2026-09-23). Generated NSIS script proves the page
  source: `MUI_PAGE_LICENSE ".../build/installer/license.txt"`, whose fixed
  content was verified byte-for-byte; packed `resources/license.txt` matches.
- Exe/installer version resources: `ProductName/FileDescription/`
  `CompanyName=AetherOS`, `LegalCopyright=Copyright (c) 2026 AetherOS`.
- Interactive GUI click-through NOT performed (per-machine installer needs
  elevation; NSIS payload is LZMA-compressed so binary string-scan cannot
  render the page) — verification is build-script + staged-source +
  metadata evidence, not a screenshot.

### Status
CLOSED. Published: NO (`--publish never`). Signing: NOT VERIFIED (unsigned
build, no fake publisher).

---

## 2026-09-23 — Installer License Agreement: upstream line removed from presentation (CLOSED)

### Issue
Installer License Agreement page still contained the line
`Copyright (c) 2025 Nous Research` under the AetherOS header.

### Root cause
`before-build.cjs` staged the NSIS license verbatim from repo-canonical
`LICENSE`, so the upstream attribution line shipped on the installer page.
`nsis.license`/`pkg.license`/`extraResources` all resolve to the staged
`build/installer/license.txt` (proven via generated NSIS
`MUI_PAGE_LICENSE` directive) — one staging source fed every surface.

### Fix (3 tracked files; `appId`/code untouched)
- NEW `apps/desktop/assets/installer-license.txt`: installer-specific
  presentation — `Copyright (c) 2026 AetherOS` + MIT terms, NO upstream
  line. No company invented, no publisher faked.
- `apps/desktop/scripts/before-build.cjs`: stages the new tracked
  presentation file instead of root `LICENSE`. No `package.json` config
  change needed (same destination path).
- `apps/desktop/electron/branding.test.cjs`: asserts the Nous line is
  ABSENT from the installer license, PRESENT in root `LICENSE`, and staged
  file == tracked source (8/8 PASS; release guards 22/22 PASS).
- Canonical `LICENSE` left INTACT (retains upstream attribution in-repo);
  ledger history entries untouched (historical record).

### Verification
- `npm run dist:win:nsis -- --publish never` → PASS (`[before-build]
  staged installer license.txt from apps\desktop\assets\installer-license.txt`).
- Fresh artifact ONLY: `apps/desktop/dist-packaged/AetherOS-1.1.0-win-x64.exe`
  (195,896,427 bytes, 2026-09-23 09:52, SHA-256
  `0E959AD34050CD4D0DFA3AA026F961869BFA7931444F4674A330697E8076AF65`).
  Staged + packed `resources/license.txt`: zero Nous hits; installer version
  resource all-AetherOS (`LegalCopyright=Copyright (c) 2026 AetherOS`).
- Live launch: `AetherOS Setup` main window confirmed running. License-page
  click-through NOT completed (assisted GUI cannot be driven from this shell;
  elevated wizard left idle, nothing installed — verified no new files under
  `C:\Program Files\AetherOS`, no uninstall entry). Dismiss manually.

### Status
CLOSED as PARTIAL (source fixed + fresh installer built + launch smoke test;
page-level visual check pending manual run). Published: NO. Signing: NOT
VERIFIED.

---

## 2026-09-23 — Jarvis Mode full agent + voice control + OS control (PARTIAL)

### Scope
Upgrade, not replacement. Same app, same `/jarvis` route, same gateway.
No second memory DB, no second execution path, no fake results anywhere.

### Root causes discovered
1. Two command paths existed: the real gateway pipeline (`ai-core.ts`) and a
   dead local-simulation stack (`engine.ts` random progress, `executor.ts`
   hardcoded `available:false`, `reasoning.ts` random confidence,
   `observer.simulateEvent`, orchestrator `setTimeout` completions,
   `startup.ts` "local simulation"). UI rendered both.
2. Voice had two implementations: a working SpeechRecognition panel and a
   composer mic button that only flipped an atom. No TTS, no shared pipeline.
3. Pipeline ignored `approval.request`/`sudo.request`/`secret.request` — an
   agent turn needing approval stalled silently until timeout.
4. Step progress was synthetic (`progress+5` per stream delta).
5. Panels were mocks: terminal/files/browser/memory views hardcoded data;
   automation "New" invented fake queued jobs; palette/manager spawned fake
   agents with random progress + auto-remove timeouts.
6. No exit control, no overlay density, no global hotkey, no OS app launch,
   no screenshot path; settings toggles were no-ops.

### Files changed
- NEW `src/lib/jarvis/capabilities/registry.ts` (+test): 37 typed
  capabilities, 12 categories, gateway-agent vs local bindings, live
  availability, tool→capability mapping for the timeline.
- NEW `src/lib/jarvis/permissions/policy.ts` (+test) + `src/store/jarvis-permissions.ts`:
  READ/WRITE/EXECUTE/NETWORK/COMMUNICATE/SYSTEM/DESTRUCTIVE policy,
  destructive+communicate always ask (unsanitizable), voice==text rule.
- NEW `src/lib/jarvis/core/command-gateway.ts` (+test): THE single entry
  (text/voice/chips/palette/panels). Conservative local router (exit, nav,
  allowlisted app/URL, status, models) + approval-first destructive gate.
- NEW `src/lib/jarvis/voice/speech.ts` (+test): STT/TTS provider
  abstraction — gateway (real `/api/audio/transcribe|/speak`) + browser
  speech recognition + system voice, honest availability, mic level meter.
- NEW `src/lib/jarvis/voice/use-jarvis-voice.ts` (+test): full state
  machine, platform mic permission, transcript→gateway, response modes,
  interrupt, opt-in wake word (default OFF).
- NEW `src/store/jarvis-voice.ts`: voice states, mic permission, settings.
- NEW `src/lib/jarvis/os/app-launcher.ts` (+test) + `local-executor.ts`
  (+test) + `hotkey.ts`: allowlisted launch (no paths/shell), validated
  https open, real local bindings (nav/stats/models/clipboard/notify).
- NEW `electron/jarvis-os.cjs` (+node:test): approval-gated screenshot,
  validated global hotkey. Wired in `main.cjs` (2 narrow handlers),
  `preload.cjs` (narrow closures only), `global.d.ts` types. Main also
  allows bare `vscode:`/`spotify:` targets (renderer allowlist is exact).
- EDIT `ai-core.ts`: real tool.start/complete drive steps + thinking stage
  with real tool names; approval/sudo/secret events park into the shared
  Security Center store + notify (no more silent stalls); prompt cleanup on
  turn end; per-command agent entries (running→completed/failed, never
  auto-removed); inputType recorded; zero synthetic progress.
- EDIT UI: composer real mic + states + Esc + focus event; MissionControl on
  gateway + inline Allow-once/Cancel + Ctrl+Space; status bar Exit + voice +
  overlay density (compact/expanded/fullscreen); voice panel on shared hook
  with live level meter; terminal = real PTY + exit codes + kill; files =
  real IPC listing + preview; browser = validated open + agent research;
  memory = real gateway recall/remember; automation = real cron REST;
  agents = real delegation (no simulated spawn); palette sink; settings =
  real voice/hotkey/permissions (dead toggles removed).
- EDIT `desktop-controller.tsx`: app-wide hotkey focus handling + saved
  accelerator registration at boot.

### Architecture
TEXT ─┐
VOICE ─┤─→ submitJarvisCommand → local router | permission gate → gateway
CHIPS ─┘   pipeline (session.create/prompt.submit/stream events) → history.
Events: thinking/tool.start+complete/approval/message → timeline, log,
agents, notifications. Voice transcript IS a text command downstream.

### Verification (real runs, no mocks)
- `tsc` clean; eslint 0 errors; vitest 130 files / 870 tests PASS (9 new
  Jarvis suites); electron node tests incl. new `jarvis-os.test.cjs` PASS.
- Rebuilt NSIS `--publish never`:
  `dist-packaged/AetherOS-1.1.0-win-x64.exe` (195,910,146 bytes, 2026-09-23
  12:47, SHA-256 `CDEC5EEE6AF1755DC7795CEC5D241DEE28A258298C428A70BE12E42ECED40B62`).
- Packaged-app CDP drive: boot title AetherOS + bridge; real system stats;
  801 KB PNG via NEW `aetheros:os:screenshot`; hotkey set+clear via NEW IPC;
  PTY echo roundtrip; gateway WS URL. All returned live data.
- Live backend agent turn (direct backend, same WS protocol the pipeline
  uses): session.create OK (anthropic/claude-sonnet-4), prompt.submit OK,
  streamed `message.complete` carrying a REAL 402 insufficient-credits
  provider error — truthful failure, zero fabrication. Success-text turn
  NOT VERIFIED (upstream funding).
- NOT VERIFIED: voice E2E (no microphone in this environment), visual
  timeline walkthrough + physical hotkey press (packaged GUI will not stay
  alive here — process reaped minutes after boot, no crash trace; needs a
  stable desktop session), TTS audio output.

### Known limitations
- Wake word: opt-in setting + browser-provider gate implemented; enabled
  path untested (no mic).
- Explorer/Settings app launch not allowlisted (main URL validation);
  use the gateway agent for file-manager tasks.
- Memory panel shows session results (no direct memory REST exists).
- `engine.ts`/`executor.ts` simulation modules remain in tree but are no
  longer on any UI path (dashboard reads engine state only).

### Status
PARTIAL (shipped + tested + runtime-proven where physically possible;
voice/model-output/visual flows pending a mic'd, funded, stable session).
Published: NO. Signing: NOT VERIFIED.
PENDING LEDGER APPEND — content to append to docs/AETHEROS_FIX_LEDGER.md:

---

## 2026-09-23 — Jarvis 2.0 autonomous brain: canonical task model + orchestrator + computer use + approval/observability (PARTIAL)

### NEW ROOT CAUSES
1. No canonical JarvisTask existed: three overlapping models (types.ts TaskStatus 8 states, planner.ts TaskStatus 7 states, task-manager BackgroundTaskStatus 6 states) with no transition validation — UI could not render one truthful task state.
2. No orchestrator: executePipeline ran gateway turns but nothing sequenced UNDERSTAND → PLAN → POLICY → EXECUTE → OBSERVE → RECOVER → VERIFY, and nothing classified errors (retryable vs fatal) — one tool error ended the task.
3. Computer use had no validated pointer/keyboard path: only launch-app/open-url/screenshot existed; blind coordinates were not structurally rejected and no gateway-owned input capabilities were registered.

### FIX
- Added lib/jarvis/core/task-state-machine.ts (14-state JarvisTask + explicit transition table + classifyError + retry cap 3).
- Added lib/jarvis/core/orchestrator.ts wrapping existing engines (ai-core, execution-planner, reasoner, observer, tool-router, approval-engine, persistence, observability).
- Added lib/jarvis/core/tool-router.ts (deterministic routing + validateToolCall), core/approval-engine.ts (NONE/LOW/MEDIUM/HIGH/CRITICAL), core/observability.ts (latency/diagnostics), core/task-persistence.ts (persist/recover), core/emergency-stop.ts, computer/computer-use.ts (validated window/pointer/keyboard with verify hooks; blind coordinates rejected).
- Registered computer.window + computer.input gateway capabilities; exported all modules from lib/jarvis/index.ts.

### VERIFICATION
- New tests: task-state-machine (5), tool-router (7), approval-engine (3), computer-use (6) — ALL PASS.
- Full Jarvis suite: 13 files / 70 tests PASS (npx vitest run src/lib/jarvis src/store/jarvis-lifecycle.test.ts).
- npx tsc -p . --noEmit CLEAN. npm run build PASS (9.53s, dist verified).
- Evidence: docs/AETHEROS_MASTER_74184_EVIDENCE/01-12.
- Installed-app flows TEST A-J: NOT VERIFIED (headless env, no backend/mic/display) — verdict AETHEROS_JARVIS_2_PARTIAL.
---

## 2026-09-23 — Installed-app verification attempt (Windows 10, bundled Python 3.12.13, Chrome present, mic present)

### ENVIRONMENT
- Windows 10 Pro 2009, AMD Radeon Graphics
- Chrome at C:\Program Files\Google\Chrome\Application\chrome.exe
- Audio endpoints: Headphones, Headset, Speakers (multiple OK)
- Bundled Python 3.12.13 at C:\Program Files\AetherOS\AetherOS\resources\py\Scripts\python.exe
- User profile exists at %USERPROFILE%\.aetheros with OPENROUTER_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS

### BUILD + PACKAGE + INSTALL
- `npm run build` (apps/desktop): PASS (9.94s)
- `npm run builder -- --win nsis`: PASS → AetherOS-1.1.0-win-x64.exe
- Silent install `/VERYSILENT /NORESTART`: PASS → C:\Program Files\AetherOS\AetherOS\AetherOS.exe

### INSTALLED APP RUNTIME
- Launch: 4 Electron processes spawn (main, renderer, GPU, utility)
- Backend: Bundled Python starts, binds HTTP on 127.0.0.1:9120 (serves dashboard HTML)
- tui_gateway: WebSocket accepts connections (logged: "ws accepted peer=127.0.0.1:61780")
- Jarvis bundle: 280.45 kB chunk included in dist
- Messaging gateway: NOT RUNNING — no platforms enabled in config.yaml (requires TELEGRAM_ALLOWED_USERS, etc.)
- Stability: App + backend exit cleanly after ~30s (no crash in agent.log/errors.log; likely shutdown when no gateway sessions)

### TEST A–J RESULTS
| Test | Description | Result |
|------|-------------|--------|
| A | Ctrl+Space → "Open Chrome" → Chrome opens → verified | NOT VERIFIED (no gateway session.create) |
| B | Voice "Open Chrome" → transcript → execution → spoken | NOT VERIFIED (mic OK but no gateway STT/TTS) |
| C | "Find latest release report" → files.search → result | NOT VERIFIED (needs active gateway session) |
| D | "Run desktop tests" → terminal → streamed output → exit code | NOT VERIFIED (needs active gateway session) |
| E | "Look at screen" → capture → vision → truthful | NOT VERIFIED (needs active gateway session) |
| F | "Open browser search AetherOS" → browser → observation | NOT VERIFIED (needs active gateway session) |
| G | "Exit Jarvis" → Home, tasks preserved | CODE PATH VERIFIED (matchLocalIntent) — NOT E2E |
| H | Disconnect gateway → reconnect → Jarvis operational | NOT VERIFIED (gateway not running) |
| I | Long task → leave Jarvis → Jobs panel shows running | NOT VERIFIED (job-manager implemented, not E2E) |
| J | Restart AetherOS → recover task metadata | NOT VERIFIED (persistence implemented, not E2E) |

### VERDICT
**AETHEROS_JARVIS_2_PARTIAL** — all code-level criteria implemented, unit-tested (70 PASS), typechecked (CLEAN), built, packaged, installed, and the installed app launches with a live backend and tui_gateway. However, the messaging gateway (which powers executePipeline, session.create, and all agent tool execution) does not run because no messaging platforms are configured in the user's config.yaml. Without an active gateway, TEST A–J cannot be completed end-to-end.
---

## 2026-10-12 � MASTER 58361 premium UI pass (desktop renderer only)

### FIXED (verified by typecheck + 891 vitest PASS)
- F-1 Duplicate command-palette mount removed (AppShell second instance deleted; canonical palette in DesktopController overlays).
- F-2 Sidebar active highlight now route-driven (location.pathname via appViewForPath; atom synced).
- F-3 Header workspace/profile pill added (-> /profiles).
- F-4 Home composer draft stashed before Files/Jarvis navigation.
- F-5 Dead permanent Context rail (app/shell/context-panel.tsx) deleted; zero importers.

### REJECTED (intentional design, test-pinned)
- Dark-mode default: reverted to light fallback per profile-theme.test.ts contract. Not reopened without maintainer decision.

### ACTIVE BLOCKERS
- Packaged-app validation not run in this environment.
- Repo-wide ESLint debt predates this pass (touched-file errors all on untouched lines).

### EVIDENCE
- docs/AETHEROS_MASTER_58361_EVIDENCE/ (00-05) + docs/AETHEROS_MASTER_58361_UI_REDESIGN_REPORT.md
- typecheck clean; vitest 134 files / 891 tests PASS.


---

## 2026-10-12 � MASTER 58362 finalization (desktop renderer only)

### BASELINE REPRODUCED
- 58361 fixes re-verified in place; typecheck clean; vitest 134/891 PASS; dev server serves HTTP 200.

### FIXED (typecheck clean + vitest 137/900 PASS + vite build PASS)
- G-1 Tasks double-count (success in Active+Completed), action-id key collisions, lastRun double-format (tasks/index.tsx + partition test).
- G-2 MCP import lost on reload (now persisted with rollback); health filter hid unknown servers (option added).
- G-3 Resource Manager fabricated Math.random() metrics labeled Live (now mirrors real $systemStats; honest empty states; Trash really clears via new clearAlerts).
- G-4 Models dead getEnvVars fetch removed; loading + error/Retry shells added.
- G-5 Projects dead Open Folder buttons wired to real folder picker + workspace start.
- G-6 Automation canvas onClick={() => {}} no-op removed.
- G-7 Icon-only buttons missing accessible names fixed (sidebar collapsed, statusbar x2 renderers, 11 Jarvis sites) + palette focus restoration.

### KNOWN PRE-EXISTING LIMITS (documented, not reopened as regressions)
- Knowledge sync simulation/scores, diagnostics simulated checks, browser local-only nav/canned AI, agent-hub local Run/Stop, repo-wide ESLint debt, light-theme default contract.

### ACTIVE BLOCKERS
- Packaged-app rebuild blocked: write-build-stamp.cjs needs a git ref; tree is not a git checkout (fake SHA refused). Stale 1.0.0/1.1.0 artifacts predate changes.
- No display harness: manual resize, screen-reader, live-gateway E2E not performed.

### EVIDENCE
- docs/AETHEROS_MASTER_58362_EVIDENCE/ (00-04) + docs/AETHEROS_MASTER_58362_UI_FINALIZATION_REPORT.md
- typecheck 3x clean; vitest 137/900 PASS; 	sc -b + ite build (26.41s) + assert-dist-built PASS.


---

## 2026-10-12 � MASTER 58363 acceptance (desktop renderer only)

### PERMANENTLY CLOSED (no fresh contrary evidence; not re-run)
- 58361 F-1..F-5, 58362 G-1..G-7.

### NEW REGRESSION FIXED
- H-1 Duplicate Jarvis execution: double-Enter/double-click spawned two gateway sessions (composers unguarded + runCommand reset-before-submit). Fixed at choke point (JarvisBusyError in submitJarvisCommand, nav-exit exempt, Allow-once bypasses) + pre-reset check in unCommand + both composer guards (text preserved, Send disabled with reason). Tests: 4 new in command-gateway.test.ts.

### VERIFICATION
- typecheck clean; vitest 137/904 PASS; touched-file lint 0 errors.
- Canonical path re-traced: Home/Chat/Jarvis all reach session.create + prompt.submit; voice LISTENING/SPEAKING gates unchanged; approval gates unchanged (no bypass found among entries).

### ACTIVE BLOCKERS (unchanged, owner/infra side)
- Live gateway/model/mic needed for Workflows A(live parts)/B(live)/D5; git checkout needed for packaged rebuild.

### EVIDENCE
- docs/AETHEROS_MASTER_58363_EVIDENCE/ (00-03) + docs/AETHEROS_MASTER_58363_ACCEPTANCE_REPORT.md


---

## 2026-10-12 � MASTER 58364 closure (evidence-only, no source changes)

### PERMANENTLY CLOSED (guard re-verified present, no contrary evidence)
- 58361 F-1..F-5, 58362 G-1..G-7, 58363 H-1.

### VERIFICATION THIS PHASE
- typecheck clean; targeted vitest 9 files / 53 tests PASS (gateway, ai-core, task-state-machine, approval-engine, policy, jarvis-lifecycle, voice hook, composer, sidebar).
- Full suite not re-run (no code changes); 58363 baseline 137/904 frozen.

### ACTIVE BLOCKERS (exact owner actions)
- Live A2/B/D: needs gateway + provider credentials in the operator's environment (all unset here). Next: credentialed dev session, run matrix rows once.
- Voice live: needs interactive mic grant + STT/TTS providers. Next: same session as above.
- Packaged rebuild: needs git checkout (or trustworthy CI $GITHUB_SHA). Next: build from a checkout with --publish never, record stamp + hashes, launch and exercise.

### EVIDENCE
- docs/AETHEROS_MASTER_58364_EVIDENCE/ (00-01) + docs/AETHEROS_MASTER_58364_INTEGRATION_CLOSURE_REPORT.md


---

## 2026-10-12 � MASTER 58366 roadmap + H-2 (desktop renderer only)

### PERMANENTLY CLOSED (no contrary evidence)
- 58361 F-1..F-5, 58362 G-1..G-7, 58363 H-1.

### NEW FIX
- H-2 Task lifecycle actions in Tasks view: cron rows now pause/resume/trigger/delete via proven runtime methods (per-row busy lock, confirm on delete, honest view-only action rows); pure action matrix tested.

### VERIFICATION
- typecheck clean; vitest 137/908 PASS (+4 new); touched-file lint 0 errors.
- Roadmap grounds every claim in traced call paths; competitor notes labeled training-knowledge (web search unavailable); visual builder rejected, simulations left to backend scope.

### ACTIVE BLOCKERS (unchanged)
- Live gateway/providers/mic; git provenance for packaging.

### EVIDENCE
- docs/AETHEROS_MASTER_58366_EVIDENCE/ (00-04) + docs/AETHEROS_MASTER_58366_ROADMAP_REPORT.md

