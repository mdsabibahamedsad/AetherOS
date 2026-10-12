# AetherOS Windows Computer Use

Backend: `aetheros_computer/` (perception, approval, side-effects,
idempotency, supervision, checkpoints). Windows execution:
`platform_caps.py` reports `desktop_backend: win32` (SendInput) with
`accessibility: ocr_fallback` — there is NO UI Automation tree yet, so
semantic targeting degrades to OCR + coordinates. Agents must prefer
semantic/identifier targets where available and treat coordinates as a
last resort.

Every action carries action/task/agent IDs, target, risk, authority, and
approval requirements; dangerous side effects never silently retry
(`SAFE_RETRY_POLICY`). Screen capture is task-scoped with provenance;
no continuous capture. Live desktop driving was NOT executed in this
environment (UNVERIFIED); capability state must be surfaced as such in
UI, never as a fake toggle.
