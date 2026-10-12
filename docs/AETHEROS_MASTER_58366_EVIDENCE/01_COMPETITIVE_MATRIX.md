# AETHEROS MASTER 58366 — Competitive Capability Matrix (2026-10-12)

Scope discipline: each row names the user problem, the inspiration (concept
level, no product-name copying as a goal), AetherOS status with evidence, the
real gap, and implement/defer/reject. Public-product details below are
training-knowledge (live web search unavailable this session) — recommendations
are driven by repo gaps, not parity claims.

| # | User problem | Inspired by (concept) | AetherOS status → evidence | Gap → verdict |
|---|--------------|----------------------|----------------------------|---------------|
| 1 | One place to run any task (chat→agent→tools) | Extensible agent frameworks (Hermes-style toolsets) | Done → canonical `prompt.submit` path, toolsets, H-1 guard | None → keep |
| 2 | Personal workflows + integrations | Personal-assistant automation (OpenClaw-style) | Done → cron/automation + 20 messaging platforms + skills | None → keep |
| 3 | Best model per task, cheap + resilient | Reasoning/coding models (DeepSeek-style) + provider routing | Done → registry + fallback chains + ModelRouter | Expose fallback health in Models UI → P1, defer (needs live providers to verify) |
| 4 | Talk instead of type | Voice-first assistants | Partial → real capture/TTS gates, unwitnessed live | Live voice session → P1, BLOCKED_EXTERNAL (mic + providers) |
| 5 | Assistant remembers me | Persistent memory products | Done (code) → memory2 + providers + provenance UI | Live recall quality eval → P1, BLOCKED_EXTERNAL (gateway) |
| 6 | Work continues on schedule | Background jobs/notifications | Done (code) → scheduler hardening + Tasks actions (H-2) | Restart persistence of desktop action tasks → P0, deferred (backend design decision) |
| 7 | Use my computer (browser/files/terminal) | Computer-use agents | Partial → real webview/bridge/PTY; sim gaps documented | Real back/fwd + download/probe wiring → P1, needs Electron-API work + display to verify |
| 8 | Hard tasks split across specialists | Delegation frameworks | Done (code) → `delegate_task` roles/caps + subagent tree UI | Live delegation trace → P1, BLOCKED_EXTERNAL |
| 9 | Don't break things / stop bad runs | Approval-first + cancellable agents | Done → policy gates both channels, CANCELLED≠FAILED, H-1 | None → keep; live counts need gateway |
| 10 | Don't get tricked by web/tool text | Injection-resistant runtimes | Done → scanners + `<untrusted_tool_result>` + redteam evidence | None → keep |
| 11 | Distribute reusable skills/agents | Extension marketplaces | Partial → marketplace + SDK + curator exist | Versioned distribution trust flow → P2 (no user evidence demanding it yet) |
| 12 | Build automations visually | Visual workflow builders | Partial → legacy canvas exists; Center API-first | No action — canvas is legacy; Center covers supported scheduled-job model. Reject visual-builder expansion (backend supports jobs, not graphs) |
| 13 | Use anywhere (remote/mobile) | Cross-device assistants | Partial → remote-agent dashboard, devices, sync exist | End-to-end sync verification → P2, BLOCKED_EXTERNAL |
| 14 | Know what it did (audit) | Traceable agent ops | Done → command log chain (request→id→tools→result), redacted | Persist log across restart → P1 (pairs with #6) |

Rejected accumulations: model-cloning, new runtimes/databases/frameworks,
visual editors beyond backend support, any feature needing secrets in the
renderer. Deferred items all name their unblocker; none becomes a prompt loop.
