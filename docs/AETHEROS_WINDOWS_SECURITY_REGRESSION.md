# AetherOS Windows Security Regression (64.1)

Executed (unit-level, all passing): toast-action spoofing (unknown/
expired/missing-task/resolved-task/capability-mismatch/unauthorized/
policy-revoked → denied); UIA privilege escalation (desktop control
denied on default scopes; control requires paired read); update
tampering (bad hash/publisher/channel/downgrade → rejected); junction
traversal + hidden-console policy (existing suites); guard injection/
traversal denial (operating-layer suite).

UNVERIFIED live (need packaged app/VM): malicious deep-link routing,
protocol abuse, installer-argument abuse, PATH/DLL hijacking, clipboard/
capture abuse, MCP/A2A payloads against native surfaces, SmartScreen/
Defender verdicts. No security control was disabled; no bypass added.
Signing remains the highest-leverage missing mitigation (BLOCKED).
