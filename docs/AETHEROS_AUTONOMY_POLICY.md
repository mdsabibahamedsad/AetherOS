# AetherOS Autonomy Policy (Master 43)

## Levels

0 OFF · 1 NOTIFY · 2 SUGGEST · 3 AUTO_READ · 4 AUTO_EXECUTE · 5 SUPERVISED.

## Risk tiers

READ < LOW_RISK_WRITE < HIGH_RISK_WRITE < DESTRUCTIVE,
EXTERNAL_COMMUNICATION, FINANCIAL, SECURITY_SENSITIVE.

Minimum autonomy per tier is tabulated in `models.RISK_MIN_AUTONOMY`;
defaults in `RISK_DEFAULT_APPROVAL`. Explicit user settings win over
inference; inference never overrides explicit settings (no code path).

## Approval kinds

ALWAYS_APPROVE · APPROVE_ONCE (scoped, expiring) · PRE_APPROVED ·
NEVER_ALLOWED (refuse). Scoped grants bind action+resource+automation+
user+expiry.

## Global settings

max_background_agents, max_monthly_cost_usd, max_daily_research (reserved),
external_communication, filesystem, network, approval, notification,
background_execution, power_mode, memory, telemetry (reserved keys
rejected by update_settings allowlist).

## Non-negotiables

- No silent autonomy upgrade.
- No external write without authorization proof.
- No destructive retry.
- No fake monitoring/completion/research/delivery claims
  (UI renders backend state only).
- Emergency STOP ALL always available; safe mode = read-only.
