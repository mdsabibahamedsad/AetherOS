# Master 81 evidence index — every file from a command that actually ran (2026-09-15 UTC)

| File | Generator | Result |
|---|---|---|
| `01-initial-state.txt` | git rev-parse/branch/status count, node/npm/builder/git versions | HEAD 2bdfbfd8, main, 2783 paths, Node 25.5/npm 11.8/builder 26.8.1 |
| `02-dirt-classification.md` | porcelain grouping + diff analysis | 1780 M (1424 real content drift) + 990 ?? + 13 D-class check; categories assigned, nothing destroyed |
| `03-node22-bootstrap.txt` | nodejs.org download + SHASUMS verify + `node --version` | v22.12.0, SHA 2b8f2256… MATCH official |
| `04-preflight-node22.log` | Master-80 preflight under Node 22 | A02→PASS; A01/A10 still FAIL (correct) |
| `05-guard-tests-node22.log` | `node --test windows-release-guards.test.cjs` under 22 | 19/19 PASS |
| `06-electron-tests-node22.log` | 17-file Electron suite under 22 | 176/176 PASS |
| `07-renderer-tests-node22.log` | vitest under 22 | 808/811 (3 pre-existing fails, identical under 25) |
| `08-workflow-promotion.md` | root workflow creation + PyYAML validation | 7 jobs, DAG verified; nested inert copy removed |
| `09-ci-auth.txt` | `gh auth status` + `git ls-remote` | token invalid → CI NOT_RUN |
| `10-gate-stop.md` | exact failed gate record | STOP at A01 RELEASE_SOURCE_NOT_CLEAN |
| `11-user-decision.txt` | user authorization prompt | block-and-report; tree untouched |
