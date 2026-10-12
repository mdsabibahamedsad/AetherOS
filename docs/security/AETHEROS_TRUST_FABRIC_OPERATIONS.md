# Trust Fabric Operations (§152-154, §159-165, §233)

## `aetheros trust doctor`

Checks identity/policy/audit/revocation/emergency/secrets health,
flags unrestricted network, unknown/quarantined/malicious
extensions, and development bypasses. Posture is CRITICAL /
MODERATE / GOOD with evidence — never a bare score (§154).

## Action stream / audit search / provenance query

Every stream item comes from real `AuditLog` events. Filters:
agent, action, risk, incident, time. `trust provenance <action-id>`
returns the recorded CLAIM->SOURCE / ACTION->POLICY / ACTION->
AUTHORITY / RESULT->ACTION / DECISION->EVIDENCE chain; unrecorded
actions report "not recorded" instead of inventing reasoning (§157).

## Revocation / emergency / recovery

`trust revoke --agent|--delegation|--capability|--device|
--remote-agent` requires authorization and propagates through the
authority graph (no UI-refresh reliance). `trust emergency-stop`
invokes layered kills with measured latency. Recovery is staged
DIAGNOSTICS -> REVIEW -> RESTORE MINIMAL -> REAUTHORIZE -> RESUME;
never auto-resumes to unrestricted autonomy.

## Exports

JSON/JSONL/CSV/signed evidence bundles/human-readable reports,
gated by access controls (§159).

## Monitoring (§233)

Denied actions, unusual agents, rapid privilege requests, repeated
approvals, unexpected remotes, large data flows, network anomalies,
policy changes, kill-switch events. Anomaly signals are advisory;
they never grant authority (§234).
