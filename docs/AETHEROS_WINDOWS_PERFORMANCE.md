# AetherOS Windows Performance Report

No benchmarks were executed in this environment — per the no-cheating
rule, no numbers are claimed. Baselines to capture on real hardware/CI
(cold/warm startup, first paint, time-to-usable-agent, idle/active
memory/CPU, IPC latency, tool latency, shutdown, update install), with
environment, hardware, OS build, Electron/Node versions, commit, method,
sample size, median/p95/p99.

Known-light facts (measured): the 8 dependency-free Electron unit files
run 110 tests in <0.5s; Python intelligence suites run 242 tests in ~8s.
`powerMonitor` resume hooks exist so background-adjacent work can pause
on sleep. No runaway polling introduced by this phase (30s top-bar poll
predates it; Home fetch is a single parallel batch).
