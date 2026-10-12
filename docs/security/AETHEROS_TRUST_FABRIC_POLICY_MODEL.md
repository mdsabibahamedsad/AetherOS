# Policy Model (§12-14, §147-148)

Policies are executable, deterministic, versioned, testable
artifacts — content-hashed (`PolicyVersion`), never bare
natural language.

## Dimensions

identity, agent type, resource, action, data classification,
network destination, environment, time, location, task purpose,
risk, trust score, delegation chain, previous actions, execution
path, approval state, model/tool identity, organization, user,
device, physical environment.

## Decisions

ALLOW | DENY | REQUIRE_APPROVAL | REQUIRE_STEP_UP_AUTH |
SANDBOX_ONLY | SIMULATION_ONLY | RATE_LIMIT | DEFER. Never
"probably allowed".

## Precedence (deterministic)

global-deny > organization > user > task > agent > tool >
resource > temporary-approval; DENY wins conflicts unless a
higher-precedence explicit semantic states otherwise (documented
per policy).

## Lifecycle

DRAFT -> TEST -> SHADOW -> CANARY -> ACTIVE -> DEPRECATED ->
REVOKED. Activation of high-impact policies requires passing
tests. Every decision records policy_id + version + hash, so
history is reconstructable. Simulator answers "what would
happen" without executing; replay diffs old/current/proposed
policies over recorded traces; regression suite flags false
allows/denies.

## Deny/approval explanations (§14)

Every DENY/REQUIRE_APPROVAL carries policy_id, version, matched
rules, identity, action, resource, risk, missing authority,
required approval, and a human-readable reason with fix guidance.
