# Desktop Application Roadmap

**Current Status:** 70% Complete  
**Target:** 100% Production Desktop AI OS

---

## Current State

### ✅ Working
- Electron shell with full main process (6.3K LOC)
- IPC bridge for backend communication
- Chat compositor with rich editing (`@assistant-ui/react`)
- Slash command pipeline (client-side curation + backend dispatch)
- Session management (list, search, resume, delete)
- Profile management (list, create, rename, delete, soul)
- Settings pages (config, env vars, provider/model setup)
- Skills management (list, toggle)
- Toolset management (list, toggle, config)
- OAuth login flow for providers
- Cron job management (CRUD, pause/resume/trigger)
- Messaging platform management
- Log viewer
- File browser with xterm.js terminal
- Side-by-side previews
- Voice (TTS/STT) support
- Self-update mechanism
- Multi-profile backend pooling
- Remote backend support
- Dark/light theme
- NSIS/MSI/DMG/AppImage/deb/rpm installers
- macOS notarization
- 16 Electron main-process test files
- Cross-platform: macOS, Windows, Linux

### 🔶 Partially Working
- **Onboarding wizard** — Provider setup exists, needs first-run flow polish
- **Settings parity** — Not all CLI features exposed in desktop UI
- **File browser** — Functional but limited compared to native explorers
- **Voice** — TTS works, STT audio capture needs testing
- **Analytics** — Connected to backend but UI may have gaps

### 🔴 Not Yet Implemented
- **Full desktop notification system** for background tasks
- **Native file drag-drop** integration with OS
- **System tray** integration
- **Multi-window** (session windows exist but limited)
- **Touch Bar / Touch ID** support (macOS)
- **Global shortcut** for quick access
- **Offline mode** for cached responses
- **Plugin browser/manager** UI
- **Advanced terminal** with tabs and splits
- **Native menubar** with full app menu

---

## Phase 1 — Polish & Parity (2-3 weeks)

### High Priority
- [ ] Complete onboarding wizard flow (provider → model → first chat)
- [ ] Add all missing settings pages (gateway, cron, security, advanced)
- [ ] Polish file browser with tree view, search, preview
- [ ] Complete notification system (desktop alerts for background tasks)
- [ ] Add system tray with mini-menu
- [ ] Full macOS menu bar integration

### Medium Priority
- [ ] Improve voice UI (mic indicator, voice activity, push-to-talk)
- [ ] Add drag-drop for files into chat
- [ ] Keyboard shortcut customization
- [ ] Settings search
- [ ] Session export/import UI

---

## Phase 2 — Desktop-Specific Features (3-4 weeks)

- [ ] Plugin browser and manager (install/remove/enable plugins)
- [ ] Multi-window support (detach sessions, side-by-side agents)
- [ ] Advanced terminal with tabs, splits, themes
- [ ] Local-first file sync (Workspace folders)
- [ ] System-wide search (Spotlight/Alfred-like)
- [ ] Touch Bar support (macOS)
- [ ] Global hotkey to summon app
- [ ] Offline mode with cached agent responses
- [ ] Screen recording/computer-use visualization

---

## Phase 3 — Advanced Desktop (4-6 weeks)

- [ ] Native mobile companion (iOS/Android)
- [ ] P2P agent mesh networking
- [ ] Desktop widgets (menubar/today view)
- [ ] Advanced session analytics dashboard
- [ ] Multi-display support
- [ ] Accessibility (VoiceOver/Narrator)
- [ ] Auto-start on login
- [ ] Deep link handling (`aetheros://`)
- [ ] Custom CSS/JS injection for theming

---

## Phase 4 — Production Hardening (2-3 weeks)

- [ ] Frontend test suite (Vitest + Playwright for Electron)
- [ ] Performance profiling and optimization
- [ ] Memory leak detection
- [ ] Crash reporting (opt-in)
- [ ] Installer telemetry (opt-in)
- [ ] Windows ARM64 support
- [ ] macOS universal binary
- [ ] Linux Flatpak/Snap packages

---

## Technical Debt

| Issue | Impact | Effort |
|-------|--------|--------|
| electron/main.cjs is 6.3K LOC | Maintainability | Refactor into modules |
| Test coverage limited to 16 files | Quality assurance | Add 50+ tests |
| PTY bridge doesn't work on native Windows | Windows users limited | WinPTY bridge |
| No Playwright E2E tests for renderer | Integration risk | Add E2E suite |
| Multi-profile backend pooling is complex | Bug prone | Simplify architecture |

---

## Success Criteria

- [ ] All CLI features accessible from desktop UI
- [ ] First-run setup completes in <30 seconds
- [ ] No feature regressions from CLI → desktop parity
- [ ] Installer works on macOS/Windows/Linux without manual steps
- [ ] 100+ desktop-specific tests passing
- [ ] <100ms IPC response time for common operations
- [ ] Auto-update works reliably across all platforms
