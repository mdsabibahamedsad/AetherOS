# Jarvis Mode — Architecture

`aetheros_jarvis` turns AetherOS into a proactive, voice-capable assistant
("Jarvis") built on the existing `aetheros_voice` engine, the
`aetheros_security` permission perimeter, and the `aetheros_runtime` /
`aetheros_automation` infrastructure. It is a separate package so the core
agent surface stays narrow: the runtime is an integration layer, not new core
model tooling.

## Design Principles

1. **No fake capability.** If a backend is absent (STT/TTS engine, audio
   devices, calendar source), subsystems report `available=False` and return
   empty data — never fabricated wake events, transcripts, or context.
2. **No bypassed safety.** Privileged actions (file delete, git push, payment,
   account login, mission execution) are denied by default and require an
   explicit approval resolver. See `aetheros_jarvis.permissions`.
3. **Privacy-first context.** Clipboard capture is disabled by default and,
   when enabled, runs in an isolated subprocess so a shared-resource fault can
   never crash the runtime.
4. **Proactive but never intrusive.** Suggestions are gated by presence
   (`PresenceDetector.is_available`), a per-source cooldown, and battery/load
   limits (`PerformanceGuard`).
5. **Explainable intelligence.** Every proactive suggestion carries a human
   `reason`; mission reports enumerate steps and errors; tone selection is a
   deterministic register, never simulated emotion.

## Subsystem Map

| Subsystem | Module | Responsibility |
|-----------|--------|----------------|
| Runtime lifecycle | `runtime.py` | init/sleep/wake/pause/resume/shutdown, health, diagnostics, recovery |
| Facade | `__init__.py` | `Jarvis` object + `get_jarvis()` singleton, lazy subsystem wiring |
| Config | `config.py` | `JarvisConfig` persisted to `<home>/jarvis/config.json` |
| Wake word | `wake_word.py` | Offline acoustic wake detection bridged from `aetheros_voice` |
| Voice | `voice.py` | `VoiceEngineWrapper` over `aetheros_voice.core.engine` |
| Conversation | `conversation.py` | Modes (voice/text/mixed/continuous/P2T/hands-free) + turn lifecycle |
| Dialogue | `dialogue.py` | Multi-turn context, follow-ups, clarifications, corrections |
| Presence | `presence.py` | active/idle/away/locked/sleeping from activity + explicit signals |
| Context | `context.py` | `ContextSnapshot` (app, file, project, battery, network, providers) |
| Proactive | `proactive.py` | Observers (battery/calendar/tasks/workspace/downloads) → suggestions |
| Briefing | `briefing.py` | Daily agenda/tasks/status/emails/activity/reminders (+ optional weather) |
| Notifications | `notifications.py` | Coalescing, muting, prioritization, escalation, summaries |
| Mission | `mission.py` | goal → plan → approval → execute → report |
| Permissions | `permissions.py` | `PermissionLayer` deny-by-default approval gate |
| Voice commands | `voice_commands.py` | Spoken phrase → permission-gated action |
| Personalization | `personalization.py` | Named voice profiles persisted per home |
| Tone | `tone.py` | Deterministic tone register for task types |
| Accessibility | `accessibility.py` | Captions, high-contrast, screen-reader, shortcuts toggles |
| Memory | `memory.py` | Long-term key/value memory (`<home>/jarvis/memory.json`) |
| Performance | `performance.py` | Battery-aware gating, cooldowns, resource limits |

## Core Flows

### Wake word (real, offline)

```
audio frames (16 kHz PCM16LE)
  → VoiceActivityDetector gate (speech-shaped envelope required)
  → LocalWakeWord acoustic gate: RMS > 0.06 sustained ≥ ~1 s
  → WakeEvent(phrase, confidence, verified)
```

A pure silence or a short noise burst never trips the detector. When no
reference phrase profile is available the event is emitted with
`phrase_verified=False` — the engine reports *what it actually heard* instead
of faking a match. Detection runs in a worker thread with a 1 s timeout so a
hung backend can never stall the audio thread (`wake_word.py:_run_detection`).

### Mission lifecycle (approval-gated)

```
create(goal, approval_required=True) → plan(steps) → [approve()]
  → execute(): per-step executor or TaskOrchestrator → report()
```

- `approval_required=True` missions never execute without an explicit
  approval callback returning True (cancelled otherwise).
- Approved missions fail-fast: a failed step stops the run and is recorded in
  the report.
- Steps can carry their own `approval_required` flag.

### Proactive observation (presence-gated)

```
PresenceDetector.is_available()  ──False──► nothing
ProactiveEngine.observe(snapshot) ──cooldown 300 s per source──► listeners
```

Each emitted `Suggestion` has `reason` text and an `action` + `params` for a
handler, and can be dismissed or accepted.

## Permissions

`PermissionLayer` wraps `aetheros_security.permissions.PermissionEngine`:

- `require(permission, ...)` returns True only when an installed approval
  resolver approves (or a prior session grant exists).
- With **no resolver installed, everything privileged is denied**.
- Risk tiers: `critical` (payment, account login), `high` (system change,
  file delete, git push, mission execute), `medium` (clipboard read, file
  write, message send), `low` (notifications, suggestions).
- Every decision is recorded in a bounded history for audit.

## Privacy & Safety Notes

- Clipboard read disabled by default; when enabled, executed in a subprocess
  with a 1 s timeout (Windows clipboard is a shared resource that can block
  or fault when another process holds it).
- Voice confirmation requests route through `PermissionLayer` via
  `set_confirmation_resolver`.
- Config, memory, voice profiles, and accessibility prefs all resolve through
  `get_aetheros_home()` (profile-aware); no `~/.aetheros` hardcoding.

## Testing

```
pytest tests/jarvis -q            # 166 tests
```

Coverage: runtime state machine + health/recovery, wake word acoustic gate
(silence/brief noise/sustained speech), conversation modes, dialogue
follow-up/clarification, presence transitions, permission deny-by-default,
mission approval/denial/fail-fast, proactive cooldowns + presence gating,
briefing sections + empty states, notification coalescing, voice command
permission gating, persistence round-trips, tone register, context snapshot,
voice wrapper honest reporting, and the `Jarvis` facade.
