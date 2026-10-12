# AETHEROS_EXPERIMENT_ENGINE — Runtime, Sandbox, Manifests

## Execution pipeline

GeneratedCode → StaticValidation (banned-primitive scan) →
SecurityPolicy (safety class) → Sandbox (subprocess) → Execution →
Observation (metrics.json, raw.json, stdout/stderr) → ArtifactValidation.

## Sandbox boundary (honest)

- Isolated: working directory (fresh temp dir per run), environment
  (PATH-only clean env — no secrets), wall-clock timeout (default
  120 s), stdout/stderr truncation, exit-code capture.
- PARTIAL: filesystem jail. Generated code runs as the user and can
  read the disk. Banned primitives block the easy destructive paths
  (`os.system`, `subprocess.*`, sockets, `shutil.rmtree`, `os.remove`,
  `ctypes`, network clients). `open()` is allowed so experiments can
  write metrics — reads of sensitive files are a documented residual
  risk; use containers + code review for untrusted code.
- Never: blind retry of dangerous actions (timeouts recorded, no
  auto-retry); network access (no network clients importable, no
  proxy env passed).

## Manifests & reproducibility

Every run records: environment, dependencies, dataset hashes,
parameters, seeds, commands, tool versions, hardware slot, and a
`manifest_fingerprint` (code+params+dataset+env+seed). Identical
fingerprints are deduplicated (`DUPLICATE_PREVENTED`) unless explicit
replication is requested. `reproduce()` reruns and compares metrics
with float tolerance (exact bitwise equality is wrong for timings).

## Checkpoints, branching, DAGs

Per-experiment checkpoints (manifest + status + timestamp); task
checkpoints (status, history, experiment ids) support crash resume
without duplicating completed runs (idempotency keys = fingerprints).
`ExperimentDesigner.branch()` forks with one variable changed;
`parent_id` links form the experiment DAG.
