# §22 renderer failure forensics — evidence, not labels

Suite: `src/themes/design-tokens.test.ts` (design-system token contract, Master 22 P5/P37).
Executed under BOTH Node v22.12.0 and Node v25.5.0: identical 3 failures.

1. `type ramp covers display→status hierarchy exactly once each`
   Reason: `expected [ 'display', 'heading', …(7) ] to deeply equal [ 'display', 'heading', …(5) ]`
   → working-tree token list grew (9 vs 7 expected). Design-token content drift.
2. `motion durations stay subtle (≤260ms) per P37 anti-decorative rule`
   Reason: `expected 320 to be less than or equal to 260`
   → a duration token is 320ms. Design-token content drift.
3. `spacing scale covers the standard step ladder in rem units`
   Reason: ladder arrays differ (working tree has extra steps).
   → Design-token content drift.

Release-relevance screen (§23): packaging NO · Windows runtime NO · renderer boot NO ·
IPC NO · branding NO · security NO. Verdict: **KNOWN_PREEXISTING** (§81).
Harness note: vitest also flags `check-packaging-path-lengths.test.mjs` (node:test module,
9/9 PASS under `node --test`) — pre-existing harness mismatch, unchanged by Masters 80–82.
