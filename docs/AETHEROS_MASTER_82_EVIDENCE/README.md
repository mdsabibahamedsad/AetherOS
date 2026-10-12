# Master 82 evidence index (2026-09-15 UTC; nothing modified in the repo worktree by Master 82 except new docs)

| File | Generator | Result |
|---|---|---|
| `01-initial-state.txt` | rev-parse/branch/log/status count | HEAD 2bdfbfd8, main, 2786 paths |
| `01-dirt-inventory.tsv` | porcelain dump + rule classifier | 2786 rows: 1778 USER_OWNED M, 13 USER_OWNED D, 824 UNKNOWN ??, 153 DOCUMENTATION, 9 GENERATED_OUTPUT, 9 MASTER_80 |
| `02-user-decision.txt` | authorization prompt | block-and-report (tree untouched) |
| `03-node-reverify.txt` | portable Node 22.12.0 + bundled npm | v22.12.0 / npm 10.9.0 |
| `04-renderer-forensics.md` | vitest under Node 22 AND Node 25 | 3 fails identical both toolchains; assertion-level causes; KNOWN_PREEXISTING |
| `05-ci-vm-recheck.txt` | gh auth + Sandbox/Hyper-V probe | token invalid → NOT_RUN; no clean env → BLOCKED |
| `06-gate-stop.md` | A01 evaluation | STOP, WINDOWS_RC_BLOCKED |
