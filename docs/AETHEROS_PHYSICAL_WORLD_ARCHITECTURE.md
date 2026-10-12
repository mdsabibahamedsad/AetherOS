# Physical World Architecture

## State representation

`PhysicalWorldState` extends the Master-52 WorldState pattern with
rooms, surfaces, objects, robots, devices, people, hazards, poses,
velocities, connectivity, power, and environmental conditions. Every
variable is a `StateVar`: value + timestamp + source + confidence +
freshness bound + mode (OBSERVED | INFERRED | PREDICTED | SIMULATED |
REPLAYED | UNKNOWN). Freshness violations force re-observation (§187);
stale state never silently acts as truth.

## Provenance ladder (§5, §180)

- camera record -> object *detected* (OBSERVED)
- identity assignment -> *inferred* (INFERRED)
- rollout output -> *predicted movement* (PREDICTED/SIMULATED)
- sensor register -> *actual position* (OBSERVED, LIVE only)

Conflicts (camera vs human) raise CONFLICT and seek evidence (§182);
resolution prefers source authority, then freshness, independence,
then direct observation.

## Frames (§15-16)

`world | room | robot | camera | sensor | tool | object`. All
transforms explicit translation + unit quaternion with timestamp and
confidence; stale/zero-confidence transforms rejected; unregistered
hops raise instead of mixing frames silently.

## Spatial + memory

Occupancy grids treat unknown as blocked (fail closed). Object memory
(`Memory 2.0` pattern: Object -> located_at -> Room -> shelf ->
timestamp) expires via TTL (§63). Skills validate per environment
(§122); cross-environment recall is flagged stale-environment.
