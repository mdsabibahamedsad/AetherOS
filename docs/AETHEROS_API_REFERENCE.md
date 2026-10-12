# AetherOS Developer API Reference

Registry version `1.0.0`, schema version `1.0.0`.

| Method | Endpoint | Stability | Auth | Scopes | Rate | Input | Output | Idempotent | Streaming |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/v1/agents` | PUBLIC | api-key | agents:write | agent | Agent | Agent | yes | no |
| GET | `/api/v1/agents` | PUBLIC | api-key | agents:read | standard | — | — | no | no |
| GET | `/api/v1/agents/{id}` | PUBLIC | api-key | agents:read | standard | — | Agent | no | no |
| POST | `/api/v1/tasks` | PUBLIC | api-key | tasks:write | task | AgentTask | AgentResult | yes | no |
| GET | `/api/v1/tasks/{id}` | PUBLIC | api-key | tasks:read | standard | — | AgentResult | no | no |
| POST | `/api/v1/tasks/{id}/cancel` | PUBLIC | api-key | tasks:write | task | — | — | yes | no |
| GET | `/api/v1/tasks/{id}/events` | PUBLIC | api-key | tasks:read | standard | — | AgentEvent | no | yes |
| POST | `/api/v1/tools` | PUBLIC | api-key | tools:write | tool | Tool | Tool | yes | no |
| GET | `/api/v1/tools` | PUBLIC | api-key | tools:read | standard | — | — | no | no |
| POST | `/api/v1/tools/{id}/invoke` | PUBLIC | api-key | tools:invoke | tool-invoke | Intent | AgentResult | yes | no |
| POST | `/api/v1/skills` | PUBLIC | api-key | skills:write | standard | Skill | Skill | yes | no |
| GET | `/api/v1/skills` | PUBLIC | api-key | skills:read | standard | — | — | no | no |
| POST | `/api/v1/memory/records` | PUBLIC | api-key | memory:write | memory | MemoryRecord | MemoryRecord | yes | no |
| GET | `/api/v1/memory/search` | PUBLIC | api-key | memory:read | memory | — | — | no | no |
| POST | `/api/v1/artifacts` | PUBLIC | api-key | artifacts:write | standard | — | Artifact | yes | no |
| GET | `/api/v1/artifacts/{id}` | PUBLIC | api-key | artifacts:read | standard | — | Artifact | no | no |
| POST | `/api/v1/automations` | PUBLIC | api-key | automations:write | standard | Automation | Automation | yes | no |
| POST | `/api/v1/webhooks` | PUBLIC | api-key | webhooks:write | standard | Webhook | Webhook | yes | no |
| GET | `/api/v1/registry` | PUBLIC | none | — | standard | — | — | no | no |
| GET | `/api/v1/schemas` | PUBLIC | none | — | standard | — | — | no | no |
| GET | `/api/v1/health` | PUBLIC | none | — | standard | — | — | no | no |
| POST | `/api/v1/a2a/tasks` | EXPERIMENTAL | api-key | a2a:write | standard | — | — | yes | no |
| GET | `/api/v1/a2a/card` | EXPERIMENTAL | none | — | standard | — | AgentCard | no | no |

## Versioning

See `AETHEROS_API_VERSIONING.md`. `/api/v2` currently serves as an alias of v1 with `Sunset: not-planned` headers; breaking changes require a new registry version plus a 6-month deprecation notice.

## Errors

Every failure returns a typed `AetherError` body (`code/category/message/retryable/remediation/...`). See `AETHEROS_DEVELOPER_SECURITY.md` for the category table.
