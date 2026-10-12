# AETHEROS MASTER 58366 — Unified Architecture (existing, not replaced)

```
┌────────────── INPUT CHANNELS ──────────────┐
│ Desktop (Home/Chat/Jarvis/palette) · CLI · TUI · 20 messaging platforms │
└──────────────┬──────────────┬──────────────┘
               ▼              ▼
┌── INTENT ────┴───┴── LOCAL FAST PATH ──────┐
│ Jarvis matchLocalIntent (exit/nav/allowlisted│
│ apps+URLs/status) + permission policy gate  │
└──────────────┬──────────────┬──────────────┘
               │              ▼ (all other input)
               │   ┌── GATEWAY AGENT RUNTIME (canonical) ──┐
               │   │ session.create + prompt.submit        │
               │   │ model routing + fallback chain      │
               │   │ tool registry/toolsets/MCP + <untrusted_tool_result> │
               │   │ delegate_task (leaf/orchestrator)   │
               │   │ approvals park agent; interrupt/timeout bound it │
               │   └──┬───────┬────────┬────────┬────────┘
└──────────────┘   │       │        │        │
                   ▼       ▼        ▼        ▼
              ┌────────┐ ┌────┐ ┌────────┐ ┌──────────┐
              │ Cron / │ │Mem │ │Observ. │ │ Desktop  │
              │ sched. │ │ory │ │cmd-log │ │ UI reads │
              │ jobs   │ │FTS │ │notify  │ │ stores   │
              └────────┘ └────┘ └────────┘ └──────────┘
```

Boundaries (each verified in code):
- **Channels → runtime:** every input funnels to `prompt.submit` (chat/home)
  or `submitJarvisCommand` (Jarvis); no second brain. H-1 guard at the funnel.
- **Intent vs execution:** local intents are exact-match only + allowlisted;
  ambiguous input always goes to the agent (conservative by construction).
- **Policy:** `decideCapability` (Jarvis) + toolset gating + backend approval
  checks shared across entries; delegation roles strip dangerous tools from
  leaf workers (no approval bypass through delegation).
- **Trust:** tool/MCP/web output wrapped as untrusted data; scanners on
  memory/cron/browser/network paths; secrets stay in `.env`, never rendered.
- **Ownership:** stable ids (`cmd-`, `agent-`, session ids); command log links
  request→session→tools→result; approval/cancel/timeout states distinct.
- **Model-agnostic:** provider plugins behind profiles; fallback chains and
  ModelRouter isolate model choice from execution logic.
