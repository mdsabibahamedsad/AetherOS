# AETHEROS MASTER 15 — CERTIFICATION BASELINE (Phase 0)

Date: 2026-08-23 · Commit: `bb9f876` ("fix: complete hermes->aetheros rebrand...")
Machine: Windows 11, Python 3.12.13 (.venv), win32.

## Frozen phase status at baseline

| Status | Count |
|---|---|
| COMPLETE | 70 |
| PARTIAL | 27 |
| NOT STARTED | 3 |

## Test run (Master-15 + adjacent tool suites)

```
pytest tests/aetheros_computer/ tests/tools/test_master15_browser_transfer.py \
       tests/tools/test_browser_cdp_tool.py tests/tools/test_computer_use.py \
       tests/tools/test_vision_tools.py tests/tools/test_terminal_tool.py \
       tests/tools/test_file_tools.py tests/tools/test_approval.py \
       tests/tools/test_mcp_tool.py -q -p no:cacheprovider
→ 687 passed / 9 failed / 0 skipped
```

## Known pre-existing failures (documented separately, excluded from comparison)

All 9 are **POSIX-only shell-guard expectations** that fail identically on
win32 before any Master-15 work:

1–6. `test_approval.py::TestAetherosConfigWriteProtection::test_{sed,perl,ruby}_in_place_*`
     — assert `sed -i` / `perl -i` / `ruby -i` in-place-edit guard behavior
     (tools not exercised this way on Windows paths).
7–8. Two sibling variants of the above.
9.  `test_mcp_tool.py::TestBuildSafeEnv::test_windows_location_vars_passed_without_secrets`.

Rule 14/15 compliance: these are **not hidden, not modified, and counted
separately**. The no-regression gate is "identical set & count vs baseline".

## Machine-readable twin

`aetheros_master15_baseline.json`
