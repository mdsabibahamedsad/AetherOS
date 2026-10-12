"""
Aetheros Master 13 — Universal Automation core-foundation layer.

This package extends the cron scheduler spine additively:

- ``model``         AutomationDefinition view over the durable job dict,
                    lifecycle derivation, validation, resource limits.
- ``schedule_time`` Timezone/DST-aware schedule helpers and missed-run policy.
- ``guard``         Circuit breaker, quarantine, emergency stop, safe mode.

Modules here never import ``cron.*`` at module level (and cron imports this
package lazily inside functions) so there is no import cycle in either
direction.
"""

from automation.model import (
    AutomationState,
    MISSED_POLICIES,
    RESOURCE_LIMIT_KEYS,
    WATCHED_FIELDS,
    definition_fingerprint,
    lifecycle_of,
    normalize_breaker,
    normalize_missed_policy,
    normalize_resource_limits,
    normalize_timezone,
    validate_automation,
)
from automation import guard, model, schedule_time

__all__ = [
    "AutomationState",
    "MISSED_POLICIES",
    "RESOURCE_LIMIT_KEYS",
    "WATCHED_FIELDS",
    "definition_fingerprint",
    "lifecycle_of",
    "normalize_breaker",
    "normalize_missed_policy",
    "normalize_resource_limits",
    "normalize_timezone",
    "validate_automation",
    "guard",
    "model",
    "schedule_time",
]
