# AetherOS 1.0 Architecture Snapshot (as shipped in source, 2bdfbfd)

- Desktop: Electron 40 + React 19 + nanostores; main (`electron/main.cjs`),
  preload bridge (`preload.cjs`), renderer (`src/`). Update subsystem
  (`src/updater/` + `src/release/`) owns check→verify→download→stage→install→
  health→rollback with platform adapters (win32 NSIS/MSI, darwin DMG/PKG,
  linux AppImage/deb/rpm, web SW, mobile store-abstracted).
- Backend: Python agent core (0.16.0) — run_agent loop, toolsets, gateway
  platforms, cron, kanban, memory providers, MCP/A2A. CLI via prompt_toolkit.
- Update service: `services/update/update-server.ts` (manifests, rollout,
  kill-switch, revocation) + release scripts.
- No Kubernetes, no containers shipped, no billing/marketplace in prod scope.
  Anything not listed here is not claimed as shipped.
