# AetherOS Automation — Security (Master 43)

## Threat model

Malicious definitions, prompt injection, malicious sites/documents,
compromised MCP, privilege escalation, recursion, notification abuse,
secret exfiltration, leakage, destructive automation, runaway execution.

## Defenses (tested in `tests/aetheros_autonomy/test_autonomy.py`)

- **Injection**: external text stored as data; policy fields keep safe
  defaults (disabled, NOTIFY, ALWAYS_APPROVE). Assembled prompts are the
  cron layer's job; autonomy definitions never eval content.
- **Poisoned import**: `scan_definition` refuses secrets; imports land
  UNTRUSTED + disabled + needs_review; `approve_import` is explicit.
- **Escalation**: risk tiers require minimum autonomy; safe mode forces
  approval for non-read; scoped approvals bind action+resource+automation
  +expiry ("send email X" ≠ arbitrary emails).
- **Recursion**: causal depth 5, cycle detect, cooldown, per-auto rate
  limit (test asserts `recursion_blocked` and skip counts).
- **Secrets**: refused in definitions/logs/notifications/messages;
  `find_secrets` gate on create+import; export excludes metadata.
- **Notifications**: external channels deny-by-default with proof note;
  no sender configured → logged, never silently sent.
- **Destructive**: ALWAYS_APPROVE default, no blind retry, safe-mode
  blocks, e-stop cancels.
- **Isolation**: project_id scoping on search; per-automation tool policy;
  file watcher rooted + ignore/type/size bounded.
- **Audit**: every lifecycle event recorded (created/modified/enabled/
  disabled/run/agent/tool/approval/artifact/notification/deleted).

## Autonomy policy

Levels 0–5, never silently upgraded (no upgrade path exists in code —
level changes only via explicit `update`). Global settings gate
background agents, cost caps, external/filesystem/network policy.
