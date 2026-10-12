# AetherOS Platform Test Matrix

Legend:
- **PASS (evidenced)** — verified by an executed test run in this repository.
- **CI** — exercised by GitHub Actions on the native OS runner; not yet
  validated on real end-user hardware.
- **PENDING EVIDENCE** — capability exists in code but no execution evidence
  yet. NOT a pass. Do not mark PASS until real evidence exists.
- **UNSUPPORTED / API-ONLY** — intentionally not available; clients must not
  pretend otherwise.

Baseline gates (measured in this working tree):

| Gate | Result | Evidence |
|---|---|---|
| Renderer tests (`apps/desktop` vitest) | 688/688 pass | local run, this tree |
| Electron unit tests (`node --test`) | 170/170 pass (161 baseline + 9 new `linux-session`) | local run, this tree |
| Python security suite | 351/351 pass | `scripts/run_tests.sh tests/security`, this tree |
| Typecheck | clean | `npm run typecheck`, this tree |
| Lint | 0 errors | 8 pre-existing style-only errors fixed in `src/components/pane-shell/snap.ts` |
| Entry JS size | ≈3.22 MB (budget ≤5 MB) | last `dist/assets/index-*.js` |

## Feature matrix

| Capability | Windows | Linux (X11) | Linux (Wayland) | iOS |
|---|---|---|---|---|
| Launch | CI + dev machines | CI packaging only — PENDING EVIDENCE on real distros | PENDING EVIDENCE | PENDING EVIDENCE (Xcode required) |
| Login/auth | PASS (bearer/API key flows) | same binary path as Windows — PENDING EVIDENCE | PENDING EVIDENCE | unit-tested request auth — PENDING EVIDENCE on device |
| Task submission | PASS | PASS (shared backend) | PASS (shared backend) | unit-tested client; device PENDING EVIDENCE |
| Plan review | PASS | PASS (shared backend) | PASS (shared backend) | UI present — PENDING EVIDENCE |
| Confirmation/approval | PASS (native dialogs) | PASS (same renderer) | PASS (same renderer) | unit-tested choice contract; device PENDING EVIDENCE |
| Agent monitoring | PASS | PASS | PASS | SSE client unit-tested; live PENDING EVIDENCE |
| Browser automation | native desktop tool | native desktop tool | native desktop tool (browser is network-level, display-independent) | **API/client ONLY** (backend-mediated) |
| Computer use (capture/input) | native | native under X11 (`capabilityStatus` = native) | **UNSUPPORTED** — structured error by design (`linux-session.cjs`) | **remote-control requests only** |
| Terminal | native PTY | native PTY (`ptyprocess` backend) | native PTY (terminal is display-independent) | **remote requests only**, never local shell |
| Filesystem tools | local host files | local host files | local host files | **restricted**: none directly; backend-mediated only |
| MCP | via agent core | via agent core | via agent core | **backend mediated** |
| Memory | agent core providers | same | same | backend mediated (no local copy) |
| Notifications | OS-native | native (x11/wslg), limited wayland tray-adjacent paths | limited | APNs bridge planned — payload contract fixed, delivery PENDING EVIDENCE |
| Updates | electron-updater path + release workflow | package-manager/AppImage replace — PENDING EVIDENCE | same | App Store/TestFlight — BLOCKED on Apple credentials |
| Recovery (uninstall preserves data) | covered by `desktop-uninstall.test.cjs` | same code path — PENDING EVIDENCE | same code path — PENDING EVIDENCE | n/a (no local user data beyond Keychain) |
| Accessibility | renderer a11y suite (`quality:a11y`) | same renderer | same renderer | Dynamic Type/VoiceOver built with system controls — audit PENDING EVIDENCE |

## Rules

1. A cell may move to **PASS** only with an executed run recorded here or in
   the platform release docs.
2. `unsupported-under-wayland` results are correct behavior (structured
   error), not failures — but they must be surfaced honestly in UI.
3. The matrix must never show a green cell that some client cannot actually
   reproduce.
