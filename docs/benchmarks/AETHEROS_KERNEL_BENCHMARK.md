# AetherOS Kernel Benchmark (methodology)

Runner: `kernel/benchmark.py::run_benchmarks(kernel)`; CLI:
`aetheros kernel benchmark`. All values are live `perf_counter`
measurements on the executing host — never transferred across machines.

Ops measured (§88): `intent.admit`, `policy.evaluate_intent`,
`capability.list`, `agent.create`, `scheduler.schedule`, `memory.write`,
`memory.read`, `checkpoint.create`. Reported per op: `n`, `p50/p95/p99`,
`mean` (ms).

Agent benchmarks (§89): task completion, tool-call count, tokens, latency,
cost, retries, failure rate, human interventions, policy blocks, recovery
success — compared only on identical tasks/methodology. Scheduler
benchmarks (§90): 10/100/1000-agent simulated workloads measuring queue
latency, fairness, throughput, utilization, starvation, deadlocks,
recovery (clearly labeled SIMULATED). Security benchmarks (§91) and
failure injection (§92: model/tool timeouts, network drop, node/agent
crash, disk/memory/GPU pressure, credential expiry, policy update, device
disconnect) verify recovery without duplicate side effects (§93).

No LLM-only judge for critical certification (§87).
