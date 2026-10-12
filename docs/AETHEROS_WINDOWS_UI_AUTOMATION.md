# AetherOS Windows UI Automation

Model: `aetheros_computer/uia.py` — normalized `UIElement`
(runtimeId, automationId, name, controlType, className, bounds, state,
value, patterns, children); raw COM never crosses to callers. Methods:
inspect/find/focus/invoke/toggle/select/expand/collapse/setValue/scroll/
getValue. Hierarchy: semantic > automationId > visual > coordinates.

Scopes (distinct, least-privilege): `UI_READ_AETHEROS`,
`UI_READ_APP`, `UI_READ_DESKTOP`, `UI_CONTROL_*` — control requires its
paired read scope; defaults are AetherOS-only. Live tree provider:
UNVERIFIED (Windows here reports `ocr_fallback`; `UnavailableProvider`
raises honestly instead of returning fake elements). Agent flow: find
("Save", Button) → verify enabled → invoke → verify application/UI/
filesystem state (never "click succeeded" alone).
