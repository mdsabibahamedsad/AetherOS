# Incident Response (§53-55, §158)

Lifecycle: DETECTED -> TRIAGED -> CONTAINING -> CONTAINED ->
INVESTIGATING -> RECOVERING -> RESOLVED -> POSTMORTEM (no backward
jumps except re-containment).

## Detectors

policy violation, credential misuse, unexpected privilege
escalation, repeated denied actions, tool abuse, prompt injection,
data exfiltration attempts, identity/agent/network/behavior
anomalies, physical safety anomalies.

## Containment ladder

WARN -> RATE_LIMIT -> PAUSE_AGENT -> REVOKE_CAPABILITY ->
ISOLATE_TOOL -> BLOCK_NETWORK -> QUARANTINE_EXTENSION ->
STOP_SWARM -> STOP_AUTOMATION -> EMERGENCY_STOP. The destructive
subset (REVOKE_CAPABILITY, BLOCK_NETWORK, EMERGENCY_STOP) requires
explicit policy opt-in — automatic containment is never
irreversibly destructive by default.

## Explanation output

what happened / why detected / what blocked / what allowed / what
revoked / what remains active — all from recorded state.

## Learning loop (§130)

incident -> root cause -> regression test -> policy test ->
benchmark -> monitoring rule (Master-51 integration point).
