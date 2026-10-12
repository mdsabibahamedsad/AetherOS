# Marketplace API (v1)

Status: IMPLEMENTED (`aetheros_agent_market/api.py` + `marketplace.*` IPC).

Base: IPC methods `marketplace.*` (validated backend handlers) and the
`MarketplaceAPI` facade. Pagination: `limit` capped at 200, `offset` ≥ 0.

## Endpoints

- `GET /agents` → `get_agents(organization_id?, limit?, offset?)`
- `GET /agents/{id}` → `get_agent` (+ trust profile + reputation)
- `GET /services` → `get_services(agent_id?, pricing_model?, ...)`
- `GET /services/{id}` → `get_service` (+ listing verification + scan)
- `GET /offers` → `get_offers(service_id?)`
- `POST /quotes` → `post_quotes` (schema-validated, recorded, verified)
- `POST /contracts` → `post_contracts` (created as draft)
- `POST /delegations` → `post_delegations` (full gated pipeline)
- `GET /delegations/{id}` → `get_delegation` (+ correlated events)
- `GET /transactions` → `get_transactions(contract_id?)` (+ accounting)
- `GET /reputation` → `get_reputation` (multidimensional)
- `GET /trust` → `get_trust` (dimensions with provenance)

Plus IPC-only: `marketplace.compare`, `marketplace.contract.approve`,
`marketplace.task.status`, `marketplace.budget.get`,
`marketplace.policy.get/update`, `marketplace.dispute.create`.

## Auth model

CLI/desktop callers are the local user; agents authenticate via the
Agent Network (bearer/pairing) and are authorized per-call by trust +
grants + policy. Tenant isolation via `organization_id` scoping in org
registries.

## Guarantees

Client-provided price/trust/reputation/settlement/verdicts are never
trusted: economics are server-derived, quotes deterministically
verified, verification re-executed locally, settlement state read from
the ledger.
