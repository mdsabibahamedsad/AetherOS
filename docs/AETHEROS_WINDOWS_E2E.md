# AetherOS Windows E2E

Golden journeys (1–12 per spec) require a packaged app on a clean VM:
BLOCKED — CLEAN VM. None are claimed passed.

What IS verified at real-state level today: Electron unit suites assert
backend-relevant behavior (install-path detection, console hiding,
symlink-safe IPC resolution, uninstall path classification — 110
passing); Python suites assert gateway trust/registry/tasks/policy,
orchestration, and the intent→guard→verify pipeline (242 passing); CLI
`--help` boots with the full command tree; web typecheck is clean.
E2E must assert backend/filesystem/process/task/artifact state (OSWorld
spirit), not DOM presence. Wire journeys into CI on `windows-latest`
with the packaged build before claiming any journey green.
