# AetherOS Windows Benchmarks (measured 2026-09-11)

Environment: Windows 10.0.26200 AMD64, 12 CPUs, Python 3.12.13, commit
2bdfbfd, `scripts/windows_bench.py`. Electron figures N/A (binary
absent); power state unknown.

| Measurement | median | p95 | n |
|---|---|---|---|
| import operating layer | 4.38ms | 287.19ms | 3 |
| intent → plan (9-step) | 0.03ms | 0.14ms | 10 |
| CLI `--help` startup | 5308.84ms | 5715.4ms | 3 |

Notes: `--help` pays ~5.3s of import cost (12k-line CLI + heavy
imports; P1 to profile/lazy-load). No baseline existed, so none is
manufactured — these ARE the baseline. Re-run via the new
`windows-platform.yml` bench job on CI hardware.
