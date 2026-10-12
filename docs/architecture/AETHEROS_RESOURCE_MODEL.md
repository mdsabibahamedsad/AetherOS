# AetherOS Resource Model

See `AETHEROS_SCHEDULER.md` for the scheduler half; this file records the
accounting contract.

- Unit: `ResourceBudget` (per-agent request/allocation) and
  `ResourceAllocation` (allocated / used / reserved snapshot).
- Costs flow into `CostManager` (LLM tokens, GPU/CPU time, network,
  storage, tool/API/delegation/automation/physical costs) with per-task
  estimate / actual / remaining budget.
- Latency flows into `LatencyManager` (queue, planning, model, tool,
  network, render, approval, execution, verification, end-to-end) with
  p50/p95/p99 exposure. `kernel/benchmark.py` reports real host-local
  numbers; cross-machine comparison is explicitly disclaimed.
